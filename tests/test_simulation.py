from __future__ import annotations

import unittest

from flightops.models import AircraftType
from flightops.scenarios import (
    build_act1_standard_scenario,
    build_act2_single_delay_scenario,
    build_act3a_overlapping_wide_delays,
    build_act3b_infeasible_gate_contention,
)
from flightops.simulator import run_plan
from flightops.protocol import MessageType


class FlightOpsTests(unittest.TestCase):

    def test_happy_path_assigns_all_flights(self) -> None:
        flights, gates, crews, trucks = build_act1_standard_scenario()
        coordinator, plans = run_plan(flights, gates, crews, trucks)

        self.assertEqual(coordinator.status, "SUCCESS")
        self.assertEqual(set(plans.keys()), {f.flight_id for f in flights})

        # Check aircraft-gate compatibility: Wide-body flights only on wide-capable gates
        wide_flight_ids = {f.flight_id for f in flights if f.aircraft_type is AircraftType.WIDE}
        wide_gate_ids = {g.gate_id for g in gates if g.wide_body_capable}

        for flight_id, plan in plans.items():
            assigned_gate_id = plan["gate"].resource_id
            if flight_id in wide_flight_ids:
                self.assertIn(assigned_gate_id, wide_gate_ids)

    def test_gate_buffer_constraint(self) -> None:
        flights, gates, crews, trucks = build_act1_standard_scenario()
        coordinator, _ = run_plan(flights, gates, crews, trucks)

        gate_snapshots = coordinator.gate_agent.snapshot()
        for gate_id, assignments in gate_snapshots.items():
            assignments_sorted = sorted(assignments, key=lambda a: a.start)
            for i in range(len(assignments_sorted) - 1):
                prev_end = assignments_sorted[i].end
                next_start = assignments_sorted[i + 1].start
                self.assertGreaterEqual(next_start - prev_end, coordinator.gate_agent.buffer_minutes)

    def test_single_delay_live_renegotiation(self) -> None:
        flights, gates, crews, trucks, delayed_flight_id, delay_minutes = build_act2_single_delay_scenario()
        coordinator, _ = run_plan(flights, gates, crews, trucks)

        before_gate_plan = coordinator.current_plan()[delayed_flight_id]["gate"]
        self.assertEqual(before_gate_plan.start, 5)

        # Trigger live delay repair
        repaired_plans = coordinator.repair_delay(delayed_flight_id, delay_minutes)
        self.assertEqual(coordinator.status, "SUCCESS")

        after_gate_plan = repaired_plans[delayed_flight_id]["gate"]
        self.assertEqual(after_gate_plan.start, 5 + delay_minutes)  # 25

        # Verify downstream services (baggage & refuel) were also updated
        baggage_plan = repaired_plans[delayed_flight_id]["baggage"]
        refuel_plan = repaired_plans[delayed_flight_id]["refuel"]
        self.assertGreaterEqual(baggage_plan.start, after_gate_plan.start)
        self.assertLessEqual(baggage_plan.end, after_gate_plan.end)
        self.assertGreaterEqual(refuel_plan.start, after_gate_plan.start)
        self.assertLessEqual(refuel_plan.end, after_gate_plan.end)

    def test_stress_overlapping_wide_delays_feasible(self) -> None:
        flights, gates, crews, trucks, delays = build_act3a_overlapping_wide_delays()
        coordinator, initial_plans = run_plan(flights, gates, crews, trucks)
        self.assertEqual(coordinator.status, "SUCCESS")

        # Inject live sequential delays
        for flight_id, delay_mins in delays:
            coordinator.repair_delay(flight_id, delay_mins)
            self.assertEqual(coordinator.status, "SUCCESS")

        final_plans = coordinator.current_plan()
        self.assertEqual(len(final_plans), len(flights))

    def test_stress_wide_gate_contention_infeasible(self) -> None:
        flights, gates, crews, trucks, delays = build_act3b_infeasible_gate_contention()
        coordinator, initial_plans = run_plan(flights, gates, crews, trucks)
        self.assertEqual(coordinator.status, "SUCCESS")

        # Inject live delays until capacity exhausted
        for flight_id, delay_mins in delays:
            coordinator.repair_delay(flight_id, delay_mins)

        self.assertEqual(coordinator.status, "INFEASIBLE")
        self.assertEqual(coordinator.current_plan(), {})

    def test_cnp_message_logging(self) -> None:
        flights, gates, crews, trucks = build_act1_standard_scenario()
        coordinator, _ = run_plan(flights, gates, crews, trucks)

        log_types = {msg.msg_type for msg in coordinator.logger.logs}
        self.assertIn(MessageType.CFP, log_types)
        self.assertIn(MessageType.PROPOSE, log_types)
        self.assertIn(MessageType.ACCEPT, log_types)


if __name__ == "__main__":
    unittest.main()
