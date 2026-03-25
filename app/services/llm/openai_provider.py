from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """Concrete strategy: OpenAI."""

    def __init__(self):
        cfg = get_settings()
        self._client = AsyncOpenAI(api_key=cfg.openai_api_key)
        self._model = cfg.openai_model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=self._model,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )
