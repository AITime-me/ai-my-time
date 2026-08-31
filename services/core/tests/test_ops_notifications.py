import asyncio
from app.services.ops_notifications import OpsNotification, RecordingOpsNotifier
from app.services.ops_notifications import _render
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
