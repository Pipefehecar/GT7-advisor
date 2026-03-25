"""
LLM Strategy Pattern
====================
Problem: we don't want to be tightly coupled to any single LLM provider.
         Switching from Anthropic to OpenAI (or a local Ollama model)
         should require zero changes outside this package.

Solution: Strategy Pattern
  - BaseLLMProvider  → the interface (abstract contract)
  - AnthropicProvider, OpenAIProvider, OllamaProvider → concrete strategies
  - LLMFactory       → resolves the right strategy from LLM_PROVIDER env var

To add a new provider (e.g. Gemini):
  1. Create app/services/llm/gemini_provider.py  implementing BaseLLMProvider
  2. Register it in factory.py  (_REGISTRY["gemini"] = GeminiProvider)
  Nothing else changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    role: str   # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLMProvider(ABC):
    """Strategy interface — every LLM provider must implement this contract."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier, e.g. 'anthropic'."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model string, e.g. 'claude-opus-4-6'."""
        ...

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Send a single-turn completion and return a normalised LLMResponse.
        Implementations must handle their own retry / error wrapping.
        """
        ...
