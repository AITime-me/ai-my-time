from app.adapters.telegram_lead import (
    ConsultationRequest,
    DiagnosticText,
    ProfileAnswer,
    StartProfile,
    adapt_telegram_lead_payload,
)


def test_adapter_extracts_private_start_without_provider_client() -> None:
    action = adapt_telegram_lead_payload(
        {
            "update_id": 101,
            "message": {
                "chat": {"type": "private"},
                "from": {"id": 900001},
                "text": "/start conference_qr",
            },
        }
    )

    assert action == StartProfile(telegram_user_id="900001", entry_code="conference_qr")


def test_adapter_extracts_private_profile_answer_and_ignores_other_updates() -> None:
    action = adapt_telegram_lead_payload(
        {
            "callback_query": {
                "from": {"id": 900001},
                "message": {"chat": {"type": "private"}},
                "data": "profile:v2:3:team_size:1",
            }
        }
    )

    assert action == ProfileAnswer(
        telegram_user_id="900001", question_code="team_size", flow_version=3, option_index=1
    )
    legacy = adapt_telegram_lead_payload(
        {"callback_query": {"from": {"id": 900001}, "message": {"chat": {"type": "private"}}, "data": "profile:team_size:4–10"}}
    )
    assert legacy == ProfileAnswer(telegram_user_id="900001", question_code="team_size", value="4–10")
    assert adapt_telegram_lead_payload({"message": {"chat": {}}}) is None
    assert adapt_telegram_lead_payload({"edited_message": {}}) is None


def test_adapter_accepts_only_private_diagnostic_text_and_consultation_callback() -> None:
    text = adapt_telegram_lead_payload(
        {"message": {"chat": {"type": "private"}, "from": {"id": 900001}, "text": "Теряем заявки на смене"}}
    )
    assert text == DiagnosticText(telegram_user_id="900001", text="Теряем заявки на смене")
    callback = adapt_telegram_lead_payload(
        {"callback_query": {"from": {"id": 900001}, "message": {"chat": {"type": "private"}}, "data": "diagnostic:consult:123"}}
    )
    assert callback == ConsultationRequest(telegram_user_id="900001", diagnostic_session_id="123")
