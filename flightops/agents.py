from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

from .models import AircraftType, Assignment, Crew, Flight, Gate, Truck
from .csp_solver import GateCSPSolver
from .protocol import Message, MessageType, MessageLogger, Proposal, Commit


def _intervals_overlap(start1: int, end1: int, start2: int, end2: int) -> bool:
    """Checks if two [start, end] intervals overlap in time."""
    return max(start1, start2) < min(end1, end2)


class GateAssignmentAgent:
    """
    Gate Assignment Agent.
    
    PEAS Description:
    - Performance: Maximize gate utilization, avoid gate overlap/buffer violations,
                   minimize delay propagation, enforce aircraft-gate compatibility.
    - Environment: Airport gate inventory (narrow vs. wide-capable), flight schedules,
                   aircraft types, delay events.
    - Actuators: Assign/reassign gate, issue Call-For-Proposals (CFP), broadcast window updates.
    - Sensors: Flight arrival/delay signals, aircraft type specifications, gate occupancy state.
    """
    name = "gate-agent"

    def __init__(self, gates: List[Gate], buffer_minutes: int = 10) -> None:
        self.gates = list(gates)
        self.buffer_minutes = buffer_minutes
        self.solver = GateCSPSolver(buffer_minutes=buffer_minutes)
        self.current_assignments: Dict[str, Assignment] = {}

    def solve_assignments(
        self, flights: List[Flight], fixed_assignments: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Assignment]]:
        """Uses CSP solver to find conflict-free gate assignments."""
        assignments = self.solver.solve(flights, self.gates, fixed_assignments=fixed_assignments)
        if assignments is not None:
            self.current_assignments = assignments
        return assignments

    def snapshot(self) -> Dict[str, List[Assignment]]:
        """Returns dict mapping gate_id to sorted list of assignments."""
        result: Dict[str, List[Assignment]] = {gate.gate_id: [] for gate in self.gates}
        for assignment in self.current_assignments.values():
            if assignment.resource_id in result:
                result[assignment.resource_id].append(assignment)
        for assignments in result.values():
            assignments.sort(key=lambda a: (a.start, a.end, a.flight_id))
        return result


class _TimeWindowResourceAgent:
    """Base autonomous agent for time-window bound resources (Baggage crews, Refueling trucks)."""
    name = "resource-agent"
    duration_attr = ""
    resource_type_name = "resource"

    def __init__(self, resource_ids: List[str]) -> None:
        self.resource_ids = list(resource_ids)
        self.assignments: Dict[str, List[Assignment]] = {rid: [] for rid in self.resource_ids}

    def _find_free_slot(
        self, window_start: int, window_end: int, duration: int, current_flight_id: str
    ) -> Optional[Tuple[str, int, int]]:
        """
        Locates the earliest available resource unit and slot within [window_start, window_end].
        """
        for rid in self.resource_ids:
            # Filter out existing booking for current_flight_id (if re-evaluating)
            existing = [a for a in self.assignments[rid] if a.flight_id != current_flight_id]
            existing.sort(key=lambda a: a.start)

            cursor = window_start
            found = False
            for booking in existing:
                if cursor + duration <= booking.start:
                    found = True
                    break
                cursor = max(cursor, booking.end)

            if not found and cursor + duration <= window_end:
                found = True

            if found and (cursor + duration <= window_end):
                return rid, cursor, cursor + duration
        return None

    def evaluate_cfp(self, flight: Flight, window_start: int, window_end: int) -> Message:
        """Evaluates a Call-For-Proposal (CFP) for a flight turnaround window."""
        duration = getattr(flight, self.duration_attr)
        slot = self._find_free_slot(window_start, window_end, duration, flight.flight_id)
        if slot is None:
            return Message(
                sender=self.name,
                receiver="coordinator",
                msg_type=MessageType.REFUSE,
                flight_id=flight.flight_id,
                details=f"No {self.resource_type_name} available in [{window_start}, {window_end}]",
            )
        rid, start, end = slot
        return Message(
            sender=self.name,
            receiver="coordinator",
            msg_type=MessageType.PROPOSE,
            flight_id=flight.flight_id,
            resource_id=rid,
            start=start,
            end=end,
            details=f"Slot allocated on {rid}",
        )

    def commit(self, flight_id: str, resource_id: str, start: int, end: int) -> None:
        """Commits a resource assignment."""
        self.release(flight_id)
        self.assignments[resource_id].append(Assignment(flight_id, resource_id, start, end))
        self.assignments[resource_id].sort(key=lambda a: a.start)

    def release(self, flight_id: str) -> None:
        """Releases any active booking for flight_id."""
        for rid in self.resource_ids:
            self.assignments[rid] = [a for a in self.assignments[rid] if a.flight_id != flight_id]

    def snapshot(self) -> Dict[str, List[Assignment]]:
        """Returns dict of resource_id -> list of assignments."""
        return {rid: list(self.assignments[rid]) for rid in self.resource_ids}


