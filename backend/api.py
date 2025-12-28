"""
Legacy API file - kept for backward compatibility
The main application is now in main.py and uses the app/ directory structure
"""
from app import app

# This file can be used to run the app if needed
# But it's recommended to use main.py instead
__all__ = ["app"]