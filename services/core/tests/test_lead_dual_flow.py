"""Dual-flow acceptance: real PostgreSQL, no external provider or Telegram I/O."""
import asyncio
import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from sqlalchemy import select, func, text
from app.db.session import create_session_factory, session_scope
from app.models import User, UserIdentity, LeadFlowRun, ConsultationRequest, OutboundMessage, DiagnosticSession
from app.services.lead_dual_flow import LeadDualFlow, callback, clean_text
from app.services import lead_dual_copy as copy
from app.services.lead_profile_flow import PROFILE_STEPS
from app.services.admin_read import AdminLeadReadService


@pytest.mark.parametrize("task,setup", [(task, list(copy.WORK)[i % 3]) for i, task in enumerate(copy.TASKS)])
def test_ai_webhook_end_to_end_without_any_provider(monkeypatch, task, setup):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.core.settings import get_settings
    import app.api.routes.telegram_lead as route
    from app.api.routes.admin_auth import current_actor
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("dedicated test database required")
    assert "ai_my_time_test" in urlsplit(url).path
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "dual-test-secret")
    monkeypatch.setenv("LEAD_DUAL_FLOW_ENABLED", "true")
    get_settings.cache_clear()
    calls = []

    def forbidden(_request):
        calls.append(1)
        raise AssertionError("AI intake attempted to construct an LLM provider")

    monkeypatch.setattr(route, "_diagnostic_provider", forbidden)

    async def inspect():
        factory = create_session_factory(url)
        try:
            async with session_scope(factory) as s:
                run = await s.scalar(select(LeadFlowRun).order_by(LeadFlowRun.created_at.desc()).limit(1))
                messages = (await s.scalars(select(OutboundMessage).where(OutboundMessage.dedupe_key.like(f"dual:{run.id}:{run.revision}:%")))).all()
                payload = next((m.payload_json for m in messages if m.dedupe_key.endswith(":prompt")), messages[-1].payload_json)
                return payload, dict(run.answers_json), run.user_id, run.source_json
        finally:
            await factory.kw["bind"].dispose()

    async def clear():
        factory = create_session_factory(url)
        try:
            async with session_scope(factory) as s:
                await s.execute(text("TRUNCATE users CASCADE"))
        finally:
            await factory.kw["bind"].dispose()

    asyncio.run(clear())
    app = create_app()

    async def owner(_request=None):
        return object()

    # Analytics reads are authenticated in production; use a test-only actor.
    monkeypatch.setattr("app.api.routes.admin_leads.current_actor", owner)
    try:
        with TestClient(app) as client:
            index = 10000

            def post(message=None, data=None):
                nonlocal index
                index += 1
                sender = {"id": 900000888, "first_name": "Тест без username"}
                payload = {"update_id": index}
                if data:
                    payload["callback_query"] = {"id": f"callback-{index}", "from": sender,
                        "message": {"message_id": 10, "chat": {"type": "private"}}, "data": data}
                else:
                    payload["message"] = {"message_id": index, "chat": {"type": "private"}, "from": sender, "text": message}
                response = client.post("/webhooks/telegram/lead", json=payload,
                    headers={"X-Telegram-Bot-Api-Secret-Token": "dual-test-secret"})
                assert response.status_code == 204, response.text
                return payload

            def press(label):
                payload, *_ = asyncio.run(inspect())
                data = next(b["callback_data"] for b in payload["buttons"] if b["text"].removeprefix("✓ ") == label)
                return post(data=data)

            first = post(message="/start unknown_payload")
            # Exact delivery retry must not multiply the welcome run.
            assert client.post("/webhooks/telegram/lead", json=first,
                headers={"X-Telegram-Bot-Api-Secret-Token": "dual-test-secret"}).status_code == 204
            press("Хочу умного помощника")
            press(copy.WORK[setup])
            press(copy.ACTIVITY["services"])
            press(copy.TASKS[task])
            press("Готово")
            if task == "other":
                post(message="Задача своими словами")
            payload, answers, uid, source = asyncio.run(inspect())
            assert answers["priority_task"] == task  # no redundant priority step
            assert source["source_code"] == "telegram_direct"
            assert "Это может быть один AI-агент" in payload["text"]
            assert calls == []
            press("Обсудить с нашим экспертом")
            post(message="ещё вопрос")
            assert calls == []
            metrics = client.get("/admin/intake-analytics?days=30")
            assert metrics.status_code == 200, metrics.text
            assert metrics.json()["directions"][1]["consultations"] == 1
            assert metrics.json()["directions"][1]["people"] == 1
            assert metrics.json()["tasks"][0]["task"] == copy.TASKS[task]
    finally:
        get_settings.cache_clear()


