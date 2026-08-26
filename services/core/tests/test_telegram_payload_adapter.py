from app.adapters.telegram_lead import ProfileAnswer, StartProfile, adapt_telegram_lead_payload


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
                "data": "profile:team_size:4–10",
            }
        }
    )

    assert action == ProfileAnswer(
        telegram_user_id="900001", question_code="team_size", value="4–10"
    )
    assert adapt_telegram_lead_payload({"message": {"chat": {}}}) is None
    assert adapt_telegram_lead_payload({"edited_message": {}}) is None