class BaggageHandlingAgent(_TimeWindowResourceAgent):
    """
    Baggage-Handling Agent.
    
    PEAS Description:
    - Performance: Allocate baggage crews without overlap, ensure baggage turnaround
                   completes within gate availability window, minimize crew idle time.
    - Environment: Crew roster, gate availability windows broadcast by GateAgent, flight schedules.
    - Actuators: Dispatch crew, issue PROPOSE / REFUSE messages.
    - Sensors: Gate window updates (CFP/DISRUPT), crew assignment state.
    """
    name = "baggage-agent"
    duration_attr = "baggage_duration"
    resource_type_name = "baggage crew"

    def __init__(self, crews: List[Crew]) -> None:
        super().__init__([crew.crew_id for crew in crews])


class RefuelingAgent(_TimeWindowResourceAgent):
    """
    Refueling Agent.
    
    PEAS Description:
    - Performance: Allocate fuel trucks without overlap, complete refueling inside flight
                   gate window, minimize truck transit/idle delays.
    - Environment: Refueling truck fleet, gate windows from GateAgent, flight refuel requirements.
    - Actuators: Dispatch truck, issue PROPOSE / REFUSE messages.
    - Sensors: Gate window updates (CFP/DISRUPT), truck assignment state.
    """
    name = "refuel-agent"
    duration_attr = "refuel_duration"
    resource_type_name = "refuel truck"

    def __init__(self, trucks: List[Truck]) -> None:
        super().__init__([truck.truck_id for truck in trucks])


