"""
WhatsApp webhook routes for handling incoming messages
"""
from fastapi import APIRouter, Request, HTTPException, Query, Header, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from app.services.appwrite_service import AppwriteService
from app.services.ai_service import AIService
from app.services.guardrails_service import GuardrailsService
from app.services.whatsapp_service import WhatsAppService
from app.models.chat import ChatMessageCreate, ChatMessageResponse
from app.utils.config import WHATSAPP_SECRET_KEY, WHATSAPP_VERIFY_TOKEN, WHATSAPP_BOT_PHONE_NUMBER
from app.utils.constants import ROLE_BOT, ROLE_USER
from typing import Optional
import hmac
import hashlib
import json
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

def get_whatsapp_service() -> WhatsAppService:
    """Dependency to get WhatsApp service instance"""
    return WhatsAppService()

def verify_whatsapp_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify WhatsApp webhook signature using HMAC SHA256
    
    Args:
        payload: Raw request body
        signature: Signature from X-Hub-Signature-256 header
        secret: WhatsApp app secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature:
        return False
    
    # Remove 'sha256=' prefix if present
    signature = signature.replace('sha256=', '')
    
    # Calculate expected signature
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures securely
    return hmac.compare_digest(signature, expected_signature)

# Add this to app/routes/whatsapp.py

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify server is reachable"""
    logger.info("=== TEST ENDPOINT HIT ===")
    return {"status": "ok", "message": "Server is reachable", "endpoint": "/webhook"}

@router.get("/webhook")
async def verify_webhook(
    mode: Optional[str] = Query(None, alias="hub.mode"),
    token: Optional[str] = Query(None, alias="hub.verify_token"),
    challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """
    Webhook verification endpoint for WhatsApp Cloud API
    Meta will call this to verify your webhook URL during setup
    Note: Meta sends parameters with 'hub.' prefix (hub.mode, hub.verify_token, hub.challenge)
    """
    logger.info(f"Webhook verification request - mode: {mode}, token present: {token is not None}, challenge: {challenge}")
    
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        print(f"✓ Webhook verified! Returning challenge: {challenge}")
        return PlainTextResponse(challenge)
    else:
        logger.warning(f"Webhook verification failed: mode={mode}, token_match={token == WHATSAPP_VERIFY_TOKEN}")
        logger.warning(f"Expected token: {WHATSAPP_VERIFY_TOKEN[:20]}... (truncated)")
        logger.warning(f"Received token: {token[:20] if token else 'None'}... (truncated)")
        print(f"✗ Webhook verification failed - mode={mode}, token_match={token == WHATSAPP_VERIFY_TOKEN}")
        raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    appwrite_service: AppwriteService = Depends(get_appwrite_service),
    ai_service: AIService = Depends(get_ai_service),
    guardrails: GuardrailsService = Depends(get_guardrails_service),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service)
):
    """
    Handle incoming WhatsApp messages from Meta Cloud API
    """
    # Print statement to ensure we see if webhook is received (even if logging fails)
    print("=" * 50)
    print("WEBHOOK RECEIVED!")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Path: {request.url.path}")
    print("=" * 50)
    
    logger.info("=== WhatsApp webhook received ===")
    
    # Get raw body for signature verification
    body = await request.body()
    logger.info(f"Request body length: {len(body)} bytes")
    logger.info(f"Signature header present: {x_hub_signature_256 is not None}")
    logger.info(f"WhatsApp service configured: {whatsapp_service.is_configured()}")
    
    # Verify webhook signature if secret is configured
    if WHATSAPP_SECRET_KEY and x_hub_signature_256:
        if not verify_whatsapp_signature(body, x_hub_signature_256, WHATSAPP_SECRET_KEY):
            logger.warning("Invalid WhatsApp webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
        else:
            logger.info("Webhook signature verified successfully")
    else:
        logger.info("Skipping signature verification (secret or signature not provided)")
    
    # Parse JSON payload
    try:
        data = json.loads(body)
        logger.info(f"Parsed webhook data - object: {data.get('object')}")
        print(f"Webhook object type: {data.get('object')}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Handle WhatsApp Cloud API webhook structure
    if data.get("object") == "whatsapp_business_account":
        logger.info("Processing whatsapp_business_account webhook")
        entries = data.get("entry", [])
        logger.info(f"Found {len(entries)} entry/entries")
        
        for entry in entries:
            changes = entry.get("changes", [])
            logger.info(f"Processing {len(changes)} change(s) in entry")
            
            for change in changes:
                field = change.get("field")
                logger.info(f"Processing change with field: {field}")
                print(f"Processing webhook field: {field}")
                value = change.get("value", {})
                
                # Handle messages field
                if field == "messages":
                    # Handle incoming messages
                    if "messages" in value:
                        messages = value["messages"]
                        logger.info(f"Found {len(messages)} message(s) in webhook")
                        print(f"Found {len(messages)} message(s) in webhook")
                        
                        for message in messages:
                            user_phone = None
                            try:
                                # Extract user phone number (who sent the message)
                                user_phone = message.get("from", "")
                                logger.info(f"Processing message from: {user_phone}")
                                print(f"Processing message from: {user_phone}")
                                
                                if not user_phone:
                                    logger.warning("No user phone number in message")
                                    continue
                                
                                # Extract message text
                                message_type = message.get("type")
                                logger.info(f"Message type: {message_type}")
                                message_text = ""
                                
                                if message_type == "text":
                                    message_text = message.get("text", {}).get("body", "")
                                elif message_type == "image":
                                    # Handle image messages
                                    caption = message.get("image", {}).get("caption", "")
                                    message_text = f"[Image] {caption}" if caption else "[Image message]"
                                elif message_type == "audio":
                                    message_text = "[Audio message]"
                                elif message_type == "video":
                                    caption = message.get("video", {}).get("caption", "")
                                    message_text = f"[Video] {caption}" if caption else "[Video message]"
                                elif message_type == "document":
                                    filename = message.get("document", {}).get("filename", "")
                                    message_text = f"[Document] {filename}" if filename else "[Document]"
                                else:
                                    message_text = f"[{message_type} message]"
                                
                                logger.info(f"Extracted message text: {message_text[:100]}")
                                print(f"Message text: {message_text[:100]}")
                                
                                if not message_text:
                                    logger.warning(f"Empty message text for type {message_type}")
                                    continue
                                
                                # Process the message
                                logger.info(f"Calling process_whatsapp_message for user {user_phone}")
                                bot_response = await process_whatsapp_message(
                                    user_phone=user_phone,
                                    message_text=message_text,
                                    appwrite_service=appwrite_service,
                                    ai_service=ai_service,
                                    guardrails=guardrails
                                )
                                
                                logger.info(f"Bot response generated: {bot_response[:100] if bot_response else 'None'}")
                                print(f"Bot response: {bot_response[:50] if bot_response else 'None'}...")
                                
                                # Send response back via WhatsApp
                                if bot_response:
                                    if whatsapp_service.is_configured():
                                        logger.info(f"Attempting to send message to {user_phone}")
                                        print(f"Sending message to {user_phone}")
                                        success = whatsapp_service.send_message(
                                            to_phone=user_phone,
                                            message_text=bot_response
                                        )
                                        logger.info(f"Message send result: {success}")
                                        print(f"Message send result: {success}")
                                        if not success:
                                            logger.error(f"Failed to send message to {user_phone}")
                                    else:
                                        logger.warning(f"Cannot send message - WhatsApp service not configured")
                                        print("ERROR: WhatsApp service not configured!")
                                else:
                                    logger.warning(f"No bot response generated for user {user_phone}")
                                
                            except Exception as e:
                                logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
                                print(f"ERROR processing message: {e}")
                                # Try to send error message to user
                                if whatsapp_service.is_configured() and user_phone:
                                    try:
                                        logger.info(f"Sending error message to {user_phone}")
                                        whatsapp_service.send_message(
                                            to_phone=user_phone,
                                            message_text="Sorry, I encountered an error. Please try again."
                                        )
                                    except Exception as send_error:
                                        logger.error(f"Error sending error message: {send_error}")
                    else:
                        logger.info("Messages field present but no messages array in value")
                        print("Messages field present but no messages array")
                
                # Handle status updates
                elif field == "status":
                    logger.info("Received status update webhook")
                    print("Received status update webhook")
                    statuses = value.get("statuses", [])
                    logger.info(f"Found {len(statuses)} status update(s)")
                    for status in statuses:
                        status_id = status.get("id", "unknown")
                        status_type = status.get("status", "unknown")
                        recipient = status.get("recipient_id", "unknown")
                        logger.info(f"Status update: id={status_id}, status={status_type}, recipient={recipient}")
                        print(f"Status: {status_type} for message {status_id} to {recipient}")
                
                # Handle other field types
                else:
                    logger.info(f"Received webhook with field: {field} (acknowledging but not processing)")
                    print(f"Received webhook with field: {field}")
    else:
        logger.warning(f"Received webhook with unexpected object type: {data.get('object')}")
        print(f"Unexpected webhook object type: {data.get('object')}")
    
    logger.info("=== WhatsApp webhook processing complete ===")
    print("=== Webhook processing complete ===")
    return JSONResponse({"status": "ok"})

async def process_whatsapp_message(
    user_phone: str,
    message_text: str,
    appwrite_service: AppwriteService,
    ai_service: AIService,
    guardrails: GuardrailsService
) -> Optional[str]:
    """
    Process incoming WhatsApp message and generate bot response
    
    Args:
        user_phone: User's phone number
        message_text: User's message text
        appwrite_service: Appwrite service instance
        ai_service: AI service instance
        guardrails: Guardrails service instance
        
    Returns:
        Bot response text, or None if processing failed
    """
    try:
        logger.info(f"Processing message for user {user_phone}: {message_text[:50]}...")
        
        # Validate and sanitize user input
        logger.info("Validating user input with guardrails...")
        is_valid, error_message = guardrails.validate_user_input(message_text)
        if not is_valid:
            logger.warning(f"Message blocked by guardrails from {user_phone}: {message_text[:100]}")
            return error_message or "I can't process that request. Please try again."
        
        logger.info("User input validation passed")
        
        # Get chat history
        logger.info(f"Fetching chat history for user {user_phone}...")
        chat_history = appwrite_service.get_recent_chat_history(
            user_phone=user_phone,
            limit=10
        )
        logger.info(f"Retrieved {len(chat_history)} previous messages")
        
        # Sanitize the message
        sanitized_message = guardrails.sanitize_input(message_text)
        
        # Save user message to database
        logger.info("Saving user message to database...")
        user_message = ChatMessageCreate(
            user_phone=user_phone,
            role=ROLE_USER,
            message=sanitized_message
        )
        appwrite_service.create_chat_message(user_message)
        logger.info("User message saved successfully")
        
        # Generate AI response
        logger.info("Generating AI response...")
        bot_response_text = ai_service.generate_response(
            user_message=sanitized_message,
            chat_history=chat_history
        )
        logger.info(f"AI response generated: {bot_response_text[:100]}...")
        
        # Validate AI response
        logger.info("Validating AI response with guardrails...")
        is_valid_response, response_error = guardrails.validate_ai_response(
            bot_response_text,
            ai_service.system_prompt
        )
        
        if not is_valid_response:
            logger.warning(f"AI response blocked by guardrails: {response_error}")
            bot_response_text = "I apologize, but I can't provide that response. How else can I help you?"
        else:
            logger.info("AI response validation passed")
        
        # Save bot message to database
        logger.info("Saving bot message to database...")
        bot_message = ChatMessageCreate(
            user_phone=user_phone,
            role=ROLE_BOT,
            message=bot_response_text
        )
        appwrite_service.create_chat_message(bot_message)
        logger.info("Bot message saved successfully")
        
        return bot_response_text
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
        return None

@router.post("/test/send")
async def test_send_message(
    phone: str = Query(...),
    message: str = Query(default="Test message"),
    whatsapp_service: WhatsAppService = Depends(get_whatsapp_service)
):
    """
    Test endpoint to send a WhatsApp message
    Usage: POST /test/send?phone=918074919312&message=Hello
    """
    logger.info(f"=== Testing WhatsApp send to {phone} ===")
    
    if not whatsapp_service.is_configured():
        logger.error("WhatsApp service not configured")
        return {
            "error": "WhatsApp service not configured",
            "configured": False,
            "phone": phone,
            "message": message
        }
    
    logger.info(f"Sending test message: {message}")
    success = whatsapp_service.send_message(to_phone=phone, message_text=message)
    
    logger.info(f"Test send result: {success}")
    return {
        "success": success,
        "phone": phone,
        "message": message,
        "configured": True
    }

