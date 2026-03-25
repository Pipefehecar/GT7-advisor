"""
Unit tests for the LLM Strategy / Factory pattern.
These run without hitting any real API.
"""

import pytest

from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.factory import create_llm_provider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.openai_provider import OpenAIProvider


def test_factory_returns_anthropic():
    provider = create_llm_provider("anthropic")
    assert isinstance(provider, AnthropicProvider)
    assert provider.provider_name == "anthropic"


def test_factory_returns_openai():
    provider = create_llm_provider("openai")
    assert isinstance(provider, OpenAIProvider)
    assert provider.provider_name == "openai"


def test_factory_returns_ollama():
    provider = create_llm_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_name == "ollama"


def test_factory_unknown_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_llm_provider("gemini_not_yet")


def test_providers_share_interface():
    """All providers must expose provider_name and model_name."""
    for name in ("anthropic", "openai", "ollama"):
        p = create_llm_provider(name)
        assert isinstance(p.provider_name, str)
        assert isinstance(p.model_name, str)
