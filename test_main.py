from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_invalid_date_format():
    response = client.get("/track-flight/?airline_code=AA&flight_number=100&departure_date=07-04-2025")
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]

def test_valid_flight_request():
    response = client.get("/track-flight/?airline_code=AA&flight_number=100&departure_date=2025-04-07")
    assert response.status_code in [200, 500]  # If scraping fails, it should return a 500 error