def test_reviewed_copy_snapshot_and_legacy_mapping():
    actual = {"welcome": copy.WELCOME, "intro": copy.AI_INTRO, "business_intro": copy.BUSINESS_INTRO,
              "business": copy.BUSINESS, "work": copy.WORK, "activity": copy.ACTIVITY, "tasks": copy.TASKS,
              "results": {k: copy.result_text({"priority_task": k}) for k in copy.TASKS}}
    actual = json.loads(json.dumps(actual, ensure_ascii=False))
    expected = json.loads((Path(__file__).parent / "fixtures/lead_dual_copy_v1.json").read_text())
    assert actual == expected
    for old, new in zip(PROFILE_STEPS, copy.BUSINESS, strict=True):
        assert old.code == new[0]
        assert len(old.options) == len(new[2])
    assert PROFILE_STEPS[0].options == ("Услуги", "Продажа товаров", "Производство", "Проектные / подрядные работы", "Смешанная модель", "Другое")
    for key in copy.TASKS:
        assert len(copy.result_text({"priority_task": key})) < 4096
        run = LeadFlowRun(id=uuid.uuid4(), revision=123456)
        assert len(callback(run, key).encode()) <= 64
    assert clean_text("  репетитор\n  английского\x00 ") == "репетитор английского"
    with pytest.raises(ValueError):
        clean_text("x" * 241)


def test_certificate_is_opt_in_and_conference_result_only():
    class Queue:
        def __init__(self):
            self.messages = []
        async def enqueue(self, **kwargs):
            self.messages.append(kwargs["payload"])

    async def check():
        run = LeadFlowRun(id=uuid.uuid4(), user_id=uuid.uuid4(), revision=1, kind="ai_assistant",
            state="result", answers_json={"priority_task": "content"}, source_json={"source_code": "conference_2026"})
        flow = LeadDualFlow(None)
        flow.q = Queue()
        await flow.render(run)
        assert "Подтверждённые условия" not in flow.q.messages[-1]["text"]
        flow.certificate_text = "Подтверждённые условия"
        await flow.render(run)
        assert flow.q.messages[-1]["text"].endswith("Подтверждённые условия")
        run.source_json = {"source_code": "telegram_direct"}
        await flow.render(run)
        assert "Подтверждённые условия" not in flow.q.messages[-1]["text"]
    asyncio.run(check())


def test_dual_intake_postgres_acceptance():
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("dedicated test PostgreSQL required")
    assert url.startswith("postgresql+asyncpg://") and "ai_my_time_test" in urlsplit(url).path
    asyncio.run(exercise(url))


