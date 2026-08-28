"""Run synthetic, non-production Diagnostic AI product-review scenarios.

Requires the already configured non-production Yandex settings. It never opens a
database, Telegram connection or file with customer data, and prints only the
validated product classification for synthetic inputs.
"""

from __future__ import annotations

import asyncio
import uuid

from app.adapters.yandex_diagnostic import YandexDiagnosticProvider, YandexDiagnosticProviderError
from app.core.settings import Settings
from app.services.diagnostic_generation import DiagnosticConversationInput


SCENARIOS = {
    "execution_gap": {
        "profile": ("Мессенджеры", "В чатах", "Заявки", "Не терять информацию"),
        "required_types": {"execution_gap"},
        "solution_ids": {"crm_implementation", "lead_intake_contour"},
        "answers": [
            "Новую заявку видит менеджер в чате и вручную передаёт её смене.",
            "При передаче не фиксируют ответственного и следующий шаг, поэтому клиент иногда ждёт.",
            "Собственник узнаёт о задержке только когда сам спрашивает команду.",
            "Другого канала или отдельной CRM у нас нет.",
        ],
    },
    "feedback_gap": {
        "profile": ("Реклама", "CRM", "Деньги", "Понимать качество лидов"),
        "required_types": {"feedback_gap"},
        "solution_ids": {"integrations_data_exchange"},
        "answers": [
            "Менеджеры быстро квалифицируют заявки, но многие не подходят по ценовому сегменту.",
            "Причину отказа отмечают в CRM, но источник и рекламная кампания не связываются с продажами и маркетолог этого не видит.",
            "В маркетинг эти причины и продажи автоматически не возвращаются.",
            "Других разрывов в этом фрагменте я не вижу.",
        ],
    },
    "observability_gap": {
        "profile": ("Мессенджеры", "В нескольких местах", "Контроль", "Понимать, что происходит"),
        "required_types": {"observability_gap"},
        "solution_ids": {"lead_intake_contour"},
        "answers": [
            "Не знаю, где именно всё тормозит.",
            "Не знаю. Последний раз мне пришлось самому спрашивать, кто ответит клиенту.",
            "Статуса нет: пишут в разные чаты, и никто не видит, что уже сделано и что дальше.",
            "Отдельной CRM с ответственным и следующим шагом нет.",
        ],
    },
    "growth_gap": {
        "profile": ("Сайт", "CRM", "Деньги", "Получать больше обращений"),
        "required_types": {"growth_gap"},
        "solution_ids": {"digital_lead_generation_product"},
        "answers": [
            "Мы расширили команду и можем обслужить больше клиентов, но новых обращений стало недостаточно.",
            "Продажи обрабатывают текущие заявки нормально; проблема именно в том, что входящего потока мало.",
            "Нам нужен новый способ привести целевую аудиторию в первую коммуникацию, а не контроль менеджеров.",
            "Текущая реклама не даёт достаточного потока для выросшей мощности.",
        ],
    },
}


def _snapshot(values: tuple[str, str, str, str]) -> dict[str, object]:
    flow, tools, pain, goal = values
    return {"profile_answers": {
        "business_type": {"value": "Услуги"}, "team_size": {"value": "11–30"},
        "client_flow": {"value": flow}, "current_tools": {"value": tools},
        "primary_pain": {"value": pain}, "automation_goal": {"value": goal},
    }}


async def _run() -> None:
    provider = YandexDiagnosticProvider(Settings())
    failures = 0
    for name, scenario in SCENARIOS.items():
        scenario_failed = False
        session_id, user_id = uuid.uuid4(), uuid.uuid4()
        turns: list[tuple[str, str]] = []
        snapshot = _snapshot(scenario["profile"])
        final = None
        try:
            opening = await provider.advance(DiagnosticConversationInput(session_id, user_id, snapshot, turns))
        except YandexDiagnosticProviderError:
            print(f"{name}: FAIL provider response at opening")
            failures += 1
            continue
        if opening.question is None:
            print(f"{name}: FAIL no opening question")
            failures += 1
            continue
        turns.append(("assistant", opening.question))
        for answer in scenario["answers"]:
            turns.append(("user", answer))
            try:
                response = await provider.advance(DiagnosticConversationInput(session_id, user_id, snapshot, turns))
            except YandexDiagnosticProviderError:
                print(f"{name}: FAIL invalid provider response")
                failures += 1
                scenario_failed = True
                break
            if response.diagnostic is not None:
                final = response.diagnostic
                break
            if response.question is None:
                break
            turns.append(("assistant", response.question))
        if scenario_failed:
            continue
        if final is None:
            print(f"{name}: FAIL no validated v2 result after {sum(1 for actor, _ in turns if actor == 'user')} replies")
            failures += 1
        elif not scenario["required_types"].issubset(final.problem_types):
            print(f"{name}: FAIL types={','.join(final.problem_types)}")
            failures += 1
        elif final.solution_class_id not in scenario["solution_ids"]:
            print(f"{name}: FAIL solution={final.solution_class_id}")
            failures += 1
        else:
            print(f"{name}: OK types={','.join(final.problem_types)} solution={final.solution_class_id}")
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    asyncio.run(_run())
