from fastapi import APIRouter
from app.api.routes import (
    health,
    vehicles,
    customers,
    deliveries,
    trips,
    incidents,
    traffic,
    optimization,
    simulation,
    analytics,
    demo,
    benchmarks,
    transit,
    ev
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(vehicles.router)
api_router.include_router(customers.router)
api_router.include_router(deliveries.router)
api_router.include_router(trips.router)
api_router.include_router(incidents.router)
api_router.include_router(traffic.router)
api_router.include_router(optimization.router)
api_router.include_router(simulation.router)
api_router.include_router(analytics.router)
api_router.include_router(demo.router)
api_router.include_router(benchmarks.router)
api_router.include_router(transit.router)
api_router.include_router(ev.router)
