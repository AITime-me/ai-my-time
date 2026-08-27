from app.diagnostic_assets import load_diagnostic_prompt_bundle


def test_diagnostic_prompt_assets_are_versioned_and_separated() -> None:
    bundle = load_diagnostic_prompt_bundle()
    assert bundle.version == "v1"
    assert "Never state a price" in bundle.guardrails
    assert "context-sensitive Russian questions" in bundle.prompt
    assert "first contact" in bundle.knowledge_base
    assert bundle.price_reply.startswith("Стоимость автоматизации рассчитывается индивидуально")