class TurnaroundCoordinator:
    """
    Decentralized Multi-Agent Turnaround Coordinator.
    
    Relays messages between GateAssignmentAgent, BaggageHandlingAgent, and RefuelingAgent
    via Contract Net Protocol (CNP) and coordinates live disruption repairs.
    """

    def __init__(
        self,
        gate_agent: GateAssignmentAgent,
        baggage_agent: BaggageHandlingAgent,
        refuel_agent: RefuelingAgent,
    ) -> None:
        self.gate_agent = gate_agent
        self.baggage_agent = baggage_agent
        self.refuel_agent = refuel_agent
        self.logger = MessageLogger()
        self._flight_map: Dict[str, Flight] = {}
        self.status = "UNINITIALIZED"

    def plan(self, flights: List[Flight]) -> Dict[str, Dict[str, Assignment]]:
        """Initial CNP planning pass for all flights."""
        self.logger.clear()
        self._flight_map = {f.flight_id: f for f in flights}
        ordered_flights = sorted(flights, key=lambda f: (f.current_arrival, f.flight_id))

        # Step 1: Gate Agent solves CSP gate assignments
        gate_assignments = self.gate_agent.solve_assignments(ordered_flights)
        if gate_assignments is None:
            self.status = "INFEASIBLE"
            self.logger.log(
                Message("gate-agent", "coordinator", MessageType.REFUSE, "ALL", details="Gate CSP infeasible")
            )
            return {}

        final_plans: Dict[str, Dict[str, Assignment]] = {}

        # Step 2: For each flight, initiate CNP with Baggage and Refueling agents
        for flight in ordered_flights:
            gate_assign = gate_assignments[flight.flight_id]
            w_start, w_end = gate_assign.start, gate_assign.end

            # CFP to Baggage Agent
            self.logger.log(
                Message("gate-agent", "baggage-agent", MessageType.CFP, flight.flight_id, gate_assign.resource_id, w_start, w_end)
            )
            baggage_resp = self.baggage_agent.evaluate_cfp(flight, w_start, w_end)
            self.logger.log(baggage_resp)

            # CFP to Refuel Agent
            self.logger.log(
                Message("gate-agent", "refuel-agent", MessageType.CFP, flight.flight_id, gate_assign.resource_id, w_start, w_end)
            )
            refuel_resp = self.refuel_agent.evaluate_cfp(flight, w_start, w_end)
            self.logger.log(refuel_resp)

            if baggage_resp.msg_type is MessageType.PROPOSE and refuel_resp.msg_type is MessageType.PROPOSE:
                # Commit proposals
                self.baggage_agent.commit(flight.flight_id, baggage_resp.resource_id, baggage_resp.start, baggage_resp.end)
                self.refuel_agent.commit(flight.flight_id, refuel_resp.resource_id, refuel_resp.start, refuel_resp.end)

                self.logger.log(
                    Message("coordinator", "baggage-agent", MessageType.ACCEPT, flight.flight_id, baggage_resp.resource_id, baggage_resp.start, baggage_resp.end)
                )
                self.logger.log(
                    Message("coordinator", "refuel-agent", MessageType.ACCEPT, flight.flight_id, refuel_resp.resource_id, refuel_resp.start, refuel_resp.end)
                )

                final_plans[flight.flight_id] = {
                    "gate": gate_assign,
                    "baggage": Assignment(flight.flight_id, baggage_resp.resource_id, baggage_resp.start, baggage_resp.end),
                    "refuel": Assignment(flight.flight_id, refuel_resp.resource_id, refuel_resp.start, refuel_resp.end),
                }
            else:
                self.status = "INFEASIBLE"
                return {}

        self.status = "SUCCESS"
        return final_plans

    def repair_delay(self, delayed_flight_id: str, new_delay_minutes: int) -> Dict[str, Dict[str, Assignment]]:
        """
        Handles live arrival delay disruption without restarting from scratch.
        Propagates updated windows to dependent agents and re-negotiates via CNP.
        """
        delayed_flight = self._flight_map[delayed_flight_id]
        updated_flight = Flight(
            flight_id=delayed_flight.flight_id,
            aircraft_type=delayed_flight.aircraft_type,
            scheduled_arrival=delayed_flight.scheduled_arrival,
            turnaround_window=delayed_flight.turnaround_window,
            gate_duration=delayed_flight.gate_duration,
            baggage_duration=delayed_flight.baggage_duration,
            refuel_duration=delayed_flight.refuel_duration,
            delay_minutes=new_delay_minutes,
        )
        self._flight_map[delayed_flight_id] = updated_flight

        self.logger.log(
            Message(
                sender="environment",
                receiver="gate-agent",
                msg_type=MessageType.DISRUPT,
                flight_id=delayed_flight_id,
                details=f"Flight delayed by {new_delay_minutes} mins (New arrival: {updated_flight.current_arrival})",
            )
        )

        all_flights = list(self._flight_map.values())
        new_gate_assignments = self.gate_agent.solve_assignments(all_flights)

        if new_gate_assignments is None:
            self.status = "INFEASIBLE"
            self.logger.log(
                Message("gate-agent", "coordinator", MessageType.REFUSE, delayed_flight_id, details="Gate CSP re-solve failed (INFEASIBLE)")
            )
            return {}

        # Renegotiate downstream services for flights whose gate windows changed
        for flight in all_flights:
            gate_assign = new_gate_assignments[flight.flight_id]
            w_start, w_end = gate_assign.start, gate_assign.end

            # Issue DISRUPT / REPAIR notification
            self.logger.log(
                Message("gate-agent", "baggage-agent", MessageType.REPAIR, flight.flight_id, gate_assign.resource_id, w_start, w_end)
            )
            baggage_resp = self.baggage_agent.evaluate_cfp(flight, w_start, w_end)
            self.logger.log(baggage_resp)

            self.logger.log(
                Message("gate-agent", "refuel-agent", MessageType.REPAIR, flight.flight_id, gate_assign.resource_id, w_start, w_end)
            )
            refuel_resp = self.refuel_agent.evaluate_cfp(flight, w_start, w_end)
            self.logger.log(refuel_resp)

            if baggage_resp.msg_type is MessageType.PROPOSE and refuel_resp.msg_type is MessageType.PROPOSE:
                self.baggage_agent.commit(flight.flight_id, baggage_resp.resource_id, baggage_resp.start, baggage_resp.end)
                self.refuel_agent.commit(flight.flight_id, refuel_resp.resource_id, refuel_resp.start, refuel_resp.end)
            else:
                self.status = "INFEASIBLE"
                return {}

        self.status = "SUCCESS"
        return self.current_plan()

    def current_plan(self) -> Dict[str, Dict[str, Assignment]]:
        """Returns the current committed assignments for all flights."""
        if self.status == "INFEASIBLE":
            return {}
        
        gate_map = self.gate_agent.current_assignments
        baggage_map = {
            a.flight_id: a for assignments in self.baggage_agent.snapshot().values() for a in assignments
        }
        refuel_map = {
            a.flight_id: a for assignments in self.refuel_agent.snapshot().values() for a in assignments
        }

        plans: Dict[str, Dict[str, Assignment]] = {}
        for flight_id in gate_map.keys() & baggage_map.keys() & refuel_map.keys():
            plans[flight_id] = {
                "gate": gate_map[flight_id],
                "baggage": baggage_map[flight_id],
                "refuel": refuel_map[flight_id],
            }
        return plans
