from app.schemas.diagnostic_result_v2 import DiagnosticResultV2
from app.services.diagnostic_dialogue import _telegram_report
from app.services.diagnostic_result_rendering import render_telegram_diagnostic_result


def test_renderer_uses_client_language_and_hides_optional_ai_block() -> None:
    result = DiagnosticResultV2.model_validate({
        "contract_version": "v2",
        "evidence": {"facts": ["В CRM не видно следующего шага"]},
        "mechanism": "Следующий шаг зависит от памяти менеджера.",
        "problem_types": ["execution_gap"],
        "problem_scale": "process",
        "solution_class_id": "crm_automation",
        "client_view": {
            "what_is_happening": "Менеджер ведёт следующий шаг вручную.",
            "where_result_is_lost": "Клиент ждёт, если менеджер не вернулся к обращению.",
            "future_process": "Система назначает следующий шаг и сигнализирует о задержке.",
            "system_responsibilities": ["Назначать следующий шаг"],
            "human_responsibilities": ["Вести нестандартные переговоры"],
        },
    })

    text = _telegram_report(result)

    assert "Что сейчас происходит" in text
    assert "Где может помочь AI" not in text
    assert "execution_gap" not in text
    assert "role_split" not in text
    assert render_telegram_diagnostic_result(result) == text
