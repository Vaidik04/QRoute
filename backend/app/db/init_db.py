import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.models import (
    RoadNode,
    RoadEdge,
    TrafficState,
    Vehicle,
    Customer
)

def init_db(db: Session):
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    # Check if network already seeded
    if db.query(RoadNode).first():
        return

    # Bhopal Canonical Road Network Nodes
    nodes_data = [
        {"id": "NODE_HAMIDIA", "external_node_id": "OSM_101", "lat": 23.2599, "lon": 77.4126, "node_type": "depot"},
        {"id": "NODE_NEW_MARKET", "external_node_id": "OSM_102", "lat": 23.2366, "lon": 77.4012, "node_type": "junction"},
        {"id": "NODE_BOARD_OFFICE", "external_node_id": "OSM_103", "lat": 23.2323, "lon": 77.4326, "node_type": "junction"},
        {"id": "NODE_MP_NAGAR", "external_node_id": "OSM_104", "lat": 23.2332, "lon": 77.4365, "node_type": "customer_stop"},
        {"id": "NODE_BHOPAL_JN", "external_node_id": "OSM_105", "lat": 23.2678, "lon": 77.4145, "node_type": "transit_hub"}
    ]

    for n in nodes_data:
        db.add(RoadNode(
            id=n["id"],
            external_node_id=n["external_node_id"],
            lat=n["lat"],
            lon=n["lon"],
            node_type=n["node_type"]
        ))
    db.commit()

    # Bhopal Canonical Road Network Edges
    edges_data = [
        {"id": "R17", "sumo": "e_hamidia_board", "from": "NODE_HAMIDIA", "to": "NODE_BOARD_OFFICE", "length": 4200.0, "speed": 50.0},
        {"id": "R18", "sumo": "e_board_mpnagar", "from": "NODE_BOARD_OFFICE", "to": "NODE_MP_NAGAR", "length": 1500.0, "speed": 40.0},
        {"id": "R19", "sumo": "e_mpnagar_newmarket", "from": "NODE_MP_NAGAR", "to": "NODE_NEW_MARKET", "length": 3200.0, "speed": 45.0},
        {"id": "R20", "sumo": "e_newmarket_hamidia", "from": "NODE_NEW_MARKET", "to": "NODE_HAMIDIA", "length": 3800.0, "speed": 50.0},
        {"id": "R21", "sumo": "e_hamidia_bhopaljn", "from": "NODE_HAMIDIA", "to": "NODE_BHOPAL_JN", "length": 1800.0, "speed": 40.0}
    ]

    for e in edges_data:
        db.add(RoadEdge(
            id=e["id"],
            sumo_edge_id=e["sumo"],
            from_node_id=e["from"],
            to_node_id=e["to"],
            length_m=e["length"],
            speed_limit_kmh=e["speed"],
            geometry_json=json.dumps([[77.4126, 23.2599], [77.4326, 23.2323]])
        ))

        # Initial clean traffic state
        db.add(TrafficState(
            id=str(uuid.uuid4()),
            edge_id=e["id"],
            timestamp=datetime.utcnow(),
            speed_kmh=e["speed"],
            travel_time_sec=round((e["length"] / (e["speed"] * 1000 / 3600)), 1),
            congestion=0.15,
            status="OPEN",
            source="INITIAL_SEED"
        ))
    db.commit()

    # Seed Demo Delivery Fleet
    db.add(Vehicle(id="V1", vehicle_code="V-101", type="van", capacity=100.0, status="IDLE"))
    db.add(Vehicle(id="V2", vehicle_code="V-102", type="van", capacity=120.0, status="IDLE"))
    db.add(Vehicle(id="V3", vehicle_code="V-EV-01", type="ev", capacity=80.0, battery_capacity=60.0, current_battery=52.0, status="IDLE"))
    db.commit()

    # Seed Demo Customers
    db.add(Customer(id="C1", customer_code="CUST-101", name="MP Nagar Zone 1 Mall", lat=23.2332, lon=77.4365, demand=15.0, priority=1))
    db.add(Customer(id="C2", customer_code="CUST-102", name="New Market Retail Hub", lat=23.2366, lon=77.4012, demand=20.0, priority=2))
    db.add(Customer(id="C3", customer_code="CUST-103", name="Bhopal Station Logistics", lat=23.2678, lon=77.4145, demand=25.0, priority=1))
    db.commit()
