"""
LLMFactory
----------
Reads LLM_PROVIDER from the environment and returns the matching strategy.

Registry is a plain dict so adding a provider is one line:
  _REGISTRY["gemini"] = GeminiProvider
"""

from app.core.config import get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import BaseLLMProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.openai_provider import OpenAIProvider

_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def create_llm_provider(name: str | None = None) -> BaseLLMProvider:
    provider_name = (name or get_settings().llm_provider).lower()
    if provider_name not in _REGISTRY:
        raise ValueError(
            f"Unknown LLM provider '{provider_name}'. "
            f"Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[provider_name]()


# FastAPI dependency — one instance per process
_instance: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    global _instance
    if _instance is None:
        _instance = create_llm_provider()
    return _instance
