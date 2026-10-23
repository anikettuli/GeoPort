import pytest
from fastapi.testclient import TestClient
from src.app import create_app

app = create_app()
client = TestClient(app)


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "GeoPort" in response.text
    assert "<!DOCTYPE html>" in response.text


def test_system_info():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "app_version" in data
    assert "platform" in data
    assert data["app_version"] == "5.0.0"


def test_devices_list():
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_search_coordinates():
    response = client.get("/api/search?q=37.7749,-122.4194")
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    assert pytest.approx(results[0]["latitude"], 0.001) == 37.7749
    assert pytest.approx(results[0]["longitude"], 0.001) == -122.4194


def test_search_text_landmark():
    response = client.get("/api/search?q=Sydney+Opera+House")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)


def test_simulation_status():
    response = client.get("/api/devices/fake-udid-123/status")
    assert response.status_code == 200
    data = response.json()
    assert data["udid"] == "fake-udid-123"
    assert data["is_active"] is False
    assert data["mode"] == "idle"


def test_gpx_route_validation():
    # Empty waypoints should fail validation
    response = client.post(
        "/api/devices/fake-udid-123/route/play",
        json={"waypoints": [], "loop": False},
    )
    assert response.status_code == 500 or response.status_code == 422


def test_fuel_endpoint():
    response = client.get("/api/fuel")
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
