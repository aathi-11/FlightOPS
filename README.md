# GroundControl — Multi-Agent Airport Ground Operations Coordination

A decentralized multi-agent system that coordinates aircraft turnaround operations across three autonomous cooperating agents (**Gate Assignment Agent**, **Baggage-Handling Agent**, **Refueling Agent**). The system uses a **Constraint Satisfaction Problem (CSP)** formulation via `python-constraint` for gate assignment and a **Contract Net Protocol (CNP)** for cross-agent negotiation and live disruption repair.

---

## Features & Architecture

```
flightops/
├── csp_solver.py    # CSP gate assignment solver using python-constraint
├── protocol.py      # Contract Net Protocol (CNP) message types & transaction logger
├── agents.py        # Autonomous Gate, Baggage, and Refueling agents with PEAS models
├── models.py        # Core domain models (Flight, Gate, Crew, Truck, Assignment)
├── scenarios.py     # Scenario builders for standard operation & live delay stress tests
├── simulator.py     # TurnaroundCoordinator execution engine and schedule renderers
└── demo.py          # Multi-act terminal demo runner
app.py               # Flask web server for interactive visual web frontend
demo.py              # Root demo script entry point
tests/               # Unit test suite covering CSP, CNP, live repair, and infeasibility
```

---

## PEAS Formulation per Agent

| Agent | Performance Measure | Environment | Actuators | Sensors |
|---|---|---|---|---|
| **GateAssignmentAgent** | Maximize compatible gate utilization, enforce 10m buffers, minimize delay impact | Gate inventory (narrow vs. wide-capable), flight schedule, aircraft types | Assign/reassign gate, issue `CFP`/`DISRUPT` messages | Flight arrival/delay signals, aircraft specs, gate occupancy |
| **BaggageHandlingAgent** | Allocate baggage crews without overlap inside turnaround window, minimize idle time | Crew roster, gate availability windows broadcast by GateAgent | Dispatch crew, issue `PROPOSE`/`REFUSE` messages | Gate window updates (`CFP`/`DISRUPT`), crew assignment state |
| **RefuelingAgent** | Allocate fuel trucks without overlap inside turnaround window, minimize truck transit | Truck fleet, gate availability windows broadcast by GateAgent | Dispatch truck, issue `PROPOSE`/`REFUSE` messages | Gate window updates (`CFP`/`DISRUPT`), truck assignment state |

---

## Environment Classification

- **Partially Observable**: Baggage and Refueling agents only see gate turnaround windows broadcast via `CFP` messages, not the GateAgent's internal CSP schedule.
- **Stochastic & Dynamic**: Flight arrival delays occur dynamically during execution, altering operational windows mid-schedule.
- **Resource-Constrained Cooperative**: All agents collaborate toward conflict-free turnarounds while sharing limited gates, crews, and fuel trucks.

---

## Demonstration Scenarios (Four-Act Structure)

1. **Act 1 (Happy Path)**: 4 flights (1 wide-body, 3 narrow-body) scheduled on-time with zero conflicts across gates, crews, and trucks.
2. **Act 2 (Single Delay)**: Wide-body flight `FL200` incurs a live 20-minute delay. The system triggers live CSP re-solving and CNP renegotiation to update downstream baggage and refueling slots without restarting from scratch.
3. **Act 3a (Overlapping Wide Delays - Feasible)**: 2 wide-body flights incur live sequential delays into overlapping windows. Resolved live across 2 wide-body capable gates (`G-W1`, `G-W2`).
4. **Act 3b (Gate Contention - Infeasible)**: 3 wide-body flights incur live sequential delays into overlapping turnaround windows with only 2 wide-capable gates available. The system detects gate capacity exhaustion live during disruption repair and cleanly reports `INFEASIBLE`.

---

## Installation & Running

### Installation
```bash
pip install -e .
```
Or directly install requirements:
```bash
pip install python-constraint flask
```

### Run Terminal Demo
```bash
python demo.py
# or
python -m flightops.demo
```

### Run Interactive Visual Web Frontend
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser to view the interactive Gantt chart, scenario controls, delay injector, and live CNP message terminal.

### Run Unit Test Suite
```bash
python -m unittest discover -s tests
```
