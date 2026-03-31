"""
OCR Strategy Pattern
====================
Problem: we don't want to be tightly coupled to any single OCR provider.
         Vision extraction could use Claude Vision, Google Vision, Tesseract, etc.
         Switching providers should require zero changes outside this package.

Solution: Strategy Pattern
  - BaseOcrProvider    → the interface (abstract contract)
  - AnthropicOcrProvider  → concrete strategy (Claude Vision)
  - GoogleVisionOcrProvider → concrete strategy (Google Cloud Vision) [future]
  - OcrFactory         → resolves the right strategy from OCR_PROVIDER env var

To add a new provider (e.g. Google Vision):
  1. Create app/services/ocr/google_vision.py implementing BaseOcrProvider
  2. Register it in factory.py (_REGISTRY["google_vision"] = GoogleVisionOcrProvider)
  Nothing else changes.
"""

from app.services.ocr.base import BaseOcrProvider, OcrExtractionResult
from app.services.ocr.factory import get_ocr_provider

__all__ = ["BaseOcrProvider", "OcrExtractionResult", "get_ocr_provider"]
