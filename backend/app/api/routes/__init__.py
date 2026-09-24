from fastapi import APIRouter
from backend.app.api.routes import (
    health,
    trip,
    optimization,
    traffic,
    incidents,
    simulation,
    transit,
    ev,
    analytics,
    benchmarks,
    demo
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(trip.router, tags=["Trips"])
api_router.include_router(optimization.router, tags=["Optimization"])
api_router.include_router(traffic.router, tags=["Traffic"])
api_router.include_router(incidents.router, tags=["Incidents"])
api_router.include_router(simulation.router, tags=["Simulation"])
api_router.include_router(transit.router, tags=["Transit"])
api_router.include_router(ev.router, tags=["EV Routing"])
api_router.include_router(analytics.router, tags=["Analytics"])
api_router.include_router(benchmarks.router, tags=["Benchmarks"])
api_router.include_router(demo.router, tags=["Demo Mode"])
