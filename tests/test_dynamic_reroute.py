def test_dynamic_rerouting_flow(client):
    # 1. Start simulation
    sim_resp = client.post("/api/v1/simulation/start", json={
        "scenario": "evening_peak_closure",
        "vehicles": 20,
        "duration_sec": 1800
    })
    sim_id = sim_resp.json()["simulation_id"]

    # 2. Inject road closure incident
    incident_payload = {
        "affected_edges": ["R17", "R18"],
        "severity": "HIGH",
        "reason": "ROAD_CLOSURE"
    }
    resp = client.post(f"/api/v1/simulation/{sim_id}/incident", json=incident_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "INCIDENT_INJECTED"
    assert "orchestration" in data
    assert data["orchestration"]["status"] == "PROCESSED"
    assert data["orchestration"]["affected_vehicles_count"] > 0
    assert len(data["orchestration"]["reroutes"]) > 0
    assert data["orchestration"]["reroutes"][0]["algorithm"] == "adaptive_d_qpso"
