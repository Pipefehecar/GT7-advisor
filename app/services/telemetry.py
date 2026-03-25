"""
GT7 Telemetry Service
---------------------
Runs a background thread that listens to the GT7 UDP stream.
Falls back to a mock mode when `granturismo` is not installed
or the console is unreachable (useful for development).

Detected behaviour events per packet:
  - Oversteer   : high yaw rate while throttle is applied
  - Understeer  : low yaw rate while steering angle is high
  - Wheel lock  : brake > 80 % while speed > 50 km/h
  - Wheelspin   : throttle > 80 % while speed < 80 km/h
  - Bottom-out  : body height below 4 cm
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LapSummary:
    lap_number: int
    lap_time_ms: int | None = None
    avg_speed_kmh: float = 0.0
    max_speed_kmh: float = 0.0
    avg_throttle: float = 0.0
    avg_brake: float = 0.0
    oversteer_events: int = 0
    understeer_events: int = 0
    wheel_lock_events: int = 0
    wheelspin_events: int = 0
    bottom_out_events: int = 0
    tyre_temp_fl: float = 0.0
    tyre_temp_fr: float = 0.0
    tyre_temp_rl: float = 0.0
    tyre_temp_rr: float = 0.0


@dataclass
class _Accumulator:
    speeds: list[float] = field(default_factory=list)
    throttles: list[float] = field(default_factory=list)
    brakes: list[float] = field(default_factory=list)
    t_fl: list[float] = field(default_factory=list)
    t_fr: list[float] = field(default_factory=list)
    t_rl: list[float] = field(default_factory=list)
    t_rr: list[float] = field(default_factory=list)
    oversteer: int = 0
    understeer: int = 0
    wheel_lock: int = 0
    wheelspin: int = 0
    bottom_out: int = 0


def _avg(lst: list[float]) -> float:
    return sum(lst) / len(lst) if lst else 0.0


class TelemetryService:
    def __init__(self, ps_ip: str):
        self.ps_ip = ps_ip
        self._lock = threading.Lock()
        self._latest: object | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._current_lap = -1
        self._acc = _Accumulator()
        self.on_lap_complete: Callable | None = None  # set by app startup

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True

        # Listener debe crearse en el hilo principal (registra signal handlers)
        try:
            from granturismo.intake import Listener  # type: ignore
            listener = Listener(self.ps_ip)
            target = lambda: self._run_with_listener(listener)
            logger.info("Telemetry listener iniciando modo real (ps_ip=%s)", self.ps_ip)
        except ImportError:
            logger.warning("granturismo not installed — running in mock mode")
            target = self._mock_run

        self._thread = threading.Thread(target=target, daemon=True, name="gt7-telemetry")
        self._thread.start()

    def stop(self):
        self._running = False
        logger.info("Telemetry listener stopped")

    @property
    def latest_packet(self):
        with self._lock:
            return self._latest

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_with_listener(self, listener):
        try:
            with listener:
                while self._running:
                    packet = listener.get()
                    with self._lock:
                        self._latest = packet
                    self._process(packet)
        except Exception as exc:
            logger.error("Telemetry thread error: %s", exc)
            self._running = False

    def _mock_run(self):
        import random
        import time

        lap = 0
        tick = 0
        while self._running:
            time.sleep(0.016)
            tick += 1
            if tick % 3000 == 0:   # ~48 s per mock lap
                lap += 1
            mock = {
                "current_lap": lap,
                "car_speed": random.uniform(30, 280) / 3.6,  # m/s, igual que el protocolo real
                "throttle": random.randint(0, 255),
                "brake": random.randint(0, 255),
                "engine_rpm": random.randint(1500, 9000),
                "tyre_temp": [
                    random.uniform(70, 110),
                    random.uniform(70, 110),
                    random.uniform(65, 105),
                    random.uniform(65, 105),
                ],
                "body_height": random.uniform(0.03, 0.13),
                "angular_velocity": [0.0, random.uniform(-0.6, 0.6), 0.0],
            }
            with self._lock:
                self._latest = mock
            self._process_dict(mock)

    def _process(self, packet):
        """Handle a real granturismo.intake.Listener packet object."""
        try:
            lap_num = packet.lap_count
            speed_ms = packet.car_speed or 0
            throttle = packet.throttle or 0                          # 0-255
            brake = packet.brake or 0                                # 0-255
            body_h = packet.body_height or 0.1
            ang_vel = [0.0, packet.angular_velocity.y, 0.0]
            tyres = [
                packet.wheels.front_left.temperature,
                packet.wheels.front_right.temperature,
                packet.wheels.rear_left.temperature,
                packet.wheels.rear_right.temperature,
            ]
            self._accumulate(lap_num, speed_ms * 3.6, throttle / 255, brake / 255, body_h, ang_vel, tyres)
        except Exception as exc:
            logger.debug("process error: %s", exc)

    def _process_dict(self, d: dict):
        """Handle a mock dict packet."""
        try:
            lap_num = d.get("current_lap")
            speed_kmh = (d.get("car_speed") or 0) * 3.6
            throttle = (d.get("throttle") or 0) / 255
            brake = (d.get("brake") or 0) / 255
            body_h = d.get("body_height") or 0.1
            ang_vel = list(d.get("angular_velocity") or [0, 0, 0])
            tyres = list(d.get("tyre_temp") or [0, 0, 0, 0])
            self._accumulate(lap_num, speed_kmh, throttle, brake, body_h, ang_vel, tyres)
        except Exception as exc:
            logger.debug("process_dict error: %s", exc)

    def _accumulate(self, lap_num, speed_kmh, throttle, brake, body_h, ang_vel, tyres):
        if lap_num is not None and lap_num != self._current_lap and self._current_lap >= 0:
            summary = self._finalise(self._current_lap)
            self._acc = _Accumulator()
            if self.on_lap_complete:
                self.on_lap_complete(summary)

        if lap_num is not None:
            self._current_lap = lap_num

        a = self._acc
        a.speeds.append(speed_kmh)
        a.throttles.append(throttle)
        a.brakes.append(brake)
        if len(tyres) >= 4:
            a.t_fl.append(tyres[0])
            a.t_fr.append(tyres[1])
            a.t_rl.append(tyres[2])
            a.t_rr.append(tyres[3])

        yaw = abs(ang_vel[1]) if len(ang_vel) > 1 else 0
        if yaw > 0.4 and throttle > 0.5:
            a.oversteer += 1
        if yaw < 0.05 and throttle > 0.5:
            a.understeer += 1
        if brake > 0.8 and speed_kmh > 50:
            a.wheel_lock += 1
        if throttle > 0.8 and speed_kmh < 80:
            a.wheelspin += 1
        if body_h < 0.04:
            a.bottom_out += 1

    def _finalise(self, lap_number: int) -> LapSummary:
        a = self._acc
        return LapSummary(
            lap_number=lap_number,
            avg_speed_kmh=_avg(a.speeds),
            max_speed_kmh=max(a.speeds, default=0),
            avg_throttle=_avg(a.throttles),
            avg_brake=_avg(a.brakes),
            oversteer_events=a.oversteer,
            understeer_events=a.understeer,
            wheel_lock_events=a.wheel_lock,
            wheelspin_events=a.wheelspin,
            bottom_out_events=a.bottom_out,
            tyre_temp_fl=_avg(a.t_fl),
            tyre_temp_fr=_avg(a.t_fr),
            tyre_temp_rl=_avg(a.t_rl),
            tyre_temp_rr=_avg(a.t_rr),
        )
