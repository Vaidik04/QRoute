from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(prefix="/transit", tags=["transit"])

@router.get("/stops", response_model=List[Dict[str, Any]])
def get_transit_stops():
    return [
        {"stop_id": "TS_01", "name": "Bhopal Junction Railway Station", "lat": 23.2667, "lng": 77.4100},
        {"stop_id": "TS_02", "name": "Habibganj Bus Station (ISBT)", "lat": 23.2300, "lng": 77.4350},
        {"stop_id": "TS_03", "name": "Board Office Square", "lat": 23.2333, "lng": 77.4333}
    ]

@router.get("/routes", response_model=List[Dict[str, Any]])
def get_transit_routes():
    return [
        {"route_id": "TR_101", "short_name": "TR-1", "long_name": "Bhopal Station to AIIMS Hospital", "type": "BUS"},
        {"route_id": "TR_102", "short_name": "TR-2", "long_name": "Bairagarh to Mandideep Industrial Zone", "type": "BUS"}
    ]
