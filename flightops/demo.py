from __future__ import annotations

from .scenarios import (
    build_act1_standard_scenario,
    build_act2_single_delay_scenario,
    build_act3a_overlapping_wide_delays,
    build_act3b_infeasible_gate_contention,
)
from .simulator import render_assignments, run_plan


def _print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(f" {title.upper()} ")
    print("=" * 70)


def run_act1() -> None:
    _print_header("Act 1: Happy Path (Standard Operating Scenario)")
    flights, gates, crews, trucks = build_act1_standard_scenario()
    coordinator, _ = run_plan(flights, gates, crews, trucks)
    print(render_assignments(coordinator))


def run_act2() -> None:
    _print_header("Act 2: Single Delay & Live Renegotiation")
    flights, gates, crews, trucks, delayed_flight_id, delay_minutes = build_act2_single_delay_scenario()
    coordinator, _ = run_plan(flights, gates, crews, trucks)
    print("--- Initial On-Time Schedule ---")
    print(render_assignments(coordinator))

    print(f"\n>>> Injecting live {delay_minutes}-minute delay to wide-body flight {delayed_flight_id}...")
    coordinator.repair_delay(delayed_flight_id, delay_minutes)

    print("\n--- Schedule After Live CNP & CSP Repair ---")
    print(render_assignments(coordinator))


def run_act3a() -> None:
    _print_header("Act 3a: Live Stress Test - Overlapping Wide-Body Delays (Feasible)")
    flights, gates, crews, trucks, delays_to_inject = build_act3a_overlapping_wide_delays()
    coordinator, _ = run_plan(flights, gates, crews, trucks)
    print("--- Initial On-Time Schedule ---")
    print(render_assignments(coordinator))

    for flight_id, delay_mins in delays_to_inject:
        print(f"\n>>> Injecting live delay of {delay_mins}m to flight {flight_id}...")
        coordinator.repair_delay(flight_id, delay_mins)

    print("\n--- Schedule After Live Renegotiation of Overlapping Wide Delays ---")
    print(render_assignments(coordinator))


def run_act3b() -> None:
    _print_header("Act 3b: Live Stress Test - Wide-Body Gate Contention (Infeasible)")
    flights, gates, crews, trucks, delays_to_inject = build_act3b_infeasible_gate_contention()
    coordinator, _ = run_plan(flights, gates, crews, trucks)
    print("--- Initial On-Time Schedule (3 Wide Flights, 2 Wide Gates) ---")
    print(render_assignments(coordinator))

    for flight_id, delay_mins in delays_to_inject:
        print(f"\n>>> Injecting live delay shift of {delay_mins}m to flight {flight_id}...")
        coordinator.repair_delay(flight_id, delay_mins)
        if coordinator.status == "INFEASIBLE":
            print(f"  [DISRUPT EVENT] Gate capacity exhausted! System caught live constraint failure.")
            break

    print("\n--- Final Status After Disruption ---")
    print(render_assignments(coordinator))


def main() -> None:
    print("\n==========================================================================")
    print("   GROUNDCONTROL: MULTI-AGENT AIRPORT GROUND OPERATIONS COORDINATION   ")
    print("==========================================================================")
    run_act1()
    run_act2()
    run_act3a()
    run_act3b()
    print("\n[Demo execution complete.]\n")


if __name__ == "__main__":
    main()
