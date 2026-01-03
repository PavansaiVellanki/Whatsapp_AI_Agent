"""
Chat API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from app.models.chat import ChatMessageCreate, ChatMessageResponse, ChatRequest
from app.services.appwrite_service import AppwriteService
from app.services.ai_service import AIService
from app.services.guardrails_service import GuardrailsService
from app.utils.constants import BOT_PHONE_NUMBER, USER_PHONE_NUMBER, ROLE_BOT, ROLE_USER
from app.middleware.rate_limit import rate_limit_dependency
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_appwrite_service() -> AppwriteService:
    """Dependency to get Appwrite service instance"""
    return AppwriteService()

def get_ai_service() -> AIService:
    """Dependency to get AI service instance"""
    return AIService()

def get_guardrails_service() -> GuardrailsService:
    """Dependency to get Guardrails service instance"""
    return GuardrailsService()

async def check_rate_limit_for_chat(
    http_request: Request,
    user_phone: str = None
):
    """Rate limit dependency for chat endpoint"""
    phone_number = user_phone or USER_PHONE_NUMBER
    await rate_limit_dependency(http_request, phone_number)

@router.post("/chat", response_model=ChatMessageResponse)
async def send_message(
    request: ChatRequest,
    http_request: Request,
    user_phone: str = None,  # Optional: can be passed for testing
    appwrite_service: AppwriteService = Depends(get_appwrite_service),
    ai_service: AIService = Depends(get_ai_service),
    guardrails: GuardrailsService = Depends(get_guardrails_service),
    _: None = Depends(check_rate_limit_for_chat)
):
    """
    Send a message and get AI response
    
    Args:
        request: Chat request containing the user's message
        user_phone: Optional user phone number (defaults to USER_PHONE_NUMBER for testing)
        
    Returns:
        Bot's response message
    """
    # Use provided user_phone or fallback to constant for testing
    phone_number = user_phone or USER_PHONE_NUMBER
    
    try:
        # Validate and sanitize user input before processing
        is_valid, error_message = guardrails.validate_user_input(request.message)
        if not is_valid:
            logger.warning(f"Message blocked by guardrails: {request.message[:100]}")
            # Return a safe response without saving the problematic message
            safe_response = error_message or "I can't process that request. Please try again."
            
            # Create bot message with safe response
            bot_message = ChatMessageCreate(
                user_phone=phone_number,
                role=ROLE_BOT,
                message=safe_response
            )
            
            # Save only the safe bot response (not the problematic user message)
            saved_bot_message = appwrite_service.create_chat_message(bot_message)
            return saved_bot_message
        
        # Get chat history BEFORE saving the new message (to avoid duplication)
        chat_history = appwrite_service.get_recent_chat_history(
            user_phone=phone_number,
            limit=10
        )
        
        # Sanitize the message before saving
        sanitized_message = guardrails.sanitize_input(request.message)
        
        # Create user message
        user_message = ChatMessageCreate(
            user_phone=phone_number,
            role=ROLE_USER,
            message=sanitized_message
        )
        
        # Save user message to database
        saved_user_message = appwrite_service.create_chat_message(user_message)
        
        # Generate AI response (chat_history doesn't include current message yet)
        bot_response_text = ai_service.generate_response(
            user_message=sanitized_message,
            chat_history=chat_history
        )
        
        # Validate AI response before saving
        is_valid_response, response_error = guardrails.validate_ai_response(
            bot_response_text,
            ai_service.system_prompt
        )
        
        if not is_valid_response:
            logger.warning(f"AI response blocked by guardrails: {response_error}")
            bot_response_text = "I apologize, but I can't provide that response. How else can I help you?"
        
        # Create bot message
        bot_message = ChatMessageCreate(
            user_phone=phone_number,
            role=ROLE_BOT,
            message=bot_response_text
        )
        
        # Save bot message to database
        saved_bot_message = appwrite_service.create_chat_message(bot_message)
        
        return saved_bot_message
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    limit: int = 50,
    user_phone: str = None,  # Optional: can be passed for testing
    appwrite_service: AppwriteService = Depends(get_appwrite_service)
):
    """
    Get chat history for the user
    
    Args:
        limit: Maximum number of messages to return (max 100)
        user_phone: Optional user phone number (defaults to USER_PHONE_NUMBER for testing)
        
    Returns:
        List of chat messages
    """
    # Enforce max limit to prevent abuse
    limit = min(limit, 100)
    
    # Use provided user_phone or fallback to constant for testing
    phone_number = user_phone or USER_PHONE_NUMBER
    
    try:
        history = appwrite_service.get_chat_history(
            user_phone=phone_number,
            limit=limit
        )
        return history
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/message", response_model=ChatMessageResponse)
async def create_message(
    chat_message: ChatMessageCreate,
    appwrite_service: AppwriteService = Depends(get_appwrite_service)
):
    """
    Create a chat message (for testing or direct message creation)
    
    Args:
        chat_message: The chat message to create
        
    Returns:
        Created chat message
    """
    try:
        return appwrite_service.create_chat_message(chat_message)
    except Exception as e:
        logger.error(f"Error creating chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

