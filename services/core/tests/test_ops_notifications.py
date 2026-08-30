import asyncio
from app.services.ops_notifications import OpsNotification, RecordingOpsNotifier

def test_ops_notification_test_double_has_no_runtime_credential_dependency() -> None:
    notifier = RecordingOpsNotifier()
    asyncio.run(notifier.notify(OpsNotification(event_type="repeat_task", consultation_id="x", text="Повторное обращение — новая задача")))
    assert notifier.items[0].event_type == "repeat_task"
