"""Testes da normalização de modelos LiteLLM (AI_MODEL / overrides independentes do código)."""

from app.services.ia_service import normalize_litellm_model


def test_openrouter_prefix_preserved_even_if_ai_provider_openai():
    # Antes: AI_PROVIDER=openai podia deixar passar string estranha; agora prefixo openrouter/ é explícito.
    assert (
        normalize_litellm_model(
            "openrouter/elephant-alpha", provider="openai", raw=False
        )
        == "openrouter/elephant-alpha"
    )


def test_openrouter_vendor_model_prepended():
    assert (
        normalize_litellm_model("google/gemini-2.0-flash-001", provider="openrouter", raw=False)
        == "openrouter/google/gemini-2.0-flash-001"
    )


def test_openrouter_short_name_uses_openai_namespace():
    assert (
        normalize_litellm_model("gpt-4o-mini", provider="openrouter", raw=False)
        == "openrouter/openai/gpt-4o-mini"
    )


def test_anthropic_native_becomes_openrouter_when_provider_openrouter():
    assert (
        normalize_litellm_model(
            "anthropic/claude-3-5-sonnet-20240620", provider="openrouter", raw=False
        )
        == "openrouter/anthropic/claude-3-5-sonnet-20240620"
    )


def test_native_anthropic_preserved_when_provider_anthropic():
    assert (
        normalize_litellm_model(
            "anthropic/claude-3-5-sonnet-20240620", provider="anthropic", raw=False
        )
        == "anthropic/claude-3-5-sonnet-20240620"
    )


def test_google_alias_to_gemini_when_explicit():
    assert (
        normalize_litellm_model("google/gemini-pro", provider="openai", raw=False)
        == "gemini/gemini-pro"
    )


def test_raw_mode_preserves_unknown_prefix():
    assert (
        normalize_litellm_model("novo_provider/foo/bar", provider="openrouter", raw=True)
        == "novo_provider/foo/bar"
    )


def test_default_placeholder_maps_to_fallback():
    assert (
        normalize_litellm_model(
            "default",
            provider="openrouter",
            raw=False,
            fallback_model="gpt-4o-mini",
        )
        == "openrouter/openai/gpt-4o-mini"
    )


def test_custom_fallback_model_respected():
    assert (
        normalize_litellm_model(
            "",
            provider="openrouter",
            raw=False,
            fallback_model="openrouter/deepseek/deepseek-chat",
        )
        == "openrouter/deepseek/deepseek-chat"
    )
