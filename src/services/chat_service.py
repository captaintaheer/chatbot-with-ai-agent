import os
import logging
from typing import List, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from ratelimit import limits, sleep_and_retry
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph

from ..config.settings import MODEL_NAME, BASE_URL, RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from .s3_memory_saver import S3MemorySaver
from ..models.chat import ChatRequest, ChatResponse
from ..models.chat_history import ChatHistoryResponse, Message
from typing_extensions import TypedDict
import json
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

class Configuration(TypedDict):
    thread_id: str

class ChatService:
    def __init__(self):
        self.llm = None
        self.memory = None
        self.chat_histories = {}
        self.prompt_template = None
        self.workflow = None
        self.workflow_app = None

    @classmethod
    async def create(cls):
        service = cls()
        service.llm = service._create_llm()
        service.memory = S3MemorySaver(
            bucket_name=S3_BUCKET_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Load QA pairs from JSON file
        qa_pairs_path = "/Users/tahirolaosebikan/python-tahir/AGENTS/chatbot-poc/knowledge_base/qa_pairs.json"
        with open(qa_pairs_path) as f:
            service.qa_pairs = json.load(f)["qa_pairs"]
        
        service.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that answers questions based strictly on our knowledge base. 
            For any question, first determine if it relates to these topics:
            - Business hours
            - Password reset
            - Payment methods
            - Customer support contacts
            - Refund policies
            
            If the question relates to these topics but isn't an exact match, try to provide a helpful answer based on similar knowledge. 
            For completely unrelated questions, respond: "I can only answer questions about our business operations."""),
            MessagesPlaceholder(variable_name="messages"),
        ])
        service.workflow = service._setup_workflow()
        service.workflow_app = service.workflow.compile(checkpointer=service.memory)
        return service

    @sleep_and_retry
    @limits(calls=RATE_LIMIT_CALLS, period=RATE_LIMIT_PERIOD)
    def _create_llm(self):
        return ChatGroq(model=MODEL_NAME)
        # return ChatOpenAI(base_url=BASE_URL,
        #                   api_key=os.environ["DEEPSEEK_API_KEY"],
        #                   model=MODEL_NAME)

    def _setup_workflow(self):
        workflow = StateGraph(state_schema=MessagesState, config_schema=Configuration)
        workflow.add_edge(START, "model")
        workflow.add_node("model", self._call_model)
        return workflow


    async def _call_model(self, state: MessagesState, config: RunnableConfig):
        try:
            logger.info(f"Current state messages count: {len(state['messages'])}")
            last_message = state['messages'][-1].content.lower()
            
            # Enhanced topic keywords with more variations
            topic_keywords = {
                "business hours": ["hour", "open", "close", "time", "operating", "when do you"],
                "password reset": [
                    "password", "login", "account", "reset", "forgot", 
                    "recover", "change", "update", "lost", "cant log", "can't log",
                    "how do i reset", "how to reset", "how can i reset"
                ],
                "payment methods": ["pay", "payment", "credit card", "invoice", "method", "how to pay"],
                "customer support": ["contact", "support", "help", "email", "phone", "reach", "speak to"],
                "refund policy": ["refund", "return", "money back", "guarantee", "cancel", "get money back"]
            }
            
            # First check for exact matches
            for pair in self.qa_pairs:
                if pair["question"].lower() in last_message:
                    return {
                        "messages": state['messages'] + [
                            AIMessage(content=pair["answer"])
                        ]
                    }
            
            # Then check for related questions with more flexible matching
            for topic, keywords in topic_keywords.items():
                if any(f" {kw} " in f" {last_message} " for kw in keywords):
                    relevant_pair = next((p for p in self.qa_pairs if topic in p["question"].lower()), None)
                    if relevant_pair:
                        return {
                            "messages": state['messages'] + [
                                AIMessage(content=relevant_pair['answer'])
                            ]
                        }
            
            # If no match found
            return {
                "messages": state['messages'] + [
                    AIMessage(content="I can only answer questions about our business operations.")
                ]
            }
        except Exception as e:
            logger.error(f"Error in call_model: {str(e)}")
            raise

    async def get_or_create_chat_history(self, session_id: str) -> List[BaseMessage]:
        if session_id not in self.chat_histories:
            try:
                checkpoint = await self.memory.get(session_id)
                if checkpoint and isinstance(checkpoint, dict) and "messages" in checkpoint:
                    self.chat_histories[session_id] = checkpoint["messages"]
                    logger.info(f"Loaded {len(self.chat_histories[session_id])} messages from checkpoint")
                else:
                    logger.info(f"No existing checkpoint found for session {session_id}")
                    self.chat_histories[session_id] = []
            except Exception as e:
                logger.warning(f"Could not load checkpoint for session {session_id}: {e}")
                self.chat_histories[session_id] = []
        return self.chat_histories[session_id]

    def _format_response(self, text: str) -> str:
        """Format the response text for better readability."""
        # Remove extra whitespace and normalize line endings
        text = text.strip()
        
        # Split into paragraphs and filter out empty ones
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Join paragraphs with double newline for clear separation
        return '\n\n'.join(paragraphs)

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        try:
            session_id = request.thread_id or self._generate_session_id(request.message)
            logger.info(f"Using session with ID: {session_id}")
            logger.info(f"Request language: {request.language}")

            chat_history = await self.get_or_create_chat_history(session_id)
            chat_history.append(HumanMessage(content=request.message))

            config = {"configurable": {"thread_id": session_id}}
            output = await self.workflow_app.ainvoke(
                {"messages": chat_history, "language": request.language},
                config=config
            )

            if "messages" in output:
                self.chat_histories[session_id] = output["messages"]
                await self._save_checkpoint(session_id, output["messages"], request.language)
                # Apply formatting to the response content before returning
                raw_response = output["messages"][-1].content
                formatted_response = self._format_response(raw_response)
                return ChatResponse(response=formatted_response, language=request.language, timestamp=datetime.now())
            else:
                raise ValueError("No response generated")
        except Exception as e:
            logger.error(f"Error processing chat: {str(e)}")
            raise

    async def _save_checkpoint(self, session_id: str, messages: List[BaseMessage], language: str) -> None:
        try:
            await self.memory.put(
                session_id,
                {"messages": messages, "language": language},
                metadata={"timestamp": datetime.now().isoformat(), "language": language},
                new_versions={"messages": len(messages)}
            )
            logger.info(f"Successfully saved checkpoint for session {session_id}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {str(e)}")
            raise

    def _generate_session_id(self, message: str) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        hash_part = format(hash(message) % (2**32), '08x')
        return f"{timestamp}-{hash_part}"

    async def get_chat_history(self, thread_id: str) -> ChatHistoryResponse:
        try:
            checkpoint = await self.memory.get(thread_id)
            if not checkpoint or not isinstance(checkpoint, dict) or "messages" not in checkpoint:
                logger.info(f"No chat history found for thread {thread_id}")
                return ChatHistoryResponse(
                    thread_id=thread_id,
                    messages=[],
                    language="English"
                )

            messages = []
            # Process messages in pairs to group human and assistant interactions
            msg_list = checkpoint["messages"]
            for i in range(0, len(msg_list), 2):
                # Get the human message
                human_msg = msg_list[i]
                if not isinstance(human_msg, HumanMessage):
                    continue
                
                # Get the corresponding assistant message if it exists
                assistant_msg = msg_list[i + 1] if i + 1 < len(msg_list) else None
                
                # Create timestamp for the conversation pair
                current_time = datetime.now()
                
                # Add human message
                messages.append(Message(
                    content=human_msg.content,
                    role="human",
                    timestamp=current_time
                ))
                
                # Add assistant message if it exists
                if assistant_msg:
                    messages.append(Message(
                        content=assistant_msg.content,
                        role="assistant",
                        timestamp=current_time
                    ))

            return ChatHistoryResponse(
                thread_id=thread_id,
                messages=messages,
                language=checkpoint.get("metadata", {}).get("language", "English")
            )
        except Exception as e:
            logger.error(f"Error retrieving chat history for thread {thread_id}: {str(e)}")
            raise