"""
Configuration management for environment variables
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Appwrite Configuration
APPWRITE_ENDPOINT = os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")
APPWRITE_SECRET = os.getenv("APPWRITE_SECRET")
APPWRITE_PROJECT_ID = os.getenv("APPWRITE_PROJECT_ID")
APPWRITE_DATABASE = os.getenv("APPWRITE_DATABASE")
APPWRITE_DATABASE_CHATS_TABLE = os.getenv("APPWRITE_DATABASE_CHATS_TABLE")

# Google AI Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# WhatsApp Cloud API Configuration
WHATSAPP_PROJECT_ID = os.getenv("WHATSAPP_PROJECT_ID")
WHATSAPP_SECRET_KEY = os.getenv("WHATSAPP_SECRET_KEY")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
WHATSAPP_BUSINESS_PHONE_ID = os.getenv("WHATSAPP_BUSINESS_PHONE_ID")
WHATSAPP_BOT_PHONE_NUMBER = os.getenv("WHATSAPP_BOT_PHONE_NUMBER")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "default_verify_token_change_me")

# WhatsApp API Base URL
WHATSAPP_API_BASE_URL = "https://graph.facebook.com/v22.0"

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "500"))

# Qdrant Vector Database Configuration
QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT")
QDRANT_KEY = os.getenv("QDRANT_KEY")  # Optional, for cloud Qdrant
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "whatsapp_documents")

# Document Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Validate required environment variables
def validate_config():
    """Validate that all required environment variables are set"""
    required_vars = {
        "APPWRITE_SECRET": APPWRITE_SECRET,
        "APPWRITE_PROJECT_ID": APPWRITE_PROJECT_ID,
        "APPWRITE_DATABASE": APPWRITE_DATABASE,
        "APPWRITE_DATABASE_CHATS_TABLE": APPWRITE_DATABASE_CHATS_TABLE,
        "GOOGLE_API_KEY": GOOGLE_API_KEY,
    }
    
    # WhatsApp variables are optional (for testing without WhatsApp)
    optional_whatsapp_vars = {
        "WHATSAPP_ACCESS_TOKEN": WHATSAPP_ACCESS_TOKEN,
        "WHATSAPP_BUSINESS_PHONE_ID": WHATSAPP_BUSINESS_PHONE_ID,
        "WHATSAPP_BOT_PHONE_NUMBER": WHATSAPP_BOT_PHONE_NUMBER,
    }
    
    missing_vars = [key for key, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Warn if WhatsApp vars are missing but don't fail
    missing_whatsapp = [key for key, value in optional_whatsapp_vars.items() if not value]
    if missing_whatsapp:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Optional WhatsApp variables not set: {', '.join(missing_whatsapp)}. WhatsApp features will be disabled.")
    
    return True

