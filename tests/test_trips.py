def test_plan_trip_route(client):
    payload = {
        "origin": {"lat": 23.2599, "lon": 77.4126},
        "destination": {"lat": 23.2366, "lon": 77.4012},
        "mode": "car",
        "objective": "balanced"
    }
    response = client.post("/api/v1/trips/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "trip_id" in data
    assert "route_id" in data
    assert data["status"] == "FEASIBLE"
    assert data["summary"]["distance_km"] > 0
    assert data["geometry"]["type"] == "FeatureCollection"

def test_location_search(client):
    response = client.get("/api/v1/locations/search?q=Board%20Office")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "Board Office Square" in data[0]["name"]
