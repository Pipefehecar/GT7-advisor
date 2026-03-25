# GT7 AI Setup Advisor

Telemetry-powered setup suggestions for Gran Turismo 7.

Listens to the PS4/PS5 UDP stream, stores lap data, and uses an LLM
to recommend car setup changes based on observed driving behaviour.

---

## Architecture

```
GT7 (PS4/PS5)
    │  UDP :33740
    ▼
TelemetryService          ← background thread, detects behaviour events
    │  LapSummary
    ▼
PostgreSQL / SQLite        ← sessions, laps, suggestions
    │
    ▼
PromptBuilder             ← builds LLM context from telemetry + car profile
    │
    ▼
LLMFactory (Strategy)     ← resolves provider from LLM_PROVIDER env var
    ├── AnthropicProvider
    ├── OpenAIProvider
    └── OllamaProvider
    │
    ▼
FastAPI REST API           ← /cars  /sessions  /telemetry
```

### LLM Strategy Pattern

Switching LLM provider = change one env variable:

```
LLM_PROVIDER=anthropic   # default
LLM_PROVIDER=openai
LLM_PROVIDER=ollama      # local models
```

To add a new provider (e.g. Gemini):
1. Create `app/services/llm/gemini_provider.py` implementing `BaseLLMProvider`
2. Add one line to `factory.py`: `_REGISTRY["gemini"] = GeminiProvider`

---

## Quick Start

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and PS_IP at minimum

docker compose up --build
```

API docs: http://localhost:8000/docs

---

## Switch to PostgreSQL

```bash
# In .env:
DATABASE_URL=postgresql+asyncpg://gt7:gt7pass@db:5432/gt7_advisor

docker compose --profile postgres up --build
```

---

## Typical workflow

```
1. POST /cars/sync-catalog          → pull GT7 car list from ddm999
2. PUT  /cars/{id}/tuning-profile   → define adjustable params + ranges
3. POST /sessions/                  → create a session (car + track + manual config)
4. Drive in GT7 — laps auto-saved via telemetry listener
   OR POST /sessions/{id}/laps      → add laps manually for testing
5. POST /sessions/{id}/suggest      → get AI setup recommendations
6. GET  /sessions/{id}/suggestions  → review past suggestions
```

---

## Parámetros de tuning (`manual_config`)

Al crear una sesión, `manual_config` debe reflejar los valores actuales del garage en GT7.
Las keys corresponden a las siguientes opciones en español:

### Suspensión
| Key | GT7 (ES) |
|---|---|
| `spring_rate_front` | Muelle (Frecuencia natural) — Delantera |
| `spring_rate_rear` | Muelle (Frecuencia natural) — Trasera |
| `ride_height_front` | Punto de altura de carrocería — Delantera |
| `ride_height_rear` | Punto de altura de carrocería — Trasera |
| `damper_bump_front` | Amortiguación (compresión) — Delantera |
| `damper_bump_rear` | Amortiguación (compresión) — Trasera |
| `damper_rebound_front` | Amortiguación (expansión) — Delantera |
| `damper_rebound_rear` | Amortiguación (expansión) — Trasera |
| `arb_front` | Barra anti-roll — Delantera |
| `arb_rear` | Barra anti-roll — Trasera |
| `camber_front` | Ángulo de caída — Delantero |
| `camber_rear` | Ángulo de caída — Trasero |
| `toe_front` | Ángulo de convergencia — Delantero |
| `toe_rear` | Ángulo de convergencia — Trasero |

### Aerodinámica
| Key | GT7 (ES) |
|---|---|
| `downforce_front` | Carga aerodinámica — Delantera |
| `downforce_rear` | Carga aerodinámica — Trasera |

### Diferencial / LSD
| Key | GT7 (ES) |
|---|---|
| `initial_torque` | Par inicial |
| `accel_sensitivity` | Sensibilidad de aceleración |
| `decel_sensitivity` | Sensibilidad de desaceleración |

### Transmisión
| Key | GT7 (ES) |
|---|---|
| `final_drive` | Relación de transmisión final |
| `gear_1` … `gear_7` | 1ª marcha … 7ª marcha |

### Frenos
| Key | GT7 (ES) |
|---|---|
| `front_bias` | Balance delantero/trasero |

> Solo incluye los parámetros que tu auto tiene disponibles para ajustar.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | SQLite | Full SQLAlchemy async URL |
| `PS_IP` | `192.168.1.100` | PlayStation local IP |
| `LLM_PROVIDER` | `anthropic` | `anthropic` / `openai` / `ollama` |
| `ANTHROPIC_API_KEY` | — | Required if provider=anthropic |
| `ANTHROPIC_MODEL` | `claude-opus-4-6` | Model string |
| `OPENAI_API_KEY` | — | Required if provider=openai |
| `OPENAI_MODEL` | `gpt-4o` | Model string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `llama3` | Local model name |
| `GT7_CARS_CSV_URL` | ddm999 GitHub Pages | Community car list |

---

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```
