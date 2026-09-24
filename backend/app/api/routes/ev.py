from fastapi import APIRouter, Depends
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.session import get_db

router = APIRouter()

@router.get("/ev/charging-stations")
def get_charging_stations():
    return [
        {
            "id": "EV_CS_01",
            "name": "Bhopal Smart City Fast Charger",
            "location": {"lat": 23.2340, "lon": 77.4350},
            "power_kw": 60.0,
            "connectors": ["CCS2", "Type2"],
            "available_ports": 3,
            "total_ports": 4
        },
        {
            "id": "EV_CS_02",
            "name": "MP Nagar EV Charging Hub",
            "location": {"lat": 23.2310, "lon": 77.4380},
            "power_kw": 120.0,
            "connectors": ["CCS2"],
            "available_ports": 2,
            "total_ports": 2
        }
    ]

@router.post("/ev/route")
def calculate_ev_route(req: Dict[str, Any]):
    return {
        "status": "FEASIBLE",
        "mode": "ev",
        "battery_soc_initial": req.get("battery_soc", 80.0),
        "battery_soc_arrival": 52.4,
        "charging_stops_required": 0,
        "energy_kwh_consumed": 8.4,
        "geometry": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.4126, 23.2599], [77.4350, 23.2340], [77.4012, 23.2366]]
                    }
                }
            ]
        }
    }
