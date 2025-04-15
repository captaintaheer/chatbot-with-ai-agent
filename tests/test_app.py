import pytest
from fastapi.testclient import TestClient
from app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_chat_endpoint(client):
    response = client.post(
        "/chat",
        json={"message": "Hello", "conversation_id": "test-123"}
    )
    assert response.status_code == 200
    assert "response" in response.json()

@pytest.mark.asyncio
async def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}