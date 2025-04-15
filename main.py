import logging
import logging.config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import API_TITLE, API_DESCRIPTION, API_VERSION, LOGGING_CONFIG
from src.models.chat import ChatRequest, ChatResponse
from src.models.chat_history import ChatHistoryResponse
from src.services.chat_service import ChatService
from contextlib import asynccontextmanager

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Initialize chat service
chat_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize chat service
    global chat_service
    chat_service = await ChatService.create()
    yield
    # Shutdown: Add any cleanup code here if needed
    pass

# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        return await chat_service.process_chat(request)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/history/{thread_id}", response_model=ChatHistoryResponse)
async def get_chat_history(thread_id: str):
    try:
        response = await chat_service.get_chat_history(thread_id)
        if not response.messages:
            raise HTTPException(status_code=404, detail=f"No chat history found for thread {thread_id}")
        return response
    except HTTPException as he:
        logger.info(f"Chat history not found: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)