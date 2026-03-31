"""
Prompt Builder
--------------
Builds system + user prompts from session data.
The LLM is instructed to respond with structured JSON so the frontend
can render the suggestions as cards (matching the GT7 in-game UI style).
"""

from app.db.models import Car, Lap, Session

SYSTEM_PROMPT = """\
You are an expert Gran Turismo 7 race engineer with deep knowledge of car dynamics.

Your task: analyse telemetry data from a driving session and suggest concrete
setup changes to improve lap time and car balance.

RESPONSE FORMAT — return ONLY a valid JSON object, no markdown, no extra text:
{
  "summary": "<1-2 sentence overall assessment in Spanish>",
  "recommendations": [
    {
      "section": "<section_key e.g. suspension>",
      "section_label": "<label exactly as shown in GT7 in Spanish e.g. Suspensión>",
      "parameter_key": "<param_key e.g. ride_height_front>",
      "parameter_label": "<label exactly as shown in GT7 in Spanish e.g. Ajuste de altura de carrocería (Del.)>",
      "current_value": "<current value as string>",
      "suggested_value": "<suggested value as string>",
      "unit": "<unit string or null e.g. mm, Hz, %, km/h>",
      "reason": "<explanation in Spanish referencing specific telemetry numbers>"
    }
  ]
}

STRICT RULES:
1. Only suggest changes to parameters listed under AVAILABLE TUNING SECTIONS.
   If a section is absent, do NOT mention it.
2. For numeric params: give a specific value within the stated [min, max] range.
3. For selection params: choose from the available options listed.
4. Link every recommendation to a specific telemetry observation.
5. Maximum 7 recommendations, ordered by expected impact.
6. Use Spanish labels exactly as they appear in Gran Turismo 7.
7. Return ONLY the JSON object — no surrounding text, no markdown code fences.
"""


def build_prompt(session: Session, car: Car | None, laps: list[Lap]) -> str:
    lines: list[str] = []

    # ── Context ───────────────────────────────────────────────────────────────
    car_name = car.name if car else "Unknown car"
    category = (car.category if car else None) or "Unknown category"
    lines += [
        f"## Car: {car_name}   |   Category: {category}",
        f"## Track: {session.track_name}",
        "",
    ]

    # ── Current manual config ────────────────────────────────────────────────
    cfg = session.manual_config or {}
    if cfg:
        lines.append("### Current Setup (entered by driver)")
        for k, v in cfg.items():
            lines.append(f"  - {k.replace('_', ' ').title()}: {v}")
        lines.append("")

    # ── Telemetry summary ────────────────────────────────────────────────────
    if laps:
        lines.append("### Telemetry Summary")
        lines.append(f"  - Laps recorded: {len(laps)}")
        timed = [lap for lap in laps if lap.lap_time_ms]
        if timed:
            best = min(timed, key=lambda lap: lap.lap_time_ms)
            ms = best.lap_time_ms
            lines.append(f"  - Best lap time: {ms // 60000}:{(ms % 60000) / 1000:06.3f}")
        lines += [
            f"  - Total oversteer events  : {sum(l.oversteer_events for l in laps)}",
            f"  - Total understeer events : {sum(l.understeer_events for l in laps)}",
            f"  - Total wheel-lock events : {sum(l.wheel_lock_events for l in laps)}",
            f"  - Total wheelspin events  : {sum(l.wheelspin_events for l in laps)}",
            f"  - Total bottom-out events : {sum(l.bottom_out_events for l in laps)}",
        ]
        last = laps[-1]
        if last.tyre_temp_fl:
            lines.append(
                f"  - Tyre temps last lap FL/FR/RL/RR: "
                f"{last.tyre_temp_fl:.1f} / {last.tyre_temp_fr:.1f} / "
                f"{last.tyre_temp_rl:.1f} / {last.tyre_temp_rr:.1f} °C"
            )
        lines.append("")

    # ── Available tuning sections ─────────────────────────────────────────────
    lines.append("### Available Tuning Sections")
    profile: dict = (car.tuning_profile if car else None) or {}

    if not profile:
        lines.append(
            "  ⚠ No tuning profile loaded for this car. "
            "Provide general advice based on telemetry only."
        )
    else:
        _numeric(lines, profile, "tires", "Neumáticos", [])
        _numeric(lines, profile, "suspension", "Suspensión", [
            "ride_height_front", "ride_height_rear",
            "arb_front", "arb_rear",
            "damper_bump_front", "damper_bump_rear",
            "damper_rebound_front", "damper_rebound_rear",
            "natural_frequency_front", "natural_frequency_rear",
            "camber_front", "camber_rear",
            "toe_front", "toe_rear",
        ])
        _numeric(lines, profile, "aerodynamics", "Aerodinámica", [
            "downforce_front", "downforce_rear",
            "power_output",
        ])
        _numeric(lines, profile, "weight_balance", "Ajuste de rendimiento", [
            "ballast", "ballast_position", "power_limiter",
        ])
        _numeric(lines, profile, "differential", "Engranaje diferencial", [
            "initial_torque_front", "initial_torque_rear",
            "accel_sensitivity_front", "accel_sensitivity_rear",
            "decel_sensitivity_front", "decel_sensitivity_rear",
            "torque_distribution",
        ])
        _numeric(lines, profile, "transmission", "Transmisión", [
            "top_speed", "final_drive",
            "gear_1", "gear_2", "gear_3", "gear_4",
            "gear_5", "gear_6", "gear_7",
        ])
        _numeric(lines, profile, "nitro", "Nitro/Rebase", ["output"])
        _numeric(lines, profile, "supercharger", "Sobrealimentador", [])
        _numeric(lines, profile, "intake_exhaust", "Admisión y escape", [])
        _numeric(lines, profile, "brakes", "Frenos", [
            "handbrake_torque", "brake_bias",
        ])
        _numeric(lines, profile, "steering", "Dirección", ["rear_steering_angle"])
        _numeric(lines, profile, "drivetrain", "Tren de transmisión", [])
        _numeric(lines, profile, "engine_mods", "Modificación del motor", [])
        _numeric(lines, profile, "body", "Carrocería", [])
        # legacy
        _numeric(lines, profile, "brake_balance", "Balance de frenos", ["front_bias"])

    lines += ["", "---", "Provide your setup recommendations as JSON:"]
    return "\n".join(lines)


def _numeric(
    lines: list[str],
    profile: dict,
    key: str,
    label: str,
    param_keys: list[str],
) -> None:
    data = profile.get(key)
    if not data:
        return

    ranges: dict = data.get("ranges", {})
    current: dict = data.get("current", {})
    selections: dict = data.get("selections", {})

    # Skip section if nothing to show
    if not ranges and not selections:
        return

    lines.append(f"\n**{label}**")

    # Numeric params with ranges
    shown_keys = param_keys if param_keys else list(ranges.keys())
    for p in shown_keys:
        if p not in ranges:
            continue
        lo, hi = ranges[p]
        curr = current.get(p, "?")
        lines.append(f"  - {p.replace('_', ' ').title()}: current={curr}  range=[{lo}, {hi}]")

    # Categorical / selection params
    for p, val in selections.items():
        lines.append(f"  - {p.replace('_', ' ').title()}: current={val}  (categorical)")