def test_existing_v2_continues_after_new_direction_menu(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.core.settings import get_settings
    from app.models import LeadBotSession
    url = os.getenv("AI_MY_TIME_TEST_DATABASE_URL")
    if not url:
        pytest.skip("dedicated test PostgreSQL required")
    assert "ai_my_time_test" in url

    async def setup():
        f = create_session_factory(url)
        try:
            async with session_scope(f) as s:
                await s.execute(text("TRUNCATE users CASCADE"))
                user = User()
                s.add(user)
                await s.flush()
                s.add(UserIdentity(user_id=user.id, provider="telegram", connection_scope="ai_my_time_lead_bot", external_id="900000999"))
                s.add(LeadBotSession(user_id=user.id, state="business_type", status="open", flow_version="v2", version=1))
        finally:
            await f.kw["bind"].dispose()

    async def state():
        f = create_session_factory(url)
        try:
            async with session_scope(f) as s:
                run = await s.scalar(select(LeadFlowRun).order_by(LeadFlowRun.created_at.desc()).limit(1))
                old = await s.scalar(select(LeadBotSession))
                return run.id, run.revision, old.state, run.kind
        finally:
            await f.kw["bind"].dispose()

    asyncio.run(setup())
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LEAD_DUAL_FLOW_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_LEAD_WEBHOOK_SECRET", "dual-test-secret")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            def post(i, data=None):
                sender = {"id": 900000999}
                p = {"update_id": i}
                if data:
                    p["callback_query"] = {"id": str(i), "from": sender, "message": {"chat": {"type": "private"}}, "data": data}
                else:
                    p["message"] = {"chat": {"type": "private"}, "from": sender, "text": "/start"}
                assert client.post("/webhooks/telegram/lead", json=p, headers={"X-Telegram-Bot-Api-Secret-Token": "dual-test-secret"}).status_code == 204
            post(20001)
            rid, rev, old, kind = asyncio.run(state())
            post(20002, f"df:{rid.hex}:{rev}:business")
            assert asyncio.run(state())[3] == "legacy_business"
            post(20003, "profile:v2:1:business_type:0")
            assert asyncio.run(state())[2] == "team_size"
            for version, step in enumerate(PROFILE_STEPS[1:], start=2):
                post(20002 + version, f"profile:v2:{version}:{step.code}:0")
            assert asyncio.run(state())[2] == "complete"

            async def verify_snapshot():
                f = create_session_factory(url)
                try:
                    async with session_scope(f) as s:
                        run = await s.get(LeadFlowRun, rid)
                        diagnostic = await s.scalar(select(DiagnosticSession))
                        assert run.status == "completed" and len(run.answers_json) == 6
                        assert diagnostic.input_snapshot_json["flow_run_id"] == str(rid)
                finally:
                    await f.kw["bind"].dispose()
            asyncio.run(verify_snapshot())
    finally:
        get_settings.cache_clear()


async def exercise(url):
    factory = create_session_factory(url)
    try:
        async with session_scope(factory) as s:
            await s.execute(text("TRUNCATE users CASCADE"))
            user = User(display_name="Тестовый человек", marketing_consent_status="unknown", content_subscription_status="unsubscribed")
            s.add(user)
            await s.flush()
            uid = user.id
            s.add(UserIdentity(user_id=uid, provider="telegram", connection_scope="ai_my_time_lead_bot", external_id="900000777"))
        async with session_scope(factory) as s:
            flow = LeadDualFlow(s)
            await flow.menu(user_id=uid, interaction_id="start:1", source={"source_code": "telegram_direct"})
            await flow.menu(user_id=uid, interaction_id="start:1")
            assert await s.scalar(select(func.count()).select_from(LeadFlowRun)) == 1
            run = await s.scalar(select(LeadFlowRun))
            rid = run.id
        counter = 0
        provider_calls = []

        def disabled_provider():
            provider_calls.append(1)
            return None

        async def press(action, *, repeat=False, foreign=False):
            nonlocal counter
            counter += 1
            async with session_scope(factory) as s:
                run = await s.get(LeadFlowRun, rid)
                rev = run.revision
                args = dict(user_id=uuid.uuid4() if foreign else uid, run_id=rid, revision=rev,
                            action=action, interaction_id=f"cb:{counter}", provider_factory=disabled_provider)
                await LeadDualFlow(s).handle(**args)
                if repeat:
                    await LeadDualFlow(s).handle(**args)

        await press("ai")
        await press("solo", repeat=True)
        await press("other")
        async with session_scope(factory) as s:
            await LeadDualFlow(s).text(user_id=uid, text="  преподаватель <script>  ", interaction_id="text:1")
        await press("materials", repeat=True)
        await press("content")
        await press("content")  # remove a selected task
        await press("other")
        await press("done")
        async with session_scope(factory) as s:
            await LeadDualFlow(s).text(user_id=uid, text="Моя задача", interaction_id="text:2")
            run = await s.get(LeadFlowRun, rid)
            assert run.state == "priority"
        await press("materials")
        async with session_scope(factory) as s:
            run = await s.get(LeadFlowRun, rid)
            assert run.answers_json["desired_tasks"] == ["materials", "other"]
            assert run.answers_json["priority_task"] == "materials"
            assert await s.scalar(select(func.count()).select_from(DiagnosticSession)) == 0
            assert await LeadDualFlow(s).text(user_id=uid, text="ещё текст", interaction_id="text:3") is True
            assert provider_calls == []
        await press("pause")
        async with session_scope(factory) as s:
            assert await s.scalar(select(func.count()).select_from(ConsultationRequest)) == 0
            user = await s.get(User, uid)
            assert user.marketing_consent_status == "unknown" and user.content_subscription_status == "unsubscribed"
        await press("consult", foreign=True)
        # Concurrent transactions must produce exactly one request and one ops outbox row.
        async def consult(i):
            async with session_scope(factory) as s:
                run = await s.get(LeadFlowRun, rid)
                await LeadDualFlow(s).handle(user_id=uid, run_id=rid, revision=run.revision,
                    action="consult", interaction_id=f"concurrent:{i}", provider_factory=disabled_provider)
        await asyncio.gather(consult(1), consult(2))
        async with session_scope(factory) as s:
            assert await s.scalar(select(func.count()).select_from(ConsultationRequest)) == 1
            request = await s.scalar(select(ConsultationRequest))
            assert request.diagnostic_session_id is None and request.flow_run_id == rid
            assert request.intake_snapshot_json["priority_task"] == copy.TASKS["materials"]
            ops = (await s.scalars(select(OutboundMessage).where(OutboundMessage.channel == "telegram_ops"))).all()
            assert len(ops) == 1
            assert provider_calls == []
            assert "900000777" in ops[0].payload_json["text"]
            assert "Уроки, презентации, материалы" in ops[0].payload_json["text"]
            detail = await AdminLeadReadService(s).person(uid)
            assert detail.telegram_user_id == "900000777"
            assert detail.consultations[0].intake_context["answers"]["activity_other"] == "преподаватель <script>"
            assert detail.flow_runs[0]["run_id"] == str(rid)
        # Explicit switching keeps the immutable old consultation snapshot.
        async with session_scope(factory) as s:
            await LeadDualFlow(s).menu(user_id=uid, interaction_id="start:2")
            newer = await s.scalar(select(LeadFlowRun).order_by(LeadFlowRun.created_at.desc()).limit(1))
            rid = newer.id
        await press("business")
        for _ in range(6):
            await press("0")
        async with session_scope(factory) as s:
            run = await s.get(LeadFlowRun, rid)
            diagnostic = await s.scalar(select(DiagnosticSession))
            assert run.state == "business_complete"
            assert diagnostic.input_snapshot_json["flow_run_id"] == str(rid)
            assert len(diagnostic.input_snapshot_json["profile_answers"]) == 6
            old = await s.scalar(select(ConsultationRequest))
            assert old.intake_snapshot_json["answers"]["work_setup"] == "solo"
            assert provider_calls == [1]
            # A normal completed-business CTA must carry the same run snapshot,
            # not the mutable latest profile or an unrelated historical run.
            from app.services.consultation_lifecycle import ConsultationLifecycleService
            from app.services.diagnostic_dialogue import DiagnosticDialogueService
            await ConsultationLifecycleService(s).cancel(old, notify=False)
            diagnostic.status = "diagnostic_completed"
            await s.flush()
            assert await DiagnosticDialogueService(s, None).consultation_requested(
                user_id=uid, diagnostic_session_id=diagnostic.id)
            business_request = await s.scalar(select(ConsultationRequest).where(ConsultationRequest.flow_run_id == rid))
            assert business_request.diagnostic_session_id == diagnostic.id
            assert business_request.intake_snapshot_json["answers"] == run.answers_json
            assert await s.scalar(select(func.count()).select_from(ConsultationRequest)) == 2
    finally:
        await factory.kw["bind"].dispose()
