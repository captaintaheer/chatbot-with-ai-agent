import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from src.services.chat_service import ChatService
from src.models.chat import ChatRequest, ChatResponse

@pytest.fixture
def chat_service():
    return ChatService()

@pytest.fixture
def mock_memory():
    return Mock()

@pytest.fixture
def mock_llm():
    return Mock()

@pytest.mark.asyncio
async def test_process_chat_success(chat_service, mock_memory, mock_llm):
    # Arrange
    chat_service.memory = mock_memory
    chat_service.llm = mock_llm
    request = ChatRequest(message="Hello", language="English")
    mock_response = AIMessage(content="Hi there!")
    
    # Mock the LLM response
    mock_llm.ainvoke.return_value = mock_response
    
    # Mock the workflow app invoke
    chat_service.workflow_app.ainvoke.return_value = {
        "messages": [HumanMessage(content="Hello"), mock_response]
    }

    # Act
    response = await chat_service.process_chat(request)

    # Assert
    assert isinstance(response, ChatResponse)
    assert response.response == "Hi there!"
    assert response.language == "English"
    assert isinstance(response.timestamp, datetime)

@pytest.mark.asyncio
async def test_get_or_create_chat_history_new_session(chat_service, mock_memory):
    # Arrange
    chat_service.memory = mock_memory
    session_id = "test-session"
    mock_memory.get.return_value = None

    # Act
    history = chat_service.get_or_create_chat_history(session_id)

    # Assert
    assert isinstance(history, list)
    assert len(history) == 0
    assert session_id in chat_service.chat_histories

@pytest.mark.asyncio
async def test_get_or_create_chat_history_existing_session(chat_service, mock_memory):
    # Arrange
    chat_service.memory = mock_memory
    session_id = "test-session"
    existing_messages = [HumanMessage(content="Hello")]
    mock_memory.get.return_value = {"messages": existing_messages}

    # Act
    history = chat_service.get_or_create_chat_history(session_id)

    # Assert
    assert isinstance(history, list)
    assert len(history) == 1
    assert history[0].content == "Hello"

@pytest.mark.asyncio
async def test_save_checkpoint(chat_service, mock_memory):
    # Arrange
    chat_service.memory = mock_memory
    session_id = "test-session"
    messages = [HumanMessage(content="Hello"), AIMessage(content="Hi there!")]
    language = "English"

    # Act
    await chat_service._save_checkpoint(session_id, messages, language)

    # Assert
    mock_memory.put.assert_called_once()
    call_args = mock_memory.put.call_args[0]
    assert call_args[0] == session_id
    assert call_args[1]["messages"] == messages

def test_generate_session_id(chat_service):
    # Arrange
    message = "test message"

    # Act
    session_id = chat_service._generate_session_id(message)

    # Assert
    assert isinstance(session_id, str)
    assert "-" in session_id
    timestamp, hash_part = session_id.split("-")
    assert len(hash_part) == 8