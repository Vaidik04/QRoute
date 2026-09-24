from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.session import get_db

router = APIRouter()

@router.get("/transit/routes")
def get_transit_routes():
    return [
        {"route_id": "TR_01", "name": "Bhopal BRTS Trunk 1", "origin": "Habibganj", "destination": "Bairagarh", "type": "BRTS"},
        {"route_id": "TR_02", "name": "City Bus Circular 2", "origin": "Board Office", "destination": "Karond", "type": "BUS"}
    ]

@router.get("/transit/stops")
def get_transit_stops():
    return [
        {"stop_id": "ST_01", "name": "Board Office Square BRTS", "lat": 23.2323, "lon": 77.4326},
        {"stop_id": "ST_02", "name": "MP Nagar BRTS", "lat": 23.2332, "lon": 77.4365},
        {"stop_id": "ST_03", "name": "Roshanpura Square", "lat": 23.2389, "lon": 77.4089}
    ]
