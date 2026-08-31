"""Translate a bounded Telegram update payload into local Lead Bot inputs."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError


class _Chat(BaseModel):
    type: str


class _Sender(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class _Message(BaseModel):
    message_id: int | None = None
    chat: _Chat
    from_: _Sender | None = Field(default=None, alias="from")
    text: str | None = None


class _CallbackQuery(BaseModel):
    id: str
    from_: _Sender = Field(alias="from")
    message: _Message | None = None
    data: str | None = None


class _Update(BaseModel):
    update_id: int | None = None
    message: _Message | None = None
    callback_query: _CallbackQuery | None = None


@dataclass(frozen=True)
class StartProfile:
    telegram_user_id: str
    entry_code: str
    interaction_id: str
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None


@dataclass(frozen=True)
class ProfileAnswer:
    telegram_user_id: str
    callback_query_id: str
    question_code: str
    value: str | None = None
    flow_version: int | None = None
    option_index: int | None = None
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None


@dataclass(frozen=True)
class DiagnosticText:
    telegram_user_id: str
    text: str
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None


@dataclass(frozen=True)
class CommunicationCommand:
    telegram_user_id: str
    action: str
    interaction_id: str
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None


@dataclass(frozen=True)
class MenuCommand:
    """The single permanent Telegram commands-menu entrypoint."""

    telegram_user_id: str
    interaction_id: str
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None


@dataclass(frozen=True)
class ConsultationRequest:
    telegram_user_id: str
    callback_query_id: str
    diagnostic_session_id: str
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None

@dataclass(frozen=True)
class LifecycleCallback:
    telegram_user_id: str
    callback_query_id: str
    action: str
    entity_id: str
    interaction_id: str
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    telegram_username: str | None = None

TelegramLeadInput = StartProfile | ProfileAnswer | DiagnosticText | CommunicationCommand | MenuCommand | ConsultationRequest | LifecycleCallback


def adapt_telegram_lead_payload(payload: object) -> TelegramLeadInput | None:
    """Return a recognised private-chat action, otherwise ignore the update.

    Telegram may send update types this MVP does not use.  Invalid or unrelated
    payloads are deliberately non-actions so the webhook can acknowledge them
    without exposing a provider parser as an application contract.
    """
    try:
        update = _Update.model_validate(payload)
    except ValidationError:
        return None

    message = update.message
    if (
        message is not None
        and message.chat.type == "private"
        and message.from_ is not None
        and message.text is not None
    ):
        entry_code = _start_parameter(message.text)
        if entry_code is not None:
            return StartProfile(
                telegram_user_id=str(message.from_.id), entry_code=entry_code,
                interaction_id=_message_interaction_id(update, message), **_profile(message.from_)
            )
        if _is_menu_command(message.text):
            return MenuCommand(
                telegram_user_id=str(message.from_.id),
                interaction_id=_message_interaction_id(update, message),
                **_profile(message.from_),
            )
        action = _communication_action(message.text)
        if action is not None:
            return CommunicationCommand(telegram_user_id=str(message.from_.id), action=action, interaction_id=_message_interaction_id(update, message), **_profile(message.from_))
        if not message.text.strip().startswith("/"):
            return DiagnosticText(telegram_user_id=str(message.from_.id), text=message.text, **_profile(message.from_))

    callback = update.callback_query
    if (
        callback is None
        or callback.message is None
        or callback.message.chat.type != "private"
        or callback.data is None
    ):
        return None
    parsed = _profile_callback(callback.data)
    if parsed is not None:
        return ProfileAnswer(
            telegram_user_id=str(callback.from_.id),
            callback_query_id=callback.id,
            question_code=parsed[0],
            value=parsed[1],
            flow_version=parsed[2],
            option_index=parsed[3],
            **_profile(callback.from_),
        )
    if callback.data.startswith("diagnostic:consult:"):
        session_id = callback.data.removeprefix("diagnostic:consult:")
        if session_id:
            return ConsultationRequest(
                telegram_user_id=str(callback.from_.id),
                callback_query_id=callback.id,
                diagnostic_session_id=session_id,
                **_profile(callback.from_),
            )
    parts = callback.data.split(":")
    if len(parts) == 3 and ((parts[0] == "consult" and parts[1] in {"confirm", "reschedule", "cancel", "cancel_yes", "cancel_no"}) or (parts[0] == "diagnostic" and parts[1] in {"resume", "result", "repeat", "channel"}) or (parts[0] == "menu" and parts[1] == "show") or (parts[0] == "content" and parts[1] in {"subscribe", "unsubscribe"})):
        return LifecycleCallback(
            telegram_user_id=str(callback.from_.id),
            callback_query_id=callback.id,
            action=f"{parts[0]}:{parts[1]}",
            entity_id=parts[2],
            interaction_id=_callback_interaction_id(update, callback),
            **_profile(callback.from_),
        )
    return None


def _profile(sender: _Sender) -> dict[str, str | None]:
    return {
        "telegram_first_name": sender.first_name,
        "telegram_last_name": sender.last_name,
        "telegram_username": sender.username,
    }


def _message_interaction_id(update: _Update, message: _Message) -> str:
    if update.update_id is not None:
        return f"telegram-update:{update.update_id}"
    if message.message_id is not None:
        return f"telegram-message:{message.message_id}"
    raise ValueError("Telegram navigation update is missing an interaction identity")


def _callback_interaction_id(update: _Update, callback: _CallbackQuery) -> str:
    if update.update_id is not None:
        return f"telegram-update:{update.update_id}"
    return f"telegram-callback:{callback.id}"


def _start_parameter(text: str) -> str | None:
    parts = text.strip().split(maxsplit=1)
    if not parts or parts[0] != "/start":
        return None
    return parts[1].strip() if len(parts) == 2 else "telegram_direct"


def _communication_action(text: str) -> str | None:
    command = text.strip().split(maxsplit=1)[0].casefold()
    if command == "/stop":
        return "unsubscribe"
    if command == "/subscribe":
        return "subscribe"
    return None


def _is_menu_command(text: str) -> bool:
    command = text.strip().split(maxsplit=1)[0].casefold()
    return command == "/menu" or command.startswith("/menu@")


def _profile_callback(data: str) -> tuple[str, str | None, int | None, int | None] | None:
    prefix, separator, remainder = data.partition(":")
    if prefix != "profile" or not separator:
        return None
    if remainder.startswith("v2:"):
        _, _, remainder = remainder.partition(":")
        version_text, separator, remainder = remainder.partition(":")
        if not separator or not version_text.isdecimal() or int(version_text) < 1:
            return None
        question_code, separator, value = remainder.partition(":")
        if not question_code or not separator or not value.isdecimal():
            return None
        return question_code, None, int(version_text), int(value)
    question_code, separator, value = remainder.partition(":")
    if not question_code or not separator or not value:
        return None
    # Legacy callback payloads intentionally carry no flow version. They stay
    # parseable only so the state machine can reject them safely for v2.
    return question_code, value, None, None
