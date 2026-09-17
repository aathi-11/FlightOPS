from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AircraftType(str, Enum):
    NARROW = "narrow"
    WIDE = "wide"


@dataclass(frozen=True, slots=True)
class Flight:
    flight_id: str
    aircraft_type: AircraftType
    scheduled_arrival: int
    turnaround_window: int
    gate_duration: int
    baggage_duration: int
    refuel_duration: int
    delay_minutes: int = 0

    @property
    def current_arrival(self) -> int:
        return self.scheduled_arrival + self.delay_minutes

    @property
    def gate_window_end(self) -> int:
        return self.current_arrival + self.turnaround_window


@dataclass(frozen=True, slots=True)
class Gate:
    gate_id: str
    wide_body_capable: bool

    def compatible(self, aircraft_type: AircraftType) -> bool:
        return aircraft_type is AircraftType.NARROW or self.wide_body_capable


@dataclass(frozen=True, slots=True)
class Crew:
    crew_id: str


@dataclass(frozen=True, slots=True)
class Truck:
    truck_id: str


@dataclass(slots=True)
class Assignment:
    flight_id: str
    resource_id: str
    start: int
    end: int
