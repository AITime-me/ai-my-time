"""Durable deterministic intake; external providers are isolated to finish_business."""
from __future__ import annotations

import uuid
import unicodedata
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (User, UserIdentity, Touchpoint, Event, LeadFlowRun, LeadFlowAction,
                        ConsultationRequest, AttentionItem)
from app.services.outbox import OutboundQueue
from app.services.consultation_lifecycle import ConsultationLifecycleService
from app.services.lead_dual_copy import WELCOME, AI_INTRO, BUSINESS_INTRO, WORK, ACTIVITY, TASKS, BUSINESS, result_text


def callback(run: LeadFlowRun, action: str) -> str:
    value = f"df:{run.id.hex}:{run.revision}:{action}"
    if len(value.encode()) > 64:
        raise ValueError("callback too long")
    return value


def clean_text(value: str) -> str:
    value = " ".join("".join(c for c in value if not unicodedata.category(c).startswith("C") or c.isspace()).split())
    if not 1 <= len(value) <= 240:
        raise ValueError("Опишите коротко, от 1 до 240 знаков.")
    return value


def context(run: LeadFlowRun) -> dict:
    a = run.answers_json
    return {
        "run_id": str(run.id), "kind": run.kind, "copy_version": run.copy_version,
        "source": run.source_json, "answers": a,
        "direction": "Умный помощник" if run.kind == "ai_assistant" else "Наладить работу бизнеса",
        "activity": a.get("activity_other") or ACTIVITY.get(a.get("expert_activity"), "") or a.get("business_type", ""),
        "work_setup": WORK.get(a.get("work_setup"), "") or a.get("team_size", ""),
        "desired_tasks": [TASKS[t] for t in a.get("desired_tasks", []) if t in TASKS],
        "priority_task": TASKS.get(a.get("priority_task"), ""),
        "task_other": a.get("task_other"),
        "business_goal": a.get("automation_goal", ""),
    }


