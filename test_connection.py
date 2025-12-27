"""Test database connection with detailed error output."""
from config.settings import settings
from app.db.connection import db
import traceback

try:
    print("Testing Secret Manager...")
    print(f"DB User from Secret Manager: '{settings.db_user}'")
    print(f"DB Password from Secret Manager: '{settings.db_password}'")
    print()
    print("Testing connection to Cloud SQL...")
    print(f"Connection string: {db.connection_string}")
    result = db.test_connection()
    if result:
        print("✓ Database connection successful!")
    else:
        print("✗ Connection failed - no specific error")
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
