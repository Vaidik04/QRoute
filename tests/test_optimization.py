import time

def test_delivery_optimization_flow(client):
    payload = {
        "depot": {"lat": 23.2599, "lon": 77.4126},
        "vehicles": [
            {"id": "V1", "vehicle_code": "V-101", "capacity": 100.0},
            {"id": "V2", "vehicle_code": "V-102", "capacity": 120.0}
        ],
        "customers": [
            {"id": "C1", "name": "MP Nagar Zone 1 Mall", "location": {"lat": 23.2332, "lon": 77.4365}, "demand": 15.0},
            {"id": "C2", "name": "New Market Retail Hub", "location": {"lat": 23.2366, "lon": 77.4012}, "demand": 20.0},
            {"id": "C3", "name": "Bhopal Station Logistics", "location": {"lat": 23.2678, "lon": 77.4145}, "demand": 25.0},
            {"id": "C4", "name": "Bairagarh Commercial", "location": {"lat": 23.2750, "lon": 77.3500}, "demand": 10.0},
            {"id": "C5", "name": "Karond Market", "location": {"lat": 23.2900, "lon": 77.4100}, "demand": 12.0}
        ],
        "objective": {"time": 0.5, "distance": 0.2, "congestion": 0.3},
        "algorithm": "adaptive_d_qpso"
    }
    
    # 1. Submit optimization job
    response = client.post("/api/v1/optimization/delivery", json=payload)
    assert response.status_code == 200
    data = response.json()
    opt_id = data["optimization_id"]
    assert data["status"] == "QUEUED"

    # 2. Wait briefly for async background worker execution
    time.sleep(1.0)

    # 3. Poll status
    status_resp = client.get(f"/api/v1/optimization/{opt_id}")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["id"] == opt_id
    assert st_data["algorithm"] == "adaptive_d_qpso"
    assert st_data["status"] in ["QUEUED", "RUNNING", "COMPLETED"]

    # 4. Check convergence data
    conv_resp = client.get(f"/api/v1/optimization/{opt_id}/convergence")
    assert conv_resp.status_code == 200
    conv_data = conv_resp.json()
    assert len(conv_data) > 0
