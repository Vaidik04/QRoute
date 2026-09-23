from fastapi.testclient import TestClient

def test_traffic_negative_speed_rejection(client: TestClient):
    # Phase 4 constraint: Reject invalid negative speed inputs before reaching optimizer
    payload = {
        "internal_edge_id": "edge_test_101",
        "current_speed_kph": -15.0,  # invalid negative speed
        "congestion_factor": 1.5
    }
    response = client.post("/api/v1/traffic/update", json=payload)
    assert response.status_code == 422
    err_data = response.json()
    assert "error" in err_data
    assert err_data["error"]["code"] == "VALIDATION_ERROR"

def test_dynamic_rerouting_orchestration(client: TestClient):
    # 1. Seed demo dataset first
    client.post("/api/v1/demo/seed")

    # 2. Ingest valid high-congestion traffic update triggering Phase 8 orchestration
    traffic_event = {
        "internal_edge_id": "edge_junc_to_mpnagar",
        "current_speed_kph": 12.0,
        "congestion_factor": 2.2,
        "jam_length_meters": 450.0
    }
    resp = client.post("/api/v1/traffic/update", json=traffic_event)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REOPTIMIZED_AND_BROADCAST"
    assert "vehicle_id" in data
    assert "new_route_id" in data
