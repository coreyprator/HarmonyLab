"""
Database connection for Cloud SQL.
Uses Secret Manager credentials.
"""
import pyodbc
from config.settings import settings


class Database:
    """Database connection manager for Cloud SQL."""
    
    def __init__(self):
        self._connection = None
    
    @property
    def connection_string(self) -> str:
        """Build pyodbc connection string for Cloud SQL."""
        return (
            f"DRIVER={{{settings.db_driver}}};"
            f"SERVER={settings.db_server};"
            f"DATABASE={settings.db_name};"
            f"UID={settings.db_user};"
            f"PWD={settings.db_password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )
    
    def get_connection(self):
        """Get a new database connection."""
        try:
            return pyodbc.connect(self.connection_string)
        except pyodbc.Error as e:
            print(f"Database connection failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


# Singleton instance
db = Database()


def get_db_connection():
    """Convenience function for getting a connection."""
    return db.get_connection()

