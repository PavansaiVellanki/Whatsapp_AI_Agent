"""
Script to initialize Appwrite database and create chats table using TablesDB
Run this script once to set up the database schema
"""
from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.exception import AppwriteException
from app.utils.config import (
    APPWRITE_ENDPOINT,
    APPWRITE_SECRET,
    APPWRITE_PROJECT_ID,
    APPWRITE_DATABASE,
    APPWRITE_DATABASE_CHATS_TABLE,
    validate_config
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chats_table():
    """Create the chats table with required columns"""
    try:
        # Validate configuration
        validate_config()
        
        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(APPWRITE_ENDPOINT)
        client.set_project(APPWRITE_PROJECT_ID)
        client.set_key(APPWRITE_SECRET)
        
        databases = Databases(client)
        
        # Check if table already exists
        try:
            table = databases.get_table(
                database_id=APPWRITE_DATABASE,
                table_id=APPWRITE_DATABASE_CHATS_TABLE
            )
            logger.info(f"Table '{APPWRITE_DATABASE_CHATS_TABLE}' already exists")
            return
        except AppwriteException as e:
            if e.code != 404:
                raise
        
        # Create table (using create_table if available, otherwise create_collection for backward compatibility)
        logger.info(f"Creating table '{APPWRITE_DATABASE_CHATS_TABLE}'...")
        try:
            # Try new API first
            table = databases.create_table(
                database_id=APPWRITE_DATABASE,
                table_id=APPWRITE_DATABASE_CHATS_TABLE,
                name="Chats",
                permissions=[
                    "read(\"any\")",
                    "create(\"any\")",
                    "update(\"any\")",
                    "delete(\"any\")"
                ]
            )
        except (AppwriteException, AttributeError):
            # Fallback to collection API if table API not available
            table = databases.create_collection(
                database_id=APPWRITE_DATABASE,
                collection_id=APPWRITE_DATABASE_CHATS_TABLE,
                name="Chats",
                permissions=[
                    "read(\"any\")",
                    "create(\"any\")",
                    "update(\"any\")",
                    "delete(\"any\")"
                ]
            )
        logger.info(f"Table created with ID: {table['$id']}")
        
        # Create columns (using create_column if available, otherwise create_string_attribute/create_enum_attribute)
        # 1. user_phone (string, size 20)
        logger.info("Creating 'user_phone' column...")
        try:
            databases.create_column(
                database_id=APPWRITE_DATABASE,
                table_id=APPWRITE_DATABASE_CHATS_TABLE,
                column_id="user_phone",
                type="string",
                size=20,
                required=True
            )
        except (AppwriteException, AttributeError):
            databases.create_string_attribute(
                database_id=APPWRITE_DATABASE,
                collection_id=APPWRITE_DATABASE_CHATS_TABLE,
                key="user_phone",
                size=20,
                required=True
            )
        
        # 2. role (enum: [bot, user])
        logger.info("Creating 'role' column...")
        try:
            databases.create_column(
                database_id=APPWRITE_DATABASE,
                table_id=APPWRITE_DATABASE_CHATS_TABLE,
                column_id="role",
                type="enum",
                elements=["bot", "user"],
                required=True,
                default="user"
            )
        except (AppwriteException, AttributeError):
            databases.create_enum_attribute(
                database_id=APPWRITE_DATABASE,
                collection_id=APPWRITE_DATABASE_CHATS_TABLE,
                key="role",
                elements=["bot", "user"],
                required=True,
                default="user"
            )
        
        # 3. message (string, max limit of table db)
        logger.info("Creating 'message' column...")
        try:
            databases.create_column(
                database_id=APPWRITE_DATABASE,
                table_id=APPWRITE_DATABASE_CHATS_TABLE,
                column_id="message",
                type="string",
                size=1000000,  # 1MB max size
                required=True
            )
        except (AppwriteException, AttributeError):
            databases.create_string_attribute(
                database_id=APPWRITE_DATABASE,
                collection_id=APPWRITE_DATABASE_CHATS_TABLE,
                key="message",
                size=1000000,  # 1MB max size
                required=True
            )
        
        logger.info("Database initialization completed successfully!")
        logger.info("Note: Columns may take a few moments to be fully created. Wait before using the table.")
        
    except AppwriteException as e:
        logger.error(f"Appwrite error: {e.message} (Code: {e.code})")
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    create_chats_table()

