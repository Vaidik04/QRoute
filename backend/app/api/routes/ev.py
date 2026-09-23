from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/ev", tags=["ev"])

@router.get("/charging-stations", response_model=List[Dict[str, Any]])
def get_charging_stations():
    return [
        {"station_id": "EV_STAT_01", "name": "Bhopal Smart City EV Hub", "lat": 23.2350, "lng": 77.4300, "total_chargers": 8, "available_chargers": 5, "power_kw": 50.0},
        {"station_id": "EV_STAT_02", "name": "MP Nagar Fast Charger", "lat": 23.2310, "lng": 77.4370, "total_chargers": 4, "available_chargers": 2, "power_kw": 120.0}
    ]

@router.post("/route", response_model=Dict[str, Any])
def compute_ev_route(payload: Dict[str, Any]):
    return {
        "status": "COMPLETED",
        "mode": "ev",
        "estimated_energy_kwh": 4.2,
        "charging_stops_required": 0,
        "recommended_charging_station": "EV_STAT_01"
    }

@router.get("/vehicle/{vehicle_id}", response_model=Dict[str, Any])
def get_ev_vehicle_state(vehicle_id: str):
    return {
        "vehicle_id": vehicle_id,
        "battery_capacity_kwh": 60.0,
        "current_battery_kwh": 45.5,
        "soc_percentage": 75.8,
        "health": "GOOD"
    }
