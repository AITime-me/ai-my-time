"""Render only already persisted diagnostic data for the Telegram client view."""

from __future__ import annotations

from collections.abc import Mapping

from app.schemas.diagnostic_result_v2 import DiagnosticResultV2

CTA_TEXT = (
    "По вашим ответам уже видно направление, но точное решение зависит от того, "
    "как сейчас проходят обращения между каналами, сотрудниками и системами. "
    "На онлайн-консультации эксперт AI My Time разберёт этот процесс подробнее и поможет "
    "определить, что имеет смысл автоматизировать в первую очередь."
)


def render_telegram_diagnostic_result(report: DiagnosticResultV2) -> str:
    """The exact v2 client rendering used at completion and for a saved replay."""
    view = report.client_view
    blocks = [
        "Первичный разбор готов.",
        f"Что сейчас происходит\n{view.what_is_happening}",
        f"Где теряется результат\n{view.where_result_is_lost}",
        f"Как это может работать\n{view.future_process}",
        "Что может взять на себя система\n" + _bullets(view.system_responsibilities),
    ]
    if view.ai_responsibilities:
        blocks.append("Где может помочь AI\n" + _bullets(view.ai_responsibilities))
    blocks.append("Что останется человеку\n" + _bullets(view.human_responsibilities))
    if view.open_questions:
        blocks.append("Что ещё важно понять\n" + _bullets(view.open_questions))
    return "\n\n".join(blocks) + "\n\n" + CTA_TEXT


def render_legacy_telegram_diagnostic_result(
    *,
    summary: str,
    priorities: object,
    next_steps: object,
    role_split: object,
    limitations: object,
) -> str:
    """Replay legacy persisted fields without inventing or regenerating an AI result."""
    priority = _first_text(priorities, "reason") or "Сохранённый результат не содержит отдельного пояснения."
    next_step = _first_text(next_steps, "action") or "Сохранённый результат не содержит отдельного сценария."
    roles = role_split if isinstance(role_split, Mapping) else {}
    blocks = [
        "Первичный разбор готов.",
        f"Что сейчас происходит\n{summary}",
        f"Где теряется результат\n{priority}",
        f"Как это может работать\n{next_step}",
        "Что может взять на себя система\n" + _bullets(roles.get("automation")),
        "Что останется человеку\n" + _bullets(roles.get("human")),
        "Что ещё важно понять\n" + _bullets(limitations),
    ]
    ai = _bullets(roles.get("ai"), empty="")
    if ai:
        blocks.insert(5, "Где может помочь AI\n" + ai)
    return "\n\n".join(blocks) + "\n\n" + CTA_TEXT


def _first_text(value: object, key: str) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping) and isinstance(item.get(key), str) and item[key].strip():
                return item[key].strip()
    return None


def _bullets(value: object, *, empty: str = "Сохранённый результат не содержит отдельных пунктов.") -> str:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [item for item in value if isinstance(item, str) and item.strip()]
    else:
        values = []
    return "\n".join(f"• {item.strip()}" for item in values) if values else empty
