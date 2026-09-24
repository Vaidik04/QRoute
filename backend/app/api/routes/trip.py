from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.app.db.session import get_db
from backend.app.schemas.trip import TripRouteRequest, TripRouteResponse
from backend.app.services.trip_service import trip_service

router = APIRouter()

@router.post("/trips/route", response_model=TripRouteResponse)
def plan_trip_route(req: TripRouteRequest, db: Session = Depends(get_db)):
    return trip_service.plan_route(db, req)

@router.get("/trips/history")
def get_trip_history(db: Session = Depends(get_db)):
    return [
        {
            "id": "TRIP_001",
            "date": "2026-09-24T18:30:00Z",
            "origin": {"name": "Hamidia Hospital", "lat": 23.2599, "lon": 77.4126},
            "destination": {"name": "New Market", "lat": 23.2366, "lon": 77.4012},
            "mode": "car",
            "distance_km": 4.8,
            "travel_time_min": 11.2,
            "status": "COMPLETED"
        }
    ]

@router.get("/locations/search")
def search_locations(q: str = Query("Board Office")):
    bhopal_places = [
        {"name": "Board Office Square", "latitude": 23.2323, "longitude": 77.4326, "type": "junction"},
        {"name": "MP Nagar Zone 1", "latitude": 23.2332, "longitude": 77.4365, "type": "commercial_hub"},
        {"name": "New Market", "latitude": 23.2366, "longitude": 77.4012, "type": "market"},
        {"name": "Hamidia Hospital", "latitude": 23.2599, "longitude": 77.4126, "type": "hospital"},
        {"name": "Bhopal Junction Railway Station", "latitude": 23.2678, "longitude": 77.4145, "type": "transit_hub"}
    ]
    query_lower = q.lower()
    matches = [p for p in bhopal_places if query_lower in p["name"].lower()]
    return matches or bhopal_places[:3]
