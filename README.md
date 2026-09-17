# FlightOPS

FlightOPS is a decentralized multi-agent simulation for airport turnaround coordination. It models three autonomous agents:

- Gate Assignment Agent
- Baggage-Handling Agent
- Refueling Agent

The agents negotiate through a lightweight contract-net style protocol. Each agent reasons only over its own resource pool and local constraints, while a coordinator relays proposals, commitments, and repair requests.

## Problem framing

### PEAS

Gate Assignment Agent
- Performance: maximize compatible gate utilization, avoid buffer violations, minimize displaced flights.
- Environment: gate inventory, aircraft-type constraints, arrival delays, competing gate requests.
- Actuators: reserve, release, and reassign gates.
- Sensors: flight arrivals, gate occupancy, aircraft type, delay updates.

Baggage-Handling Agent
- Performance: allocate crews without overlap, keep baggage work inside turnaround windows, minimize rework.
- Environment: baggage crews, flight turnaround windows, delay events.
- Actuators: reserve, release, and repair crew assignments.
- Sensors: flight service window, crew availability, disruption notices.

Refueling Agent
- Performance: allocate trucks without overlap, keep refueling inside turnaround windows, minimize rework.
- Environment: refuel trucks, flight turnaround windows, delay events.
- Actuators: reserve, release, and repair truck assignments.
- Sensors: flight service window, truck availability, disruption notices.

### Environment properties

- Partially observable: each agent sees only its own schedule and the shared flight messages.
- Stochastic: delays change the available windows during operation.
- Dynamic: arrivals and assignments change while planning is in progress.
- Resource-constrained: gates, crews, and trucks are all limited.
- Cooperative: the agents jointly seek a conflict-free turnaround plan.

## Run the demo

```bash
python -m flightops.demo
```

The demo prints a standard operating schedule and a cascading delay stress test. The stress test includes a delayed wide-body flight that can only use wide-body-capable gates, forcing live renegotiation and a displacement chain.

## Test

```bash
python -m unittest
```