class LeadDualFlow:
    def __init__(self, session: AsyncSession, *, certificate_text: str | None = None):
        self.s = session
        self.q = OutboundQueue(session)
        self.certificate_text = certificate_text[:600] if certificate_text else None

    async def lock(self, user_id):
        await self.s.scalar(select(User).where(User.id == user_id).with_for_update())

    async def claim(self, user_id, interaction_id):
        await self.lock(user_id)
        old = await self.s.scalar(select(LeadFlowAction.id).where(
            LeadFlowAction.user_id == user_id, LeadFlowAction.interaction_id == interaction_id))
        if old:
            return False
        self.s.add(LeadFlowAction(user_id=user_id, interaction_id=interaction_id))
        await self.s.flush()
        return True

    async def menu(self, *, user_id, interaction_id, source=None):
        if not await self.claim(user_id, interaction_id):
            return
        if source is None:
            touch = await self.s.scalar(select(Touchpoint).where(Touchpoint.user_id == user_id)
                                       .order_by(Touchpoint.observed_at.desc()).limit(1))
            source = {"source_code": touch.source_code, "entry_code": touch.entry_code} if touch else {"source_code": "telegram_direct"}
        run = LeadFlowRun(user_id=user_id, kind="choice", state="choice", status="open",
                          source_json=source, answers_json={}, revision=1, copy_version="dual_v1")
        self.s.add(run)
        await self.s.flush()
        buttons = [self.button(run, "Навести порядок в бизнесе", "business"),
                   self.button(run, "Хочу умного помощника", "ai")]
        previous = await self.s.scalar(select(LeadFlowRun).where(LeadFlowRun.user_id == user_id,
            LeadFlowRun.kind != "choice", LeadFlowRun.status.in_(("open", "completed", "paused")))
            .order_by(LeadFlowRun.created_at.desc()).limit(1))
        if previous:
            buttons.append(self.button(previous, "Вернуться к сохранённому прохождению", "resume"))
        from app.models import DiagnosticSession
        diagnostic = await self.s.scalar(select(DiagnosticSession).where(DiagnosticSession.user_id == user_id)
            .order_by(DiagnosticSession.created_at.desc()).limit(1))
        if diagnostic:
            action = "result" if diagnostic.status == "diagnostic_completed" else "resume"
            buttons.append({"text": "Сохранённый разбор бизнеса", "callback_data": f"diagnostic:{action}:{diagnostic.id}"})
        await self.send(run, WELCOME, buttons, f"menu:{interaction_id}")

    def button(self, run, text, action):
        return {"text": text, "callback_data": callback(run, action)}

    async def send(self, run, text, buttons, suffix="prompt"):
        await self.q.enqueue(user_id=run.user_id, channel="telegram_lead",
            payload={"kind": "message", "text": text, "buttons": buttons},
            dedupe_key=f"dual:{run.id}:{run.revision}:{suffix}")

    async def handle(self, *, user_id, run_id, revision, action, interaction_id, provider_factory=None):
        await self.lock(user_id)
        run = await self.s.scalar(select(LeadFlowRun).where(LeadFlowRun.id == run_id, LeadFlowRun.user_id == user_id).execution_options(populate_existing=True))
        if not run or run.revision != revision or run.status == "superseded":
            return
        if not await self.claim(user_id, interaction_id):
            return
        if action == "menu":
            await self.menu(user_id=user_id, interaction_id=interaction_id + ":menu", source=run.source_json)
            return
        if action in ("ai", "business") and run.state == "choice":
            if action == "business":
                from app.models import LeadBotSession, DiagnosticAcceptanceFlow
                legacy = await self.s.scalar(select(LeadBotSession).where(LeadBotSession.user_id == user_id, LeadBotSession.status == "open"))
                acceptance = await self.s.scalar(select(DiagnosticAcceptanceFlow).where(DiagnosticAcceptanceFlow.user_id == user_id, DiagnosticAcceptanceFlow.status == "open"))
                if legacy or acceptance:
                    others = (await self.s.scalars(select(LeadFlowRun).where(LeadFlowRun.user_id == user_id,
                        LeadFlowRun.id != run.id, LeadFlowRun.status == "open"))).all()
                    for other in others:
                        other.status = "superseded"
                    run.kind, run.state = "legacy_business", "legacy"
                    from app.services.lead_profile_flow import LeadProfileFlow
                    await LeadProfileFlow(self.s).start(user_id=user_id)
                    return
            others = (await self.s.scalars(select(LeadFlowRun).where(LeadFlowRun.user_id == user_id,
                        LeadFlowRun.id != run.id, LeadFlowRun.status == "open"))).all()
            for other in others:
                other.status = "superseded"
            run.kind = "ai_assistant" if action == "ai" else "business_operations"
            run.state = "work_setup" if action == "ai" else "business_type"
            await self.send(run, AI_INTRO if action == "ai" else BUSINESS_INTRO, [], "intro")
        elif action == "resume":
            others = (await self.s.scalars(select(LeadFlowRun).where(LeadFlowRun.user_id == user_id,
                LeadFlowRun.id != run.id, LeadFlowRun.status == "open"))).all()
            for other in others:
                other.status = "superseded"
            if run.kind == "legacy_business" and run.state == "legacy":
                from app.services.lead_profile_flow import LeadProfileFlow
                await LeadProfileFlow(self.s).start(user_id=user_id)
                return
        elif action == "pause" and run.state == "result":
            run.status = "paused"
        elif action == "consult" and run.state in ("result", "business_complete"):
            await self.consult(run)
            return
        elif action == "back":
            old_state = run.state
            if run.state == "result":
                prior = run
                run = LeadFlowRun(user_id=user_id, kind=prior.kind, state="tasks", status="open",
                    revision=1, copy_version=prior.copy_version, source_json=dict(prior.source_json),
                    answers_json=dict(prior.answers_json))
                self.s.add(run)
                prior.revision += 1
                await self.s.flush()
            previous = {"expert_activity": "work_setup", "activity_other": "expert_activity",
                        "tasks": "expert_activity", "task_other": "tasks", "priority": "tasks", "result": "tasks"}
            run.state = previous.get(old_state, run.state)
            run.status = "open"
        elif run.kind == "ai_assistant":
            a = dict(run.answers_json)
            if run.state == "work_setup" and action in WORK:
                a["work_setup"] = action
                run.state = "expert_activity"
            elif run.state == "expert_activity" and action in ACTIVITY:
                a["expert_activity"] = action
                a.pop("activity_other", None)
                run.state = "activity_other" if action == "other" else "tasks"
            elif run.state == "tasks" and action in TASKS:
                selected = list(a.get("desired_tasks", []))
                if action in selected:
                    selected.remove(action)
                else:
                    selected.append(action)
                a["desired_tasks"] = [t for t in TASKS if t in selected]
                a.pop("priority_task", None)
            elif run.state == "tasks" and action == "done" and a.get("desired_tasks"):
                self.finish_tasks(run, a)
            elif run.state == "priority" and action in a.get("desired_tasks", []):
                a["priority_task"] = action
                run.state, run.status = "result", "completed"
            else:
                return
            run.answers_json = a
        elif run.kind == "business_operations" and action.isdecimal():
            from app.services.lead_profile_flow import PROFILE_STEPS
            index = next((i for i, step in enumerate(BUSINESS) if step[0] == run.state), None)
            if index is None or int(action) >= len(BUSINESS[index][2]):
                return
            a = dict(run.answers_json)
            a[run.state] = PROFILE_STEPS[index].options[int(action)]
            run.answers_json = a
            if index == 5:
                run.state, run.status = "business_complete", "completed"
                run.revision += 1
                await self.finish_business(run, provider_factory)
                return
            run.state = BUSINESS[index + 1][0]
        else:
            return
        run.revision += 1
        await self.s.flush()
        self.s.add(Event(user_id=user_id, kind="lead_flow_step", payload_json={"run_id": str(run.id),
            "kind": run.kind, "state": run.state, "status": run.status, "revision": run.revision}))
        await self.render(run)

    def finish_tasks(self, run, a):
        if "other" in a["desired_tasks"] and not a.get("task_other"):
            run.state = "task_other"
        elif len(a["desired_tasks"]) == 1:
            a["priority_task"] = a["desired_tasks"][0]
            run.state, run.status = "result", "completed"
        else:
            run.state = "priority"

    async def text(self, *, user_id, text, interaction_id):
        await self.lock(user_id)
        run = await self.s.scalar(select(LeadFlowRun).where(LeadFlowRun.user_id == user_id,
            LeadFlowRun.status != "superseded", LeadFlowRun.kind != "choice")
            .order_by(LeadFlowRun.created_at.desc()).limit(1))
        if not run or run.kind != "ai_assistant":
            return False
        if not interaction_id:
            return True
        if not await self.claim(user_id, interaction_id):
            return True
        if run.state not in ("activity_other", "task_other"):
            await self.send(run, "Выберите вариант кнопкой или вернитесь в главное меню.",
                            [self.button(run, "Главное меню", "menu")], interaction_id)
            return True
        try:
            value = clean_text(text)
        except ValueError as error:
            await self.send(run, str(error), [self.button(run, "Назад", "back")], interaction_id)
            return True
        a = dict(run.answers_json)
        a[run.state] = value
        if run.state == "activity_other":
            run.state = "tasks"
        else:
            self.finish_tasks(run, a)
        run.answers_json = a
        run.revision += 1
        self.s.add(Event(user_id=user_id, kind="lead_flow_text_saved", payload_json={"run_id": str(run.id), "state": run.state}))
        await self.render(run)
        return True

    async def render(self, run):
        a, state = run.answers_json, run.state
        buttons = []
        if state == "work_setup":
            text, options = "А кто сейчас помогает вам в работе?", WORK
        elif state == "expert_activity":
            text, options = "А чем вы занимаетесь?\nНапример, обучаете, консультируете, оказываете услуги или создаёте товары.", ACTIVITY
        elif state == "tasks":
            text, options = "Представьте, что у вас появился помощник. Какие дела вы бы с удовольствием ему поручили?\nМожно выбрать несколько вариантов.", TASKS
        elif state == "priority":
            text, options = "А какое из выбранных дел отнимает больше всего времени или сил?\nДавайте начнём с него.", {k: TASKS[k] for k in a["desired_tasks"]}
        elif state in ("activity_other", "task_other"):
            text, options = "Опишите коротко своими словами (до 240 знаков). Можно вернуться назад или в меню.", {}
        elif state == "result":
            text, options = result_text(a), {}
            if self.certificate_text and run.source_json.get("source_code") == "conference_2026":
                text += "\n\n" + self.certificate_text
            buttons = [self.button(run, "Обсудить с нашим экспертом", "consult"), self.button(run, "Пока не готов(а)", "pause")]
        elif state == "business_complete":
            text, options = "Ответы сохранены. Вы можете обратиться к нашему эксперту, даже если первичный разбор временно недоступен.", {}
            buttons = [self.button(run, "Обсудить с нашим экспертом", "consult")]
        else:
            step = next((item for item in BUSINESS if item[0] == state), None)
            if not step:
                return
            text, options = step[1], {str(i): label for i, label in enumerate(step[2])}
        for key, label in options.items():
            selected = state == "tasks" and key in a.get("desired_tasks", [])
            buttons.append(self.button(run, ("✓ " if selected else "") + label, key))
        if state == "tasks" and a.get("desired_tasks"):
            buttons.append(self.button(run, "Готово", "done"))
        if run.kind == "ai_assistant" and state != "work_setup":
            buttons.append(self.button(run, "Назад", "back"))
        buttons.append(self.button(run, "Главное меню", "menu"))
        await self.send(run, text, buttons)

    async def finish_business(self, run, provider_factory):
        from app.models import DiagnosticSession
        from app.schemas.profile import SaveProfileAnswersCommand
        from app.services.profile import ProfileService
        from app.services.diagnostic_dialogue import DiagnosticDialogueService
        await ProfileService(self.s).save(SaveProfileAnswersCommand(user_id=run.user_id, complete=True,
            answers=[{"question_code": k, "value": v} for k, v in run.answers_json.items()]))
        diagnostic = DiagnosticSession(user_id=run.user_id, status="prepared",
            input_snapshot_json={"flow_run_id": str(run.id), "profile_answers": {k: {"value": v} for k, v in run.answers_json.items()}})
        self.s.add(diagnostic)
        await self.s.flush()
        # A permanent fallback CTA is queued before touching an external provider.
        await self.render(run)
        await DiagnosticDialogueService(self.s, provider_factory() if provider_factory else None).open(diagnostic_session_id=diagnostic.id)

    async def consult(self, run):
        lifecycle = ConsultationLifecycleService(self.s)
        request = await lifecycle.active(run.user_id)
        if request is None:
            request = await self.s.scalar(select(ConsultationRequest).where(ConsultationRequest.flow_run_id == run.id))
        if request is not None:
            if request.status not in {"new", "waiting_response", "scheduled"}:
                await self.send(run, "По этому прохождению обращение уже закрыто. Для новой задачи вернитесь в главное меню.",
                    [self.button(run, "Главное меню", "menu")], "consultation-closed")
                return
            from app.api.routes.telegram_lead import _show_active_consultation
            await _show_active_consultation(self.s, active_consultation=request, interaction_id=f"dual:{run.id}:{run.revision}", include_subscription=False)
            return
        snapshot = context(run)
        request = ConsultationRequest(user_id=run.user_id, flow_run_id=run.id, intake_snapshot_json=snapshot,
            origin_type="ai_assistant_intro" if run.kind == "ai_assistant" else "business_intake", status="new")
        self.s.add(request)
        await self.s.flush()
        user = await self.s.get(User, run.user_id)
        user.lifecycle_stage = "consultation_requested"
        self.s.add(AttentionItem(user_id=run.user_id, consultation_request_id=request.id, kind="consultation_requested",
            reason=f"{snapshot['direction']}: {snapshot['priority_task'] or snapshot['business_goal']}", priority="normal", status="new"))
        self.s.add(Event(user_id=run.user_id, kind="dual_consultation_requested", payload_json={"run_id": str(run.id), "consultation_request_id": str(request.id), "kind": run.kind}))
        from app.services.ops_notifications import OpsNotificationService
        await OpsNotificationService(self.s).enqueue_created_consultation(request)
        await self.send(run, "Готово, ваше обращение получено!\n\nНаш эксперт увидит, чем вы занимаетесь и с чего хотите начать, и свяжется с вами здесь, в Telegram, чтобы договориться о разговоре.", [], "consultation-confirmed")
