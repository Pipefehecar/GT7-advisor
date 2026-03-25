import anthropic

from app.core.config import get_settings
from app.services.llm.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Concrete strategy: Anthropic Claude."""

    def __init__(self):
        cfg = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key)
        self._model = cfg.anthropic_model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return LLMResponse(
            content=msg.content[0].text,
            provider=self.provider_name,
            model=self._model,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )
