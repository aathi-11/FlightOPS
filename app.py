from __future__ import annotations

from typing import Dict, Any, List
from flask import Flask, jsonify, render_template, request

from flightops.models import AircraftType, Flight, Gate, Crew, Truck
from flightops.scenarios import (
    build_act1_standard_scenario,
    build_act2_single_delay_scenario,
    build_act3a_overlapping_wide_delays,
    build_act3b_infeasible_gate_contention,
)
from flightops.simulator import build_coordinator

app = Flask(__name__, template_folder="templates")

active_state: Dict[str, Any] = {
    "scenario_name": "act1",
    "flights": [],
    "gates": [],
    "crews": [],
    "trucks": [],
    "coordinator": None,
}


def load_scenario(name: str) -> None:
    if name == "act1":
        flights, gates, crews, trucks = build_act1_standard_scenario()
        coord = build_coordinator(gates, crews, trucks)
        coord.plan(flights)

    elif name == "act2":
        flights, gates, crews, trucks, delayed_id, delay_mins = build_act2_single_delay_scenario()
        coord = build_coordinator(gates, crews, trucks)
        coord.plan(flights)
        coord.repair_delay(delayed_id, delay_mins)

    elif name == "act3a":
        flights, gates, crews, trucks, delays = build_act3a_overlapping_wide_delays()
        coord = build_coordinator(gates, crews, trucks)
        coord.plan(flights)
        for flight_id, delay_mins in delays:
            coord.repair_delay(flight_id, delay_mins)

    elif name == "act3b":
        flights, gates, crews, trucks, delays = build_act3b_infeasible_gate_contention()
        coord = build_coordinator(gates, crews, trucks)
        coord.plan(flights)
        for flight_id, delay_mins in delays:
            coord.repair_delay(flight_id, delay_mins)

    else:
        flights, gates, crews, trucks = build_act1_standard_scenario()
        coord = build_coordinator(gates, crews, trucks)
        coord.plan(flights)

    active_state["scenario_name"] = name
    active_state["flights"] = flights
    active_state["gates"] = gates
    active_state["crews"] = crews
    active_state["trucks"] = trucks
    active_state["coordinator"] = coord


def serialize_state() -> Dict[str, Any]:
    coord = active_state["coordinator"]
    if coord is None:
        return {}

    flights_data = [
        {
            "flight_id": f.flight_id,
            "aircraft_type": f.aircraft_type.value,
            "scheduled_arrival": f.scheduled_arrival,
            "current_arrival": f.current_arrival,
            "turnaround_window": f.turnaround_window,
            "gate_duration": f.gate_duration,
            "baggage_duration": f.baggage_duration,
            "refuel_duration": f.refuel_duration,
            "delay_minutes": f.delay_minutes,
        }
        for f in active_state["flights"]
    ]

    gates_data = [
        {"gate_id": g.gate_id, "wide_body_capable": g.wide_body_capable}
        for g in active_state["gates"]
    ]
    crews_data = [{"crew_id": c.crew_id} for c in active_state["crews"]]
    trucks_data = [{"truck_id": t.truck_id} for t in active_state["trucks"]]

    gate_schedule = {
        g_id: [
            {"flight_id": a.flight_id, "start": a.start, "end": a.end} for a in assignments
        ]
        for g_id, assignments in coord.gate_agent.snapshot().items()
    }

    baggage_schedule = {
        c_id: [
            {"flight_id": a.flight_id, "start": a.start, "end": a.end} for a in assignments
        ]
        for c_id, assignments in coord.baggage_agent.snapshot().items()
    }

    refuel_schedule = {
        t_id: [
            {"flight_id": a.flight_id, "start": a.start, "end": a.end} for a in assignments
        ]
        for t_id, assignments in coord.refuel_agent.snapshot().items()
    }

    messages_data = [
        {
            "sender": m.sender,
            "receiver": m.receiver,
            "msg_type": m.msg_type.value,
            "flight_id": m.flight_id,
            "resource_id": m.resource_id,
            "start": m.start,
            "end": m.end,
            "details": m.details,
            "str": str(m),
        }
        for m in coord.logger.logs
    ]

    return {
        "scenario_name": active_state["scenario_name"],
        "status": coord.status,
        "flights": flights_data,
        "gates": gates_data,
        "crews": crews_data,
        "trucks": trucks_data,
        "schedules": {
            "gate": gate_schedule,
            "baggage": baggage_schedule,
            "refuel": refuel_schedule,
        },
        "messages": messages_data,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scenario/<name>", methods=["GET"])
def get_scenario(name: str):
    load_scenario(name)
    return jsonify(serialize_state())


@app.route("/api/delay", methods=["POST"])
def inject_delay():
    data = request.json or {}
    flight_id = data.get("flight_id")
    delay_minutes = int(data.get("delay_minutes", 0))

    coord = active_state["coordinator"]
    if coord and flight_id:
        coord.repair_delay(flight_id, delay_minutes)

    return jsonify(serialize_state())


if __name__ == "__main__":
    load_scenario("act1")
    print("Starting GroundControl Web UI at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
