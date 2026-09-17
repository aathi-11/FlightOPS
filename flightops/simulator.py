from __future__ import annotations

from typing import List, Tuple, Dict
from .agents import BaggageHandlingAgent, GateAssignmentAgent, RefuelingAgent, TurnaroundCoordinator
from .models import Assignment, Crew, Flight, Gate, Truck


def build_coordinator(gates: List[Gate], crews: List[Crew], trucks: List[Truck]) -> TurnaroundCoordinator:
    """Helper to instantiate a TurnaroundCoordinator with its three agents."""
    return TurnaroundCoordinator(
        GateAssignmentAgent(gates),
        BaggageHandlingAgent(crews),
        RefuelingAgent(trucks),
    )


def run_plan(
    flights: List[Flight], gates: List[Gate], crews: List[Crew], trucks: List[Truck]
) -> Tuple[TurnaroundCoordinator, Dict[str, Dict[str, Assignment]]]:
    """Builds coordinator and executes initial plan pass."""
    coordinator = build_coordinator(gates, crews, trucks)
    plans = coordinator.plan(flights)
    return coordinator, plans


def render_assignments(coordinator: TurnaroundCoordinator) -> str:
    """Renders formatted ASCII representation of current gate, baggage, and refuel schedules."""
    if coordinator.status == "INFEASIBLE":
        return "  [STATUS: INFEASIBLE - No valid conflict-free schedule satisfies all constraints!]"

    lines: list[str] = []
    lines.append("--- Gate Schedule ---")
    for gate_id, assignments in coordinator.gate_agent.snapshot().items():
        if not assignments:
            lines.append(f"  {gate_id}: (Empty)")
        for assignment in assignments:
            lines.append(f"  {gate_id}: Flight {assignment.flight_id} [{assignment.start}, {assignment.end}]")

    lines.append("--- Baggage Crew Schedule ---")
    for crew_id, assignments in coordinator.baggage_agent.snapshot().items():
        if not assignments:
            lines.append(f"  {crew_id}: (Empty)")
        for assignment in assignments:
            lines.append(f"  {crew_id}: Flight {assignment.flight_id} [{assignment.start}, {assignment.end}]")

    lines.append("--- Refueling Truck Schedule ---")
    for truck_id, assignments in coordinator.refuel_agent.snapshot().items():
        if not assignments:
            lines.append(f"  {truck_id}: (Empty)")
        for assignment in assignments:
            lines.append(f"  {truck_id}: Flight {assignment.flight_id} [{assignment.start}, {assignment.end}]")

    return "\n".join(lines)


def render_message_logs(coordinator: TurnaroundCoordinator) -> str:
    """Renders CNP negotiation message logs."""
    return coordinator.logger.render()
