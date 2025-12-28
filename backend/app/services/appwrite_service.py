"""
Appwrite database service for chat operations using TablesDB
"""
from appwrite.client import Client
from appwrite.services.tables_db import TablesDB
from appwrite.id import ID
from appwrite.query import Query
from appwrite.exception import AppwriteException
from app.utils.config import (
    APPWRITE_ENDPOINT,
    APPWRITE_SECRET,
    APPWRITE_PROJECT_ID,
    APPWRITE_DATABASE,
    APPWRITE_DATABASE_CHATS_TABLE
)
from app.models.chat import ChatMessageCreate, ChatMessageResponse
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class AppwriteService:
    """Service for interacting with Appwrite TablesDB"""
    
    def __init__(self):
        """Initialize Appwrite client"""
        self.client = Client()
        self.client.set_endpoint(APPWRITE_ENDPOINT)
        self.client.set_project(APPWRITE_PROJECT_ID)
        self.client.set_key(APPWRITE_SECRET)
        
        self.tables_db = TablesDB(self.client)
        self.database_id = APPWRITE_DATABASE
        self.table_id = APPWRITE_DATABASE_CHATS_TABLE
    
    def create_chat_message(self, chat_message: ChatMessageCreate) -> ChatMessageResponse:
        """Create a new chat message in the database"""
        try:
            response = self.tables_db.create_row(
                database_id=self.database_id,
                table_id=self.table_id,
                row_id=ID.unique(),  # Let Appwrite generate unique ID
                data={
                    "user_phone": chat_message.user_phone,
                    "role": chat_message.role,
                    "message": chat_message.message
                }
            )
            
            return ChatMessageResponse(
                id=response["$id"],
                user_phone=response["user_phone"],
                role=response["role"],
                message=response["message"],
                created_at=response.get("$createdAt")
            )
        except AppwriteException as e:
            logger.error(f"Error creating chat message: {e.message}")
            raise
    
    def get_chat_history(self, user_phone: str, limit: int = 50) -> List[ChatMessageResponse]:
        """Get chat history for a specific user"""
        try:
            response = self.tables_db.list_rows(
                database_id=self.database_id,
                table_id=self.table_id,
                queries=[
                    Query.equal("user_phone", user_phone),
                    Query.order_desc("$createdAt"),
                    Query.limit(limit)
                ]
            )
            
            messages = []
            for row in response["rows"]:
                messages.append(ChatMessageResponse(
                    id=row["$id"],
                    user_phone=row["user_phone"],
                    role=row["role"],
                    message=row["message"],
                    created_at=row.get("$createdAt")
                ))
            
            # Reverse to get chronological order
            return list(reversed(messages))
        except AppwriteException as e:
            logger.error(f"Error getting chat history: {e.message}")
            raise
    
    def get_recent_chat_history(self, user_phone: str, limit: int = 10) -> List[ChatMessageResponse]:
        """Get recent chat history for context (ordered chronologically)"""
        return self.get_chat_history(user_phone, limit)

