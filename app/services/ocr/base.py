"""
Base OCR Provider interface and data models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class OcrExtractionResult:
    """Result of OCR extraction from an image."""

    extracted_profile: dict[str, Any]
    """Extracted tuning profile (same structure as TuningProfile API)."""

    provider: str
    """OCR provider used (e.g., 'anthropic')."""

    model: str
    """Model name (e.g., 'claude-opus-4-6')."""

    sections_found: list[str]
    """List of sections that had visible data (e.g., ['tires', 'suspension'])."""

    warnings: list[str]
    """Non-critical warnings (e.g., ambiguous values, unrecognized options)."""

    car_name: str | None = None
    """Car name detected in the screenshot, if visible (e.g., '911 GT3 RS (991) \'16')."""


class BaseOcrProvider(ABC):
    """
    Strategy interface for OCR extraction.
    Every OCR provider must implement this contract.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier, e.g., 'anthropic', 'google_vision', 'tesseract'."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model string, e.g., 'claude-opus-4-6' or 'vision-v1'."""
        ...

    @abstractmethod
    async def extract(
        self,
        image_bytes: bytes,
        media_type: str = "image/jpeg",
    ) -> OcrExtractionResult:
        """
        Extract tuning configuration from an image.

        Args:
            image_bytes: Raw image data (JPEG, PNG, WEBP, etc.)
            media_type: MIME type (e.g., 'image/jpeg')

        Returns:
            OcrExtractionResult with extracted profile and metadata.

        Raises:
            ValueError: If extraction fails or image is invalid.
        """
        ...
