import pytest

from app.diagnostic_assets import (
    load_diagnostic_prompt_bundle,
    load_diagnostic_result_contract,
    load_solution_catalog,
    validate_diagnostic_result_v2,
)


def test_diagnostic_prompt_assets_are_versioned_and_separated() -> None:
    bundle = load_diagnostic_prompt_bundle()
    assert bundle.version == "v1"
    assert "Never state a price" in bundle.guardrails
    assert "context-sensitive Russian questions" in bundle.prompt
    assert "first contact" in bundle.knowledge_base
    assert bundle.price_reply.startswith("Стоимость автоматизации рассчитывается индивидуально")


def test_solution_catalog_is_versioned_and_has_only_real_product_classes() -> None:
    catalog = load_solution_catalog()

    assert catalog.version == "v1"
    assert len(catalog.solution_classes) == 10
    assert {item.id for item in catalog.solution_classes} >= {
        "crm_implementation",
        "ai_employee",
        "digital_lead_generation_product",
        "point_automation",
    }
    assert all(item.when_to_consider and item.boundaries and item.includes for item in catalog.solution_classes)


def test_result_contract_v2_is_separate_and_validates_catalog_membership() -> None:
    asset = load_diagnostic_result_contract()
    payload = {
        "contract_version": "v2",
        "evidence": {"facts": ["Заявки приходят в несколько чатов"]},
        "mechanism": "Передача между сменами не фиксируется, поэтому следующий шаг теряется.",
        "problem_types": ["execution_gap", "observability_gap"],
        "problem_scale": "process",
        "solution_class_id": "lead_intake_contour",
        "client_view": {
            "what_is_happening": "Обращения передаются вручную.",
            "where_result_is_lost": "Не видно ответственного и следующего шага.",
            "future_process": "Каждое обращение фиксируется и передаётся с ответственным.",
            "system_responsibilities": ["Фиксировать передачу и следующий шаг"],
            "human_responsibilities": ["Решать нестандартные случаи"],
        },
    }

    result = validate_diagnostic_result_v2(payload)

    assert asset["contract_version"] == "v2"
    assert result.solution_class_id == "lead_intake_contour"
    with pytest.raises(ValueError, match="unknown solution class"):
        validate_diagnostic_result_v2({**payload, "solution_class_id": "invented_service"})
