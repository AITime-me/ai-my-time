"""First durable step of QR → Lead Bot → profile for conference_2026."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConferenceEntry, Event, Touchpoint, User, UserIdentity
from app.schemas.conference import ConferenceStartCommand, ConferenceStartResult

_TELEGRAM_PROVIDER = "telegram"
_LEAD_BOT_SCOPE = "ai_my_time_lead_bot"
_CONFERENCE_SOURCE = "conference_2026"


class ConferenceIntakeService:
    """Idempotently turn an already-validated bot start into durable state.

    The calling adapter owns authentication, Telegram signature/update checks,
    and the database transaction. This service does no network I/O.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, command: ConferenceStartCommand) -> ConferenceStartResult:
        identity = await self._session.scalar(
            select(UserIdentity).where(
                UserIdentity.provider == _TELEGRAM_PROVIDER,
                UserIdentity.connection_scope == _LEAD_BOT_SCOPE,
                UserIdentity.external_id == command.telegram_user_id,
            )
        )
        created_user = identity is None
        if identity is None:
            user = User(lifecycle_stage="profiling")
            self._session.add(user)
            await self._session.flush()
            identity = UserIdentity(
                user_id=user.id,
                provider=_TELEGRAM_PROVIDER,
                connection_scope=_LEAD_BOT_SCOPE,
                external_id=command.telegram_user_id,
            )
            self._session.add(identity)
            await self._session.flush()
        else:
            user = await self._session.get(User, identity.user_id)
            if user is None:
                raise RuntimeError("identity refers to a missing user")
            if user.lifecycle_stage == "new":
                user.lifecycle_stage = "profiling"

        entry = await self._session.scalar(
            select(ConferenceEntry).where(
                ConferenceEntry.user_id == user.id,
                ConferenceEntry.conference_code == command.conference_code,
            )
        )
        created_entry = entry is None
        if entry is None:
            entry = ConferenceEntry(
                user_id=user.id,
                conference_code=command.conference_code,
                qr_code=command.qr_code,
                status="started",
            )
            self._session.add(entry)
            self._session.add(
                Touchpoint(
                    user_id=user.id,
                    source_code=_CONFERENCE_SOURCE,
                    entry_code=command.entry_code or command.qr_code,
                    metadata_json={"conference_code": command.conference_code},
                )
            )
            self._session.add(
                Event(
                    user_id=user.id,
                    kind="conference_entry_started",
                    payload_json={"conference_code": command.conference_code},
                )
            )
            await self._session.flush()

        return ConferenceStartResult(
            user_id=user.id,
            conference_entry_id=entry.id,
            created_user=created_user,
            created_entry=created_entry,
            next_stage=user.lifecycle_stage,
        )
