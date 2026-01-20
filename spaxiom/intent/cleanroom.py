"""Cleanroom contamination risk pattern and events."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from spaxiom.geo import Zone
from spaxiom.intent.pattern import Pattern, PatternEvent


@dataclass
class PressureBreach(PatternEvent):
    """Emitted when pressure differential drops below spec."""

    zone: str = ""
    boundary: str = ""
    differential_pa: float = 0.0
    min_required_pa: float = 0.0


@dataclass
class ParticleExcursion(PatternEvent):
    """Emitted when particle counts exceed class limit."""

    zone: str = ""
    count_per_m3: float = 0.0
    class_limit: float = 0.0


@dataclass
class AirlockViolation(PatternEvent):
    """Emitted when an airlock sequence violation is detected."""

    zone: str = ""
    airlock_id: str = ""
    duration_s: float = 0.0


@dataclass
class HighRiskMovement(PatternEvent):
    """Emitted when occupancy is high during elevated CRI."""

    zone: str = ""
    occupancy: float = 0.0
    cri: float = 0.0


@dataclass
class ContaminationRiskUpdated(PatternEvent):
    """Emitted with CRI and component breakdown."""

    zone: str = ""
    cri: float = 0.0
    breach_seconds: float = 0.0
    particle_excursion: float = 0.0
    airlock_violations: int = 0


class CleanroomRisk(Pattern):
    """Cleanroom contamination risk pattern with CRI computation."""

    def __init__(
        self,
        name: str,
        zone: Zone,
        particle_sensor,
        dp_sensors: Dict[str, Any],
        airlock_sensors: List[Any],
        temperature_sensor: Any,
        humidity_sensor: Optional[Any] = None,
        occupancy_sensor: Optional[Any] = None,
        max_particles: float = 352000.0,
        min_dp_anteroom_pa: float = 5.0,
        min_dp_corridor_pa: float = 12.5,
        alpha: float = 1e-3,
        beta: float = 1e-6,
        gamma: float = 1.0,
        window_s: float = 3600.0,
        risk_threshold: float = 0.7,
    ) -> None:
        super().__init__(name=name)
        self.zone = zone
        self.particle_sensor = particle_sensor
        self.dp_sensors = dp_sensors
        self.airlock_sensors = airlock_sensors
        self.temperature_sensor = temperature_sensor
        self.humidity_sensor = humidity_sensor
        self.occupancy_sensor = occupancy_sensor

        self.max_particles = max_particles
        self.min_dp_anteroom_pa = min_dp_anteroom_pa
        self.min_dp_corridor_pa = min_dp_corridor_pa
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.window_s = window_s
        self.risk_threshold = risk_threshold

        self._pressure_history = {"anteroom": deque(), "corridor": deque()}
        self._particle_history = deque()
        self._airlock_history: Dict[str, deque] = {}
        self._last_cri: Optional[float] = None
        self._last_violation_state: Dict[str, bool] = {}

        for idx, _sensor in enumerate(self.airlock_sensors):
            self._airlock_history[f"airlock_{idx + 1}"] = deque()

    def _trim(self, q: deque, now: float) -> None:
        cutoff = now - self.window_s
        while q and q[0][0] < cutoff:
            q.popleft()

    def _record(self, q: deque, now: float, value: float) -> None:
        q.append((now, float(value)))
        self._trim(q, now)

    def _breach_seconds(self, boundary: str, min_dp: float) -> float:
        history = self._pressure_history.get(boundary, deque())
        if len(history) < 2:
            return 0.0
        total = 0.0
        for (t0, v0), (t1, v1) in zip(list(history)[:-1], list(history)[1:]):
            if v0 < min_dp:
                total += max(0.0, t1 - t0)
        return total

    def _particle_excursion(self) -> float:
        history = self._particle_history
        if len(history) < 2:
            return 0.0
        total = 0.0
        for (t0, v0), (t1, v1) in zip(list(history)[:-1], list(history)[1:]):
            excess = max(0.0, v0 - self.max_particles)
            total += excess * max(0.0, t1 - t0)
        return total

    def _airlock_violations(self) -> int:
        total = 0
        for key, history in self._airlock_history.items():
            if not history:
                continue
            # Count rising edges of violation state
            prev = False
            for _, value in history:
                curr = bool(value)
                if curr and not prev:
                    total += 1
                prev = curr
        return total

    def _cri(self, breach_seconds: float, excursion: float, violations: int) -> float:
        score = (
            (self.alpha * breach_seconds)
            + (self.beta * excursion)
            + (self.gamma * violations)
        )
        return 1.0 - (1.0 / (1.0 + score))

    def update(self, dt: float, context: Dict[str, Any]) -> List[PatternEvent]:
        now = time.time()

        # Read sensors
        particle = float(self.particle_sensor.read() or 0.0)
        dp_anteroom = float(self.dp_sensors["anteroom"].read() or 0.0)
        dp_corridor = float(self.dp_sensors["corridor"].read() or 0.0)

        self._record(self._particle_history, now, particle)
        self._record(self._pressure_history["anteroom"], now, dp_anteroom)
        self._record(self._pressure_history["corridor"], now, dp_corridor)

        for idx, sensor in enumerate(self.airlock_sensors):
            key = f"airlock_{idx + 1}"
            value = float(sensor.read() or 0.0)
            self._record(self._airlock_history[key], now, value)

        breach_seconds = self._breach_seconds(
            "anteroom", self.min_dp_anteroom_pa
        ) + self._breach_seconds("corridor", self.min_dp_corridor_pa)
        excursion = self._particle_excursion()
        violations = self._airlock_violations()
        cri = self._cri(breach_seconds, excursion, violations)

        self._emit_event(
            ContaminationRiskUpdated(
                zone=self.zone.name,
                cri=cri,
                breach_seconds=breach_seconds,
                particle_excursion=excursion,
                airlock_violations=violations,
            )
        )

        if particle > self.max_particles:
            self._emit_event(
                ParticleExcursion(
                    zone=self.zone.name,
                    count_per_m3=particle,
                    class_limit=self.max_particles,
                )
            )

        if dp_anteroom < self.min_dp_anteroom_pa:
            self._emit_event(
                PressureBreach(
                    zone=self.zone.name,
                    boundary="anteroom",
                    differential_pa=dp_anteroom,
                    min_required_pa=self.min_dp_anteroom_pa,
                )
            )

        if dp_corridor < self.min_dp_corridor_pa:
            self._emit_event(
                PressureBreach(
                    zone=self.zone.name,
                    boundary="corridor",
                    differential_pa=dp_corridor,
                    min_required_pa=self.min_dp_corridor_pa,
                )
            )

        for idx, sensor in enumerate(self.airlock_sensors):
            key = f"airlock_{idx + 1}"
            violation = bool(sensor.read() or 0)
            prev = self._last_violation_state.get(key, False)
            if violation and not prev:
                self._emit_event(
                    AirlockViolation(
                        zone=self.zone.name,
                        airlock_id=key,
                        duration_s=2.0,
                    )
                )
            self._last_violation_state[key] = violation

        if self.occupancy_sensor is not None:
            occupancy = float(self.occupancy_sensor.read() or 0.0)
            if cri >= self.risk_threshold and occupancy >= 8:
                self._emit_event(
                    HighRiskMovement(
                        zone=self.zone.name,
                        occupancy=occupancy,
                        cri=cri,
                    )
                )

        self._last_cri = cri
        return self.emit()

    def depends_on(self) -> List[Any]:
        deps = [self.particle_sensor, *self.dp_sensors.values(), *self.airlock_sensors]
        deps.append(self.temperature_sensor)
        if self.humidity_sensor is not None:
            deps.append(self.humidity_sensor)
        if self.occupancy_sensor is not None:
            deps.append(self.occupancy_sensor)
        return deps
