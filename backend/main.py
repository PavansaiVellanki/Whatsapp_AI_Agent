"""
Main entry point for the FastAPI application
"""
import uvicorn
from app import app
from app.utils.config import validate_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Validate configuration on startup
        validate_config()
        logger.info("Configuration validated successfully")
        
        # Run the application
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set all required environment variables in your .env file")
    except Exception as e:
        logger.error(f"Error starting application: {e}")

