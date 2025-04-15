# Chatbot API with S3-backed Memory Using LangChain and LangGraph with Fastapi

A sophisticated chatbot implementation using LangChain and LangGraph with persistent memory storage in AWS S3. This project demonstrates advanced conversational AI capabilities with state management and asynchronous processing.

## Architecture Overview 

### Core Components

1. **Chat Service (`chat_service.py`)**
   - Main orchestrator for chat interactions
   - Manages conversation flow and state
   - Integrates with LangChain for LLM interactions
   - Handles session management and message routing

2. **S3 Memory Saver (`s3_memory_saver.py`)**
   - Provides persistent storage for chat histories
   - Implements async S3 operations using aioboto3
   - Handles serialization/deserialization of LangChain messages
   - Supports automatic cleanup of old chat sessions

### Key Features

- **Persistent Memory**: Chat histories are stored in S3 for long-term persistence
- **Async Processing**: Built with async/await patterns for efficient I/O operations
- **Session Management**: Unique session IDs for conversation tracking
- **Message Serialization**: Custom JSON encoding for LangChain message types
- **Automatic Cleanup**: Configurable cleanup of old chat sessions
- **Language Support**: Multi-language support with configurable language settings
- **Rate Limiting**: Built-in rate limiting for API calls
- **Error Handling**: Comprehensive error handling and logging

## Setup Instructions

### Prerequisites

- Python 3.8+
- AWS Account with S3 access
- Required Python packages (see `requirements.txt`)
- Groq API key for LLM access
- LangSmith API key for tracing (optional)

### Environment Configuration

1. Create a `.env` file with the following variables:
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
S3_BUCKET_NAME=your_bucket_name
GROQ_API_KEY=your_groq_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
RATE_LIMIT_CALLS=50
RATE_LIMIT_PERIOD=60
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
python main.py
```

The server will start on `http://0.0.0.0:8000`

### Chat Service Integration

```python
from services.chat_service import ChatService
from models.chat import ChatRequest

# Initialize the chat service
chat_service = ChatService()

# Create a chat request
request = ChatRequest(
    message="Hello!",
    thread_id="unique_session_id",  # Optional
    language="English"  # Default
)

# Process the chat request
response = await chat_service.process_chat(request)
```

## API Endpoints

### Chat Endpoint

- **POST** `/chat`
  - Process a chat message and return the response
  - Request body:
    ```json
    {
        "message": "User message",
        "thread_id": "optional_session_id",
        "language": "English"
    }
    ```
  - Response:
    ```json
    {
        "response": "Assistant's response",
        "language": "English"
    }
    ```

### Chat History Endpoint

- **GET** `/chat/history/{thread_id}`
  - Retrieve chat history for a specific session
  - Response:
    ```json
    {
        "messages": [
            {
                "content": "Message content",
                "role": "human|assistant",
                "timestamp": "2024-01-01T12:00:00"
            }
        ]
    }
    ```

## Configuration

### Rate Limiting

The chat service implements rate limiting using the `ratelimit` decorator:
```python
@sleep_and_retry
@limits(calls=50, period=60)  # 50 calls per minute
def create_llm():
    return ChatGroq(model="llama3-8b-8192")
```

### LangChain Integration

The project uses LangChain for:
- Chat prompt templates
- Message state management
- LLM interactions with Groq
- Conversation memory management

### LangGraph Integration

LangGraph is used for:
- State management
- Workflow orchestration
- Checkpoint management
- Async processing

### S3 Storage Structure

Chat histories are stored in S3 with the following structure:
- Bucket: `{S3_BUCKET_NAME}`
- Key format: `chat_histories/{session_id}.json`
- Content format:
  ```json
  {
      "state": {
          "messages": [...],
          "language": "English"
      },
      "metadata": {
          "timestamp": "2024-01-01T12:00:00",
          "language": "English"
      },
      "new_versions": {
          "messages": 1
      }
  }
  ```

## Error Handling

The application implements comprehensive error handling:
- S3 operation errors
- Rate limiting exceptions
- LLM service errors
- Invalid message format errors
- Session management errors

All errors are logged using the Python `logging` module with appropriate log levels.

## Development Guidelines

### Adding New Features

1. Implement new functionality in appropriate service modules
2. Update the API endpoints if needed
3. Add appropriate error handling and logging
4. Update tests to cover new functionality
5. Follow async/await patterns for I/O operations
6. Maintain backward compatibility

### Testing

Run tests using:
```bash
python -m pytest tests/
```

The project includes:
- Unit tests
- Integration tests
- End-to-end tests
- Performance tests

## License

This project is licensed under the MIT License - see the LICENSE file for details.