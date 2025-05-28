def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200

# Ajoute le client de test dans conftest.py ou test_routes.py
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app("test")
    with app.test_client() as client:
        yield client
