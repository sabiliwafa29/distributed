"""Tests for health check endpoints."""


def test_health_check(client):
    """Test basic health check."""
    response = client.get("/api/v1/health/")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data
