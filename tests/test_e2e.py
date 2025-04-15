import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from src.models.chat import ChatRequest, ChatResponse
from app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_chat_endpoint_success(client):
    # Arrange
    request_data = {
        "message": "Hello",
        "language": "English"
    }

    # Act
    response = client.post("/chat", json=request_data)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data
    assert "language" in response_data
    assert response_data["language"] == "English"

def test_chat_endpoint_with_thread_id(client):
    # Arrange
    request_data = {
        "message": "Hello",
        "language": "English",
        "thread_id": "test-thread"
    }

    # Act
    response = client.post("/chat", json=request_data)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert "response" in response_data

def test_chat_endpoint_conversation_flow(client):
    # Test a complete conversation flow with multiple messages
    # First message
    response1 = client.post("/chat", json={
        "message": "Hello",
        "language": "English",
        "thread_id": "test-conversation"
    })
    assert response1.status_code == 200
    thread_response1 = response1.json()

    # Second message in same thread
    response2 = client.post("/chat", json={
        "message": "How are you?",
        "language": "English",
        "thread_id": "test-conversation"
    })
    assert response2.status_code == 200
    thread_response2 = response2.json()

    # Verify both responses are valid
    assert "response" in thread_response1
    assert "response" in thread_response2

def test_chat_endpoint_error_handling(client):
    # Test with invalid request data
    response = client.post("/chat", json={})
    assert response.status_code == 422  # Validation error

    # Test with invalid language
    response = client.post("/chat", json={
        "message": "Hello",
        "language": ""
    })
    assert response.status_code == 200  # Should default to English

def test_chat_endpoint_performance(client):
    # Test response time for a simple request
    import time
    start_time = time.time()
    
    response = client.post("/chat", json={
        "message": "Hello",
        "language": "English"
    })
    
    end_time = time.time()
    response_time = end_time - start_time
    
    assert response.status_code == 200
    assert response_time < 5  # Response should be under 5 seconds