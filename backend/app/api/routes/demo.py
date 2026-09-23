from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.base import Base
from app.repositories.fleet import VehicleRepository, CustomerRepository, DeliveryRepository
from app.repositories.network import NetworkRepository
from app.repositories.traffic import TrafficRepository
from app.repositories.benchmarks import BenchmarkRepository
from app.schemas.fleet import VehicleCreate, CustomerCreate, DeliveryCreate
from app.schemas.traffic import TrafficStateCreate
from app.core.logging import logger

router = APIRouter(prefix="/demo", tags=["Demo Mode & Seeding"])

@router.post("/seed", status_code=status.HTTP_201_CREATED, summary="Seed Bhopal road network & sample fleet dataset for demo")
def seed_demo_data(db: Session = Depends(get_db)):
    logger.info("Seeding demo data for Bhopal Q-TRANSIT NEXUS network...")

    net_repo = NetworkRepository(db)
    veh_repo = VehicleRepository(db)
    cust_repo = CustomerRepository(db)
    deliv_repo = DeliveryRepository(db)
    traffic_repo = TrafficRepository(db)
    bench_repo = BenchmarkRepository(db)

    # 1. Road Nodes (Bhopal Key Intersections)
    nodes_data = [
        ("node_bhopal_junction", 23.2599, 77.4126, "osm_101", "sumo_n1"),
        ("node_mp_nagar", 23.2332, 77.4343, "osm_102", "sumo_n2"),
        ("node_vip_road", 23.2625, 77.3850, "osm_103", "sumo_n3"),
        ("node_arera_colony", 23.2100, 77.4420, "osm_104", "sumo_n4"),
        ("node_indrapuri", 23.2510, 77.4650, "osm_105", "sumo_n5")
    ]
    created_nodes = {}
    for nid, lat, lng, osm_id, sumo_id in nodes_data:
        if not net_repo.get_node(nid):
            created_nodes[nid] = net_repo.create_node(nid, lat, lng, osm_id, sumo_id)

    # 2. Road Edges (Bhopal Arterials)
    edges_data = [
        ("edge_vip_to_junc", "node_vip_road", "node_bhopal_junction", 4500.0, 60.0, "way_501", "edge_sumo_1"),
        ("edge_junc_to_mpnagar", "node_bhopal_junction", "node_mp_nagar", 3200.0, 50.0, "way_502", "edge_sumo_2"),
        ("edge_mpnagar_to_arera", "node_mp_nagar", "node_arera_colony", 2800.0, 45.0, "way_503", "edge_sumo_3"),
        ("edge_mpnagar_to_indrapuri", "node_mp_nagar", "node_indrapuri", 3900.0, 50.0, "way_504", "edge_sumo_4")
    ]
    for eid, src, tgt, length, speed, osm_w, sumo_e in edges_data:
        if not net_repo.get_edge(eid):
            net_repo.create_edge(eid, src, tgt, length, speed, osm_w, sumo_e)

    # 3. Fleet Vehicles
    vehicles_data = [
        VehicleCreate(plate_number="MP04-AB-1001", vehicle_type="electric_van", capacity_weight=800.0, capacity_volume=8.0, current_lat=23.2599, current_lng=77.4126, status="IDLE"),
        VehicleCreate(plate_number="MP04-CD-2002", vehicle_type="heavy_truck", capacity_weight=2500.0, capacity_volume=25.0, current_lat=23.2332, current_lng=77.4343, status="IDLE"),
        VehicleCreate(plate_number="MP04-EF-3003", vehicle_type="delivery_truck", capacity_weight=1200.0, capacity_volume=12.0, current_lat=23.2625, current_lng=77.3850, status="IN_TRANSIT")
    ]
    created_vehs = []
    for v_in in vehicles_data:
        existing = veh_repo.get_by_plate(v_in.plate_number)
        if not existing:
            created_vehs.append(veh_repo.create(v_in))
        else:
            created_vehs.append(existing)

    # 4. Customers & Deliveries
    customers_data = [
        CustomerCreate(name="Bhopal Junction Cargo Hub", address="Station Road, Bhopal", lat=23.2599, lng=77.4126, time_window_start="08:00", time_window_end="18:00"),
        CustomerCreate(name="MP Nagar Commercial Complex", address="Zone-I, MP Nagar", lat=23.2332, lng=77.4343, time_window_start="09:00", time_window_end="17:00"),
        CustomerCreate(name="Arera Retail Hub", address="E-5 Arera Colony", lat=23.2100, lng=77.4420, time_window_start="10:00", time_window_end="16:00")
    ]
    created_custs = []
    for c_in in customers_data:
        created_custs.append(cust_repo.create(c_in))

    created_delivs = []
    for cust in created_custs:
        d_in = DeliveryCreate(customer_id=cust.id, package_weight=45.0, package_volume=0.5, priority=1, status="PENDING")
        created_delivs.append(deliv_repo.create(d_in))

    # 5. Traffic States
    traffic_data = [
        TrafficStateCreate(internal_edge_id="edge_vip_to_junc", current_speed_kph=55.0, congestion_factor=1.0, jam_length_meters=0.0),
        TrafficStateCreate(internal_edge_id="edge_junc_to_mpnagar", current_speed_kph=22.0, congestion_factor=1.6, jam_length_meters=250.0),
        TrafficStateCreate(internal_edge_id="edge_mpnagar_to_arera", current_speed_kph=40.0, congestion_factor=1.1, jam_length_meters=20.0)
    ]
    for ts_in in traffic_data:
        traffic_repo.create_traffic_state(ts_in)

    # 6. Benchmark Run
    bench_run = bench_repo.create_run("Bhopal Baseline vs Adaptive D-QPSO", "Demo benchmark comparing unoptimized legacy routing vs AI D-QPSO", "bhopal_core")
    bench_repo.add_result(bench_run.id, "total_travel_distance_km", 142.5, 110.2)
    bench_repo.add_result(bench_run.id, "total_travel_time_hours", 4.8, 3.2)
    bench_repo.add_result(bench_run.id, "fleet_emissions_kg_co2", 310.0, 225.0)

    return {
        "status": "DEMO_DATA_SEEDED",
        "nodes_count": len(nodes_data),
        "edges_count": len(edges_data),
        "vehicles_count": len(created_vehs),
        "customers_count": len(created_custs),
        "deliveries_count": len(created_delivs)
    }

@router.post("/reset", status_code=status.HTTP_200_OK, summary="Reset database state to clean initial state")
def reset_demo_database(db: Session = Depends(get_db)):
    logger.info("Resetting demo database tables...")
    try:
        from app.db.session import engine
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"status": "DATABASE_RESET_SUCCESSFUL"}
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return {"status": "DATABASE_RESET_FAILED", "detail": str(e)}
