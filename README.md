# Q-TRANSIT NEXUS — Member 3 Work Package Complete System

Central Nervous System Backend, Data Pipeline, Database Schema, System Orchestrator & Control Dashboard for **Q-TRANSIT NEXUS**.

---

## 🌟 Key Features

1. **FastAPI Modular Microservices Architecture**: API v1 router structure with clean separation across controllers, services, repositories, schemas, models, and adapters.
2. **PostgreSQL / PostGIS & SQLite Dual ORM Engine**: Complete SQLAlchemy models for Users, Vehicles, Customers, Deliveries, RoadNodes, RoadEdges, TrafficStates, Predictions, Incidents, Trips, Routes, OptimizationRuns, Solutions, Convergence Iterations, Simulations, and Benchmarks.
3. **Pluggable Optimization Adapter**: Interface converting API requests to VRP Problem definitions for Member 1's **Adaptive D-QPSO**, QPSO, PSO, GA, and ACO algorithms.
4. **Traffic & SUMO Simulation Adapters**: Live edge traffic status, ML predictions (T+10m horizon), TraCI simulation wrapper & high-fidelity simulator fallback.
5. **Real-Time WebSockets Engine**: Live event streaming for `traffic_update`, `optimization_progress`, `route_changed`, and `simulation_update`.
6. **Dynamic Feedback Rerouting Loop**: End-to-end event handler that ingests road closures, re-evaluates affected vehicles, executes Adaptive D-QPSO re-optimization, applies updated routes to SUMO, and streams GeoJSON route changes over WebSockets.
7. **Interactive Dashboard Control Panel**: Embedded Leaflet map, Chart.js Quantum Lab convergence visualizer, incident injector, and live orchestration event log ticker.
8. **Automated Test Suite**: Pytest suite verifying health, trips, optimization jobs, traffic APIs, simulation lifecycle, and dynamic rerouting.

---

## 🚀 Quick Start (Local Run)

### 1. Activate Environment & Run Backend
```bash
# Environment is pre-configured
python scripts/run_dev.py
```
Open **http://127.0.0.1:8000** in your browser to view the interactive Control Dashboard!
Open **http://127.0.0.1:8000/api/v1/docs** for the OpenAPI Swagger UI!

### 2. Run Test Suite
```bash
pytest -v
```

### 3. Docker Deployment
```bash
docker compose up --build
```
Starts backend, PostgreSQL/PostGIS, and Redis containers.

---

## 📂 System Directory Layout

```
qroute_mem3/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── api/                     # REST & WebSocket Endpoints
│   │   ├── core/                    # Config, Security, Logging, Exceptions
│   │   ├── db/                      # Session, Base, Seeders, Migrations
│   │   ├── models/                  # SQLAlchemy ORM Data Models
│   │   ├── schemas/                 # Pydantic Schemas
│   │   ├── adapters/                # Optimization, Traffic & SUMO Adapters
│   │   ├── repositories/            # Data Access Layer
│   │   ├── services/                # Business Logic Services
│   │   ├── workers/                 # Background Job Pool
│   │   └── utils/                   # GeoJSON & Graph Mapper Utils
│   └── alembic/                     # Alembic Migrations
├── frontend/                        # Web Visual Control Dashboard
├── tests/                           # Pytest Test Suite
├── scripts/                         # Seeder & Runner Scripts
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── API_CONTRACT.md                  # Integration Contracts for Team Members
```
