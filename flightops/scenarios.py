from __future__ import annotations

from typing import List, Tuple
from .models import AircraftType, Crew, Flight, Gate, Truck


def build_act1_standard_scenario() -> Tuple[List[Flight], List[Gate], List[Crew], List[Truck]]:
    """
    Act 1: Happy Path Scenario.
    4 flights (1 wide-body, 3 narrow-body) with adequate gates, crews, and trucks.
    """
    flights = [
        Flight("FL100", AircraftType.NARROW, scheduled_arrival=0, turnaround_window=45, gate_duration=20, baggage_duration=10, refuel_duration=12),
        Flight("FL200", AircraftType.WIDE, scheduled_arrival=5, turnaround_window=55, gate_duration=25, baggage_duration=15, refuel_duration=18),
        Flight("FL300", AircraftType.NARROW, scheduled_arrival=18, turnaround_window=45, gate_duration=20, baggage_duration=10, refuel_duration=12),
        Flight("FL400", AircraftType.NARROW, scheduled_arrival=30, turnaround_window=45, gate_duration=18, baggage_duration=10, refuel_duration=10),
    ]
    gates = [
        Gate("G1", wide_body_capable=False),
        Gate("G2", wide_body_capable=False),
        Gate("G3", wide_body_capable=True),
    ]
    crews = [Crew("B1"), Crew("B2")]
    trucks = [Truck("T1"), Truck("T2")]
    return flights, gates, crews, trucks


def build_act2_single_delay_scenario() -> Tuple[List[Flight], List[Gate], List[Crew], List[Truck], str, int]:
    """
    Act 2: Single Delay Scenario.
    FL200 (wide-body) delayed by 20 minutes.
    """
    flights, gates, crews, trucks = build_act1_standard_scenario()
    delayed_flight_id = "FL200"
    delay_minutes = 20
    return flights, gates, crews, trucks, delayed_flight_id, delay_minutes


def build_act3a_overlapping_wide_delays() -> Tuple[List[Flight], List[Gate], List[Crew], List[Truck]]:
    """
    Act 3a: Overlapping Wide-Body Delays (Feasible).
    2 wide-body flights delayed into overlapping windows, 2 wide-capable gates present.
    """
    flights = [
        Flight("WX901", AircraftType.WIDE, scheduled_arrival=20, turnaround_window=45, gate_duration=30, baggage_duration=15, refuel_duration=15, delay_minutes=5),
        Flight("WX902", AircraftType.WIDE, scheduled_arrival=25, turnaround_window=45, gate_duration=30, baggage_duration=15, refuel_duration=15, delay_minutes=5),
        Flight("NX101", AircraftType.NARROW, scheduled_arrival=10, turnaround_window=40, gate_duration=20, baggage_duration=10, refuel_duration=10),
        Flight("NX102", AircraftType.NARROW, scheduled_arrival=35, turnaround_window=40, gate_duration=20, baggage_duration=10, refuel_duration=10),
    ]
    gates = [
        Gate("G-A", wide_body_capable=False),
        Gate("G-B", wide_body_capable=False),
        Gate("G-W1", wide_body_capable=True),
        Gate("G-W2", wide_body_capable=True),
    ]
    crews = [Crew("BC-1"), Crew("BC-2"), Crew("BC-3")]
    trucks = [Truck("TR-1"), Truck("TR-2")]
    return flights, gates, crews, trucks


def build_act3b_infeasible_gate_contention() -> Tuple[List[Flight], List[Gate], List[Crew], List[Truck]]:
    """
    Act 3b: Overlapping Wide-Body Delays Exceeding Capacity (Infeasible).
    3 wide-body flights competing for overlapping windows with only 2 wide-capable gates.
    """
    flights = [
        Flight("WX901", AircraftType.WIDE, scheduled_arrival=20, turnaround_window=45, gate_duration=30, baggage_duration=15, refuel_duration=15),
        Flight("WX902", AircraftType.WIDE, scheduled_arrival=22, turnaround_window=45, gate_duration=30, baggage_duration=15, refuel_duration=15),
        Flight("WX903", AircraftType.WIDE, scheduled_arrival=25, turnaround_window=45, gate_duration=30, baggage_duration=15, refuel_duration=15),
    ]
    gates = [
        Gate("G-A", wide_body_capable=False),
        Gate("G-B", wide_body_capable=False),
        Gate("G-W1", wide_body_capable=True),
        Gate("G-W2", wide_body_capable=True),
    ]
    crews = [Crew("BC-1"), Crew("BC-2"), Crew("BC-3")]
    trucks = [Truck("TR-1"), Truck("TR-2"), Truck("TR-3")]
    return flights, gates, crews, trucks


# Aliases for backward compatibility
build_standard_scenario = build_act1_standard_scenario
build_stress_scenario = build_act2_single_delay_scenario
