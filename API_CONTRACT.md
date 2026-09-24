# Q-TRANSIT NEXUS — API CONTRACT & INTEGRATION SPECIFICATION

This document outlines the API contracts and architectural boundaries owned by **Member 3 (Backend + Database + Orchestration)** for the Q-TRANSIT NEXUS platform.

---

## 1. System Pipeline

```
USER ──► FRONTEND ──► FASTAPI BACKEND ──► DATABASE & SERVICES ──► [TRAFFIC / OPTIMIZATION / SUMO]
                                 ▲                                           │
                                 └───────────────────────────────────────────┘
```

---

## 2. API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System health check (DB, Traffic, Optimizer, SUMO) |
| `POST` | `/api/v1/trips/route` | Point-to-point shortest route request |
| `GET` | `/api/v1/trips/history` | Historical saved trips |
| `GET` | `/api/v1/locations/search` | Location search with Bhopal network hubs |
| `POST` | `/api/v1/optimization/delivery` | Submit VRP delivery optimization job (Adaptive D-QPSO) |
| `POST` | `/api/v1/optimization/run` | Alias endpoint for optimization jobs |
| `GET` | `/api/v1/optimization/{opt_id}` | Poll optimization job status & solution routes |
| `GET` | `/api/v1/optimization/{opt_id}/convergence` | Quantum Lab convergence iteration data |
| `GET` | `/api/v1/optimization/{opt_id}/metrics` | Solution distance, delay, congestion & penalty metrics |
| `GET` | `/api/v1/traffic/current` | Live edge traffic speed & congestion states |
| `GET` | `/api/v1/traffic/edge/{edge_id}` | Detailed edge traffic state |
| `GET` | `/api/v1/traffic/prediction` | ML predicted speed & travel time horizon (T+10m) |
| `GET` | `/api/v1/incidents` | List active traffic incidents |
| `POST` | `/api/v1/incidents` | Report a road closure or accident incident |
| `POST` | `/api/v1/simulation/start` | Start SUMO simulation session |
| `GET` | `/api/v1/simulation/{sim_id}` | Fetch current simulation step state & vehicle positions |
| `POST` | `/api/v1/simulation/{sim_id}/incident` | Inject simulation incident & trigger dynamic re-optimization loop |
| `GET` | `/api/v1/simulation/{sim_id}/metrics` | Simulation metrics (average delay, queue, throughput) |
| `GET` | `/api/v1/transit/routes` | Public transport BRTS & bus routes |
| `GET` | `/api/v1/transit/stops` | BRTS stops and hubs |
| `GET` | `/api/v1/ev/charging-stations` | EV Fast Chargers in Bhopal |
| `POST` | `/api/v1/ev/route` | EV route calculation with SoC consumption estimates |
| `GET` | `/api/v1/analytics/comparison` | Baseline vs. Q-TRANSIT optimized comparison analytics |
| `GET` | `/api/v1/analytics/traffic` | Traffic dashboard metrics |
| `POST` | `/api/v1/benchmarks/run` | Run comparative benchmark suite (PSO, GA, ACO, QPSO, Adaptive D-QPSO) |
| `POST` | `/api/v1/demo/reset` | Reset demo state to clean initial Bhopal configuration |
| `GET` | `/api/v1/demo/scenarios` | Predefined demo presentation scenarios |
| `WS` | `/api/v1/ws` | Real-time WebSocket event broadcasting stream |

---

## 3. Real-Time WebSocket Events

Client connects to `ws://<host>:<port>/api/v1/ws`.

### Events Broadcast:
1. `traffic_update`: Live speed & congestion updates
2. `optimization_progress`: Iteration and fitness progress during QPSO solving
3. `route_changed`: Dynamic reroute notification emitted when road closures occur
4. `simulation_update`: Step update of vehicle positions

---

## 4. Team Member Integration Contracts

### To Member 1 (Optimization Brain)
- **Contract Interface**: `OptimizationAdapter.solve(VRPProblem) -> OptimizationResult`
- Backend handles API validation, database queries, graph distance matrices, convergence persistence, and GeoJSON geometry construction.

### To Member 2 (Traffic & Simulation World)
- **Contract Interface**: `TrafficAdapter`, `SUMOAdapter`, `OrchestrationService.handle_traffic_change_event(...)`
- Backend exposes edge traffic, predictions, and TraCI simulation triggers cleanly.

### To Member 4 (Frontend UI)
- **Contract Interface**: REST `/api/v1/...` and WebSocket `ws://...`
- Frontend does not query raw database tables or invoke Python modules directly.

### To Member 5 (Research & Benchmarking)
- **Contract Interface**: `POST /api/v1/benchmarks/run` & `/api/v1/optimization/{id}/convergence`
- Complete reproducible records containing seed, dataset, iteration convergence curve, runtime, and optimality gap.

### To Member 6 (Demo & Scenarios)
- **Contract Interface**: `POST /api/v1/demo/reset` & `/api/v1/demo/scenarios`
- Enables one-click reset to clean presentation scenarios.
