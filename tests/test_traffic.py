def test_current_traffic(client):
    response = client.get("/api/v1/traffic/current")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "edge_id" in data[0]
    assert "speed_kmh" in data[0]

def test_edge_traffic(client):
    response = client.get("/api/v1/traffic/edge/R17")
    assert response.status_code == 200
    data = response.json()
    assert data["edge_id"] == "R17"

def test_traffic_prediction(client):
    response = client.get("/api/v1/traffic/prediction?edge_id=R17&horizon_min=10")
    assert response.status_code == 200
    data = response.json()
    assert data["edge_id"] == "R17"
    assert data["horizon_min"] == 10
    assert "predicted_speed" in data
