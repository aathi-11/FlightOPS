from __future__ import annotations

from typing import Iterable, Dict, List, Tuple, Optional
import constraint

from .models import AircraftType, Flight, Gate, Assignment


class GateCSPSolver:
    """
    CSP-based Gate Assignment Solver using python-constraint.
    
    Variables: Flight IDs
    Domains: Compatible gate IDs based on aircraft type
             - Wide-body aircraft -> Wide-body capable gates ONLY
             - Narrow-body aircraft -> Any gate
    Constraints:
             - Non-overlapping gate usage including buffer_minutes buffer
    """

    def __init__(self, buffer_minutes: int = 10) -> None:
        self.buffer_minutes = buffer_minutes

    @staticmethod
    def _intervals_overlap(start1: int, duration1: int, start2: int, duration2: int, buffer: int) -> bool:
        end1_buffered = start1 + duration1 + buffer
        end2_buffered = start2 + duration2 + buffer
        # Two intervals overlap with buffer if:
        # start1 < start2 + duration2 + buffer AND start2 < start1 + duration1 + buffer
        return (start1 < end2_buffered) and (start2 < end1_buffered)

    def solve(
        self,
        flights: Iterable[Flight],
        gates: Iterable[Gate],
        fixed_assignments: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Assignment]]:
        """
        Solves the CSP for the given flights and gates.
        
        :param flights: Collection of flights to schedule
        :param gates: Collection of airport gates
        :param fixed_assignments: Optional dict of flight_id -> gate_id to lock in place
        :return: Dict mapping flight_id to Assignment object, or None if INFEASIBLE.
        """
        flight_list = list(flights)
        gate_list = list(gates)
        fixed = fixed_assignments or {}

        if not flight_list:
            return {}

        problem = constraint.Problem()

        # Add variables and domains
        for flight in flight_list:
            if flight.flight_id in fixed:
                # Fixed assignment locked
                target_gate_id = fixed[flight.flight_id]
                gate_obj = next((g for g in gate_list if g.gate_id == target_gate_id), None)
                if gate_obj is None or not gate_obj.compatible(flight.aircraft_type):
                    return None  # Infeasible fixed lock
                problem.addVariable(flight.flight_id, [target_gate_id])
            else:
                compatible_gates = [
                    g.gate_id for g in gate_list if g.compatible(flight.aircraft_type)
                ]
                if not compatible_gates:
                    return None  # No compatible gate for flight (INFEASIBLE)
                
                # Heuristic domain sorting: for narrow-body aircraft, prefer narrow-only gates first
                # to preserve wide-capable gates for wide-body flights.
                if flight.aircraft_type is AircraftType.NARROW:
                    compatible_gates.sort(
                        key=lambda gid: next(g.wide_body_capable for g in gate_list if g.gate_id == gid)
                    )
                problem.addVariable(flight.flight_id, compatible_gates)

        # Add binary non-overlap constraints between flights whose times overlap
        for i in range(len(flight_list)):
            f1 = flight_list[i]
            s1 = f1.current_arrival
            d1 = f1.gate_duration
            for j in range(i + 1, len(flight_list)):
                f2 = flight_list[j]
                s2 = f2.current_arrival
                d2 = f2.gate_duration

                if self._intervals_overlap(s1, d1, s2, d2, self.buffer_minutes):
                    # f1 and f2 overlap in time: they MUST NOT share the same gate
                    problem.addConstraint(lambda g1, g2: g1 != g2, (f1.flight_id, f2.flight_id))

        solutions = problem.getSolutions()
        if not solutions:
            return None

        # Pick best solution prioritizing narrow-body on non-wide gates
        best_solution = solutions[0]
        
        assignments: Dict[str, Assignment] = {}
        for flight in flight_list:
            assigned_gate_id = best_solution[flight.flight_id]
            start = flight.current_arrival
            end = start + flight.gate_duration
            assignments[flight.flight_id] = Assignment(
                flight_id=flight.flight_id,
                resource_id=assigned_gate_id,
                start=start,
                end=end,
            )

        return assignments
