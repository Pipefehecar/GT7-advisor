"""
OCR Provider Factory.
Reads OCR_PROVIDER from the environment and returns the matching strategy.
"""

from app.core.config import get_settings
from app.services.ocr.anthropic import AnthropicOcrProvider
from app.services.ocr.base import BaseOcrProvider

_REGISTRY: dict[str, type[BaseOcrProvider]] = {
    "anthropic": AnthropicOcrProvider,
    # "google_vision": GoogleVisionOcrProvider,  # add in future
    # "tesseract": TesseractOcrProvider,         # add in future
}


def create_ocr_provider(name: str | None = None) -> BaseOcrProvider:
    """Create an OCR provider by name."""
    provider_name = (name or get_settings().ocr_provider).lower()
    if provider_name not in _REGISTRY:
        raise ValueError(
            f"Unknown OCR provider '{provider_name}'. "
            f"Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[provider_name]()


# FastAPI dependency — one instance per process
_instance: BaseOcrProvider | None = None


def get_ocr_provider() -> BaseOcrProvider:
    """FastAPI dependency for OCR provider."""
    global _instance
    if _instance is None:
        _instance = create_ocr_provider()
    return _instance
