"""
Prompt Builder
--------------
Builds system + user prompts from session data.

The key safety mechanism: only sections present in the car's
tuning_profile JSON are included.  The LLM cannot suggest
changes to parts that don't exist on the car.
"""

from app.db.models import Car, Lap, Session

SYSTEM_PROMPT = """\
You are an expert Gran Turismo 7 race engineer with deep knowledge of car dynamics.

Your task: analyse telemetry data from a driving session and suggest concrete
setup changes to improve lap time and car balance.

STRICT RULES:
1. Only suggest changes to parameters listed under AVAILABLE TUNING SECTIONS.
   If a section is absent, do NOT mention it.
2. Always give a specific numeric value within the stated range.
3. Link every suggestion to a telemetry observation (e.g. "X oversteer events
   indicate the rear is too loose — increase rear spring rate from Y to Z").
4. Keep suggestions concise and ordered by expected impact.
5. If no tuning profile is available, give general advice but explicitly state
   you cannot confirm valid ranges for this specific car.
"""


def build_prompt(
    session: Session,
    car: Car | None,
    laps: list[Lap],
) -> str:
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

        timed = [l for l in laps if l.lap_time_ms]
        if timed:
            best = min(timed, key=lambda l: l.lap_time_ms)
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
        _section(lines, profile, "suspension", "Suspension", [
            "spring_rate_front", "spring_rate_rear",
            "ride_height_front", "ride_height_rear",
            "damper_bump_front", "damper_bump_rear",
            "damper_rebound_front", "damper_rebound_rear",
            "arb_front", "arb_rear",
            "camber_front", "camber_rear",
            "toe_front", "toe_rear",
        ])
        _section(lines, profile, "aerodynamics", "Aerodynamics", [
            "downforce_front", "downforce_rear",
        ])
        _section(lines, profile, "differential", "Differential / LSD", [
            "initial_torque", "accel_sensitivity", "decel_sensitivity",
        ])
        _section(lines, profile, "transmission", "Transmission", [
            "final_drive",
            "gear_1", "gear_2", "gear_3", "gear_4",
            "gear_5", "gear_6", "gear_7",
        ])
        _section(lines, profile, "brake_balance", "Brake Balance", [
            "front_bias",
        ])

    lines += ["", "---", "Please provide your setup recommendations:"]
    return "\n".join(lines)


def _section(
    lines: list[str],
    profile: dict,
    key: str,
    label: str,
    params: list[str],
):
    data = profile.get(key)
    if not data:
        return
    ranges: dict = data.get("ranges", {})
    current: dict = data.get("current", {})
    if not ranges:
        return

    lines.append(f"\n**{label}**")
    for p in params:
        if p not in ranges:
            continue
        lo, hi = ranges[p]
        curr = current.get(p, "?")
        lines.append(f"  - {p.replace('_', ' ').title()}: current={curr}  range=[{lo}, {hi}]")
