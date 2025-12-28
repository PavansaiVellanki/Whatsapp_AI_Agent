"""
Standalone script to initialize the Appwrite database
Run this script once before starting the application:
    python init_database.py
"""
from app.database.init_db import create_chats_table

if __name__ == "__main__":
    print("Initializing Appwrite database...")
    print("=" * 50)
    create_chats_table()
    print("=" * 50)
    print("Database initialization complete!")
    print("\nYou can now start the application with: python main.py")

