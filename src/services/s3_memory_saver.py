import json
import logging
import aioboto3
from datetime import datetime
from typing import Any, Dict, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from botocore.exceptions import ClientError
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

class MessageEncoder(json.JSONEncoder):
    """Custom JSON encoder for LangChain message objects."""
    def default(self, obj):
        if isinstance(obj, BaseMessage):
            return {
                '_type': obj.__class__.__name__,
                'content': obj.content,
                'additional_kwargs': obj.additional_kwargs,
                'type': obj.type
            }
        return super().default(obj)

class S3MemorySaver(MemorySaver):
    """A memory saver that uses S3 as the backend storage."""

    def __init__(self, bucket_name: str, aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None, region_name: Optional[str] = None):
        """Initialize the S3 memory saver.

        Args:
            bucket_name: Name of the S3 bucket to use for storage
            aws_access_key_id: AWS access key ID (optional if using IAM roles)
            aws_secret_access_key: AWS secret access key (optional if using IAM roles)
            region_name: AWS region name (optional, defaults to boto3's default region)
        """
        super().__init__()
        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.session = aioboto3.Session()

    def _deserialize_messages(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize message objects from JSON data."""
        if isinstance(data, dict):
            if '_type' in data:
                msg_type = data['_type']
                if msg_type == 'HumanMessage':
                    return HumanMessage(content=data['content'], additional_kwargs=data['additional_kwargs'])
                elif msg_type == 'AIMessage':
                    return AIMessage(content=data['content'], additional_kwargs=data['additional_kwargs'])
            return {k: self._deserialize_messages(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._deserialize_messages(item) for item in data]
        return data

    def _get_s3_key(self, session_id: str) -> str:
        """Generate the S3 key for a given session ID."""
        return f"chat_histories/{session_id}.json"

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chat history from S3 by session ID."""
        try:
            async with self.session.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            ) as s3_client:
                s3_key = self._get_s3_key(session_id)
                response = await s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                async with response['Body'] as stream:
                    content = await stream.read()
                    data = json.loads(content.decode('utf-8'))
                    if 'state' in data:
                        return self._deserialize_messages(data['state'])
                    return self._deserialize_messages(data)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"No chat history found for session {session_id}")
                return None
            else:
                logger.error(f"Error retrieving chat history from S3: {str(e)}")
                raise

    async def put(self, session_id: str, data: Any, metadata: Optional[Dict] = None, new_versions: Optional[Dict] = None) -> None:
        """Save chat history to S3.

        Args:
            session_id: The unique session identifier
            data: The data to save
            metadata: Optional metadata to save with the state
            new_versions: Optional version information
        """
        try:
            async with self.session.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            ) as s3_client:
                s3_key = self._get_s3_key(session_id)
                save_data = {
                    'state': data,
                    'metadata': metadata or {},
                    'new_versions': new_versions or {},
                    'last_updated': datetime.now().isoformat()
                }
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=json.dumps(save_data, cls=MessageEncoder),
                    ContentType='application/json'
                )
                logger.info(f"Successfully saved chat history to S3 for session {session_id}")
        except Exception as e:
            logger.error(f"Error saving chat history to S3: {str(e)}")
            raise

    async def cleanup_old_sessions(self, max_age_days: int = 30) -> None:
        """Clean up old chat histories from S3.

        Args:
            max_age_days: Maximum age of chat histories to keep (in days)
        """
        try:
            async with self.session.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            ) as s3_client:
                paginator = s3_client.get_paginator('list_objects_v2')
                current_time = datetime.now()
                
                async for page in paginator.paginate(Bucket=self.bucket_name, Prefix='chat_histories/'):
                    if 'Contents' not in page:
                        continue
                        
                    for obj in page['Contents']:
                        # Skip if not a chat history file
                        if not obj['Key'].endswith('.json'):
                            continue
                            
                        # Check if file is older than max_age_days
                        age = (current_time - obj['LastModified'].replace(tzinfo=None)).days
                        if age > max_age_days:
                            await s3_client.delete_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            logger.info(f"Deleted old chat history: {obj['Key']}")
                            
                logger.info("Completed cleanup of old chat histories")
        except Exception as e:
            logger.error(f"Error during cleanup of old chat histories: {str(e)}")
            raise