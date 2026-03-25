import httpx

from app.core.config import get_settings
from app.services.llm.base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """Concrete strategy: Ollama (local / self-hosted models)."""

    def __init__(self):
        cfg = get_settings()
        self._base_url = cfg.ollama_base_url.rstrip("/")
        self._model = cfg.ollama_model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            content=data["message"]["content"],
            provider=self.provider_name,
            model=self._model,
        )
