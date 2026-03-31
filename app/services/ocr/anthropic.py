"""
Anthropic Claude Vision OCR provider.
Uses Claude's multimodal capabilities to extract GT7 tuning data from screenshots.
"""

import base64
import json
from typing import Any

import anthropic

from app.core.config import get_settings
from app.services.ocr.base import BaseOcrProvider, OcrExtractionResult
from app.services.vision_extractor import normalize_extracted_profile

# todo: this must be in english, llms are cheaper and more accurate in english. We can add a translation step in the prompt if needed, but let's see how it performs first.
# System prompt for Claude Vision extraction
CLAUDE_SYSTEM_PROMPT = """Eres un extractor de datos de configuración del videojuego Gran Turismo 7.
El usuario te enviará una captura de pantalla de la "Hoja de configuración" del juego.
Tu única tarea: extraer todos los valores visibles y devolver ÚNICAMENTE un objeto JSON válido.

REGLAS ESTRICTAS:
1. Devuelve SOLO el JSON. Sin markdown, sin explicaciones, sin texto adicional.
2. Si un valor no es visible o no puedes leerlo con certeza, omite esa clave.
3. Para valores numéricos: usa número (no string). Ej: 65, no "65".
4. Para valores de selección: usa el string exacto que ves en pantalla.
5. La pantalla puede mostrar solo una página. Extrae lo que esté visible.
6. Los valores Min/Max pueden aparecer como rango o como límites del slider.
7. Solo devuelve el JSON, sin ningún delimitador de código markdown."""


class AnthropicOcrProvider(BaseOcrProvider):
    """OCR provider using Anthropic's Claude Vision."""

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

    async def extract(
        self,
        image_bytes: bytes,
        media_type: str = "image/jpeg",
    ) -> OcrExtractionResult:
        """Extract tuning data using Claude Vision."""
        # Convert image to base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Build the user prompt with expected JSON structure
        user_prompt = """Extrae todos los parámetros de tunning visibles en esta imagen de GT7.
Devuelve el JSON con esta estructura exacta. Incluye solo las secciones visibles.

ESTRUCTURA ESPERADA:
{
  "car_name": "<nombre del vehículo visible en la esquina superior izquierda, sin número de catálogo>",
  "tires": {
    "selections": {
      "compound_front": "<valor>",
      "compound_rear": "<valor>"
    }
  },
  "suspension": {
    "current": {
      "ride_height_front": <número>,
      "ride_height_rear": <número>,
      "arb_front": <número>,
      "arb_rear": <número>,
      "damper_bump_front": <número>,
      "damper_bump_rear": <número>,
      "damper_rebound_front": <número>,
      "damper_rebound_rear": <número>,
      "natural_frequency_front": <número>,
      "natural_frequency_rear": <número>,
      "camber_front": <número>,
      "camber_rear": <número>,
      "toe_front": <número>,
      "toe_rear": <número>
    }
  },
  "aerodynamics": {
    "current": {
      "downforce_front": <número>,
      "downforce_rear": <número>,
      "power_output": <número>
    }
  },
  "weight_balance": {
    "current": {
      "ballast": <número>,
      "ballast_position": <número>,
      "power_limiter": <número>
    }
  },
  "differential": {
    "current": {
      "initial_torque_rear": <número>,
      "accel_sensitivity_rear": <número>,
      "decel_sensitivity_rear": <número>,
      "initial_torque_front": <número>,
      "accel_sensitivity_front": <número>,
      "decel_sensitivity_front": <número>,
      "torque_distribution": <número>
    },
    "selections": {
      "torque_vectoring": "<valor>"
    }
  },
  "transmission": {
    "current": {
      "top_speed": <número>,
      "final_drive": <número>,
      "gear_1": <número>,
      "gear_2": <número>,
      "gear_3": <número>,
      "gear_4": <número>,
      "gear_5": <número>,
      "gear_6": <número>,
      "gear_7": <número>
    }
  },
  "nitro": {
    "selections": {
      "enabled": "<Sí/No>"
    },
    "current": {
      "output": <número>
    }
  },
  "supercharger": {
    "selections": {
      "turbo": "<valor>",
      "anti_lag": "<valor>",
      "intercooler": "<valor>",
      "supercharger": "<valor>"
    }
  },
  "intake_exhaust": {
    "selections": {
      "air_filter": "<valor>",
      "muffler": "<valor>"
    }
  },
  "brakes": {
    "selections": {
      "brake_system": "<valor>",
      "brake_pads": "<valor>",
      "handbrake": "<valor>"
    },
    "current": {
      "brake_bias": <número>,
      "handbrake_torque": <número>
    }
  },
  "steering": {
    "selections": {
      "steering_kit": "<valor>",
      "all_wheel_steering": "<valor>"
    },
    "current": {
      "rear_steering_angle": <número>
    }
  },
  "drivetrain": {
    "selections": {
      "clutch": "<valor>",
      "drive_shaft": "<valor>"
    }
  },
  "engine_mods": {
    "selections": {
      "boring": "<valor>",
      "stroke_increase": "<valor>",
      "displacement_increase": "<valor>",
      "valve_timing": "<valor>",
      "valve_lift_amount": "<valor>",
      "compression_ratio": "<valor>",
      "titanium_exhaust": "<valor>",
      "lightweight_flywheel": "<valor>",
      "racing_engine_computer": "<valor>",
      "all_wheel_drive_convert": "<valor>",
      "custom_transmission": "<valor>",
      "transmission_oil_cooler": "<valor>",
      "racing_transmission": "<valor>",
      "carbon_driveshaft": "<valor>"
    }
  },
  "body": {
    "selections": {
      "weight_reduction_1": "<valor>",
      "weight_reduction_2": "<valor>",
      "weight_reduction_3": "<valor>",
      "weight_reduction_4": "<valor>",
      "weight_reduction_5": "<valor>"
    }
  }
}

NOTAS:
- Solo incluye valores que puedas ver claramente en la imagen
- Omite secciones vacías o no visibles
- Para valores de selección, usa el string EXACTO que aparece en la pantalla
- Para números, usa números puros (no strings)
- La pantalla puede mostrar solo una página; extrae lo que esté visible"""

        # Call Claude Vision
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
        )

        # Parse response
        response_text = msg.content[0].text
        try:
            extracted_data = self._parse_json_response(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Claude Vision: {e}")

        # Extract car name before normalization (it's not a tuning section)
        car_name: str | None = extracted_data.pop("car_name", None)
        if car_name and not isinstance(car_name, str):
            car_name = None

        # Normalize selection values using shared utility
        normalized_data, warnings = normalize_extracted_profile(extracted_data)

        # Extract sections found
        sections_found = [k for k in normalized_data if normalized_data[k]]

        return OcrExtractionResult(
            extracted_profile=normalized_data,
            provider=self.provider_name,
            model=self._model,
            sections_found=sections_found,
            warnings=warnings,
            car_name=car_name,
        )

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Parse JSON from Claude's response, handling markdown code blocks."""
        text = text.strip()

        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Remove markdown code block if present
        if text.startswith("```"):
            # Try to extract JSON from code block
            import re

            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
            else:
                # Fallback: find first { and last }
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    text = text[start : end + 1]

        return json.loads(text)
