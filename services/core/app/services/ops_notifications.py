"""Interface boundary for the future private operations Telegram chat.

No token or chat id is required to exercise the lifecycle.  A deployment may
inject a concrete sender later; tests use RecordingOpsNotifier.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class OpsNotification:
    event_type: str
    consultation_id: str
    text: str

class OpsNotifier(Protocol):
    async def notify(self, notification: OpsNotification) -> None: ...

class RecordingOpsNotifier:
    def __init__(self) -> None: self.items: list[OpsNotification] = []
    async def notify(self, notification: OpsNotification) -> None: self.items.append(notification)
