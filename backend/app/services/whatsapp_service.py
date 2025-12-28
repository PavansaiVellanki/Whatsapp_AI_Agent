"""
WhatsApp Cloud API service for sending messages
"""
import requests
import logging
import json
from typing import Optional
from app.utils.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_BUSINESS_PHONE_ID,
    WHATSAPP_API_BASE_URL
)

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Service for sending messages via WhatsApp Cloud API"""
    
    def __init__(self):
        """Initialize WhatsApp service"""
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.phone_id = WHATSAPP_BUSINESS_PHONE_ID
        self.api_base_url = WHATSAPP_API_BASE_URL
        
        if not self.access_token or not self.phone_id:
            logger.warning("WhatsApp credentials not configured. WhatsApp messaging will be disabled.")
    
    def send_message(self, to_phone: str, message_text: str) -> bool:
        """
        Send a text message via WhatsApp Cloud API
        
        Args:
            to_phone: Recipient phone number (with country code, no + or spaces)
            message_text: Message content to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        logger.info(f"=== Attempting to send WhatsApp message ===")
        logger.info(f"To: {to_phone}, Message length: {len(message_text)}")
        
        if not self.access_token or not self.phone_id:
            logger.error("WhatsApp credentials not configured. Cannot send message.")
            logger.error(f"Access token present: {bool(self.access_token)}")
            logger.error(f"Phone ID present: {bool(self.phone_id)}")
            return False
        
        # Clean phone number (remove +, spaces, and @c.us suffix if present)
        original_phone = to_phone
        to_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
        if "@" in to_phone:
            to_phone = to_phone.split("@")[0]
        
        if original_phone != to_phone:
            logger.info(f"Cleaned phone number: {original_phone} -> {to_phone}")
        
        url = f"{self.api_base_url}/{self.phone_id}/messages"
        logger.info(f"Sending to URL: {url}")
        logger.info(f"Using phone ID: {self.phone_id}")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        logger.info(f"Request headers prepared (Authorization token length: {len(self.access_token)})")
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {
                "body": message_text
            }
        }
        logger.info(f"Payload prepared: to={to_phone}, type=text, body_length={len(message_text)}")
        
        try:
            logger.info("Sending POST request to WhatsApp API...")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Response JSON: {json.dumps(result, indent=2)}")
            
            if "messages" in result:
                message_id = result.get("messages", [{}])[0].get("id", "unknown")
                logger.info(f"Message sent successfully to {to_phone}, message ID: {message_id}")
                return True
            else:
                logger.error(f"Unexpected response from WhatsApp API: {result}")
                return False
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error sending WhatsApp message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
                try:
                    error_json = e.response.json()
                    logger.error(f"Response JSON: {json.dumps(error_json, indent=2)}")
                except:
                    pass
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error sending WhatsApp message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}", exc_info=True)
            return False
    
    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured"""
        return bool(self.access_token and self.phone_id)

