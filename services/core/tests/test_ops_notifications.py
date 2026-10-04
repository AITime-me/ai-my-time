import asyncio
from app.services.ops_notifications import OpsNotification, RecordingOpsNotifier
from app.services.ops_notifications import (
    _render,
    _render_website_diagnostic_completed,
    _render_website_start,
)
from app.models import User

def test_ops_notification_test_double_has_no_runtime_credential_dependency() -> None:
    notifier = RecordingOpsNotifier()
    asyncio.run(notifier.notify(OpsNotification(event_type="repeat_task", consultation_id="x", text="Повторное обращение — новая задача")))
    assert notifier.items[0].event_type == "repeat_task"


def test_ops_message_contains_only_the_operational_consultation_context() -> None:
    message = _render(
        event_type="repeat_task",
        user=User(display_name="Светлана", telegram_username="Kuznecova_Lana"),
        source="conference_qr", campaign="august", segment="Услуги",
        summary="Не используется", repeat_task_text="Собрать заявки из всех каналов.",
    )
    assert "Светлана" in message and "@Kuznecova_Lana" in message
    assert "Источник: conference_qr" in message and "Кампания: august" in message
    assert "Сегмент бизнеса: Услуги" in message
    assert "Собрать заявки из всех каналов." in message
    assert "Не используется" not in message
    assert "consultation_id" not in message and "uuid" not in message


def test_ops_repeat_task_includes_radar_interest_when_intent_present() -> None:
    message = _render(
        event_type="repeat_task",
        user=User(display_name="Анна", telegram_username="anna"),
        source="Сайт · AI-консультант",
        campaign=None,
        segment="Услуги",
        summary=None,
        repeat_task_text="интересует радар спроса",
        intent="radar",
    )
    assert "Интерес: Радар спроса" in message
    assert "интересует радар спроса" in message


def test_website_radar_start_notification_contains_no_numeric_identity_or_message() -> None:
    message = _render_website_start(
        user=User(
            display_name="Анна Иванова",
            telegram_username="anna_owner",
        ),
        source="Сайт · AI-консультант",
        intent="radar",
    )

    assert message.startswith("Новый переход в диагностику с сайта")
    assert "Источник: Сайт · AI-консультант" in message
    assert "Интерес: Радар спроса" in message
    assert "Анна Иванова" in message and "@anna_owner" in message
    assert "910001" not in message
    assert "текст сообщения" not in message


def test_website_completed_notification_is_concise_and_operational() -> None:
    message = _render_website_diagnostic_completed(
        user=User(display_name="Анна", telegram_username="anna"),
        source="Сайт · Контакты",
        intent="general",
        business_type="Услуги",
        main_task="Не забывать вернуться к клиенту",
        summary="Итог " + "очень длинный " * 100,
    )

    assert "Диагностика с сайта завершена" in message
    assert "Тип бизнеса: Услуги" in message
    assert "Основная задача: Не забывать вернуться к клиенту" in message
    assert "Радар спроса" not in message
    assert len(message) < 1000
