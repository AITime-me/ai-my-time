"""Run synthetic, non-production Diagnostic AI product-review scenarios.

Requires the already configured non-production Yandex settings. It never opens a
database, Telegram connection or file with customer data, and prints only the
validated product classification for synthetic inputs.
"""

from __future__ import annotations

import asyncio
import uuid

from app.adapters.yandex_diagnostic import YandexDiagnosticProvider
from app.core.settings import Settings
from app.services.diagnostic_generation import DiagnosticConversationInput


SCENARIOS = {
    "execution_gap": {
        "profile": ("Мессенджеры", "В чатах", "Заявки", "Не терять информацию"),
        "answers": [
            "Новую заявку видит менеджер в чате и вручную передаёт её смене.",
            "При передаче не фиксируют ответственного и следующий шаг, поэтому клиент иногда ждёт.",
            "Собственник узнаёт о задержке только когда сам спрашивает команду.",
        ],
    },
    "feedback_gap": {
        "profile": ("Реклама", "CRM", "Деньги", "Понимать качество лидов"),
        "answers": [
            "Менеджеры быстро квалифицируют заявки, но многие не подходят по ценовому сегменту.",
            "Причину отказа отмечают в CRM, но источник и рекламная кампания не связываются с продажами и маркетолог этого не видит.",
        ],
    },
    "observability_gap": {
        "profile": ("Мессенджеры", "В нескольких местах", "Контроль", "Понимать, что происходит"),
        "answers": [
            "Не знаю, где именно всё тормозит.",
            "Не знаю. Последний раз мне пришлось самому спрашивать, кто ответит клиенту.",
            "Статуса нет: пишут в разные чаты, и никто не видит, что уже сделано и что дальше.",
        ],
    },
    "growth_gap": {
        "profile": ("Сайт", "CRM", "Деньги", "Получать больше обращений"),
        "answers": [
            "Мы расширили команду и можем обслужить больше клиентов, но новых обращений стало недостаточно.",
            "Продажи обрабатывают текущие заявки нормально; проблема именно в том, что входящего потока мало.",
            "Нам нужен новый способ привести целевую аудиторию в первую коммуникацию, а не контроль менеджеров.",
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
    for name, scenario in SCENARIOS.items():
        session_id, user_id = uuid.uuid4(), uuid.uuid4()
        turns: list[tuple[str, str]] = []
        snapshot = _snapshot(scenario["profile"])
        final = None
        opening = await provider.advance(DiagnosticConversationInput(session_id, user_id, snapshot, turns))
        if opening.question is None:
            print(f"{name}: FAIL no opening question")
            continue
        turns.append(("assistant", opening.question))
        for answer in scenario["answers"]:
            turns.append(("user", answer))
            response = await provider.advance(DiagnosticConversationInput(session_id, user_id, snapshot, turns))
            if response.diagnostic is not None:
                final = response.diagnostic
                break
            if response.question is None:
                break
            turns.append(("assistant", response.question))
        if final is None:
            print(f"{name}: FAIL no validated v2 result after {sum(1 for actor, _ in turns if actor == 'user')} replies")
        else:
            print(f"{name}: OK types={','.join(final.problem_types)} solution={final.solution_class_id}")


if __name__ == "__main__":
    asyncio.run(_run())
