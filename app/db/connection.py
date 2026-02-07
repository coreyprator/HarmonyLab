"""
Database connection for Cloud SQL.
Uses Secret Manager credentials.
"""
import logging
import pyodbc
from config.settings import settings

logger = logging.getLogger(__name__)


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
            f"Connection Timeout=30;"
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


class DatabaseConnection:
    """Database connection wrapper with query execution methods."""

    def __init__(self, settings_obj=None):
        self._settings = settings_obj or settings

    def _get_conn(self):
        return db.get_connection()

    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute query and return list of dicts."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()

    def execute_scalar(self, query: str, params: tuple = None):
        """Execute query and return first column of first row."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def execute_non_query(self, query: str, params: tuple = None) -> int:
        """Execute non-query (INSERT/UPDATE/DELETE) and return rows affected."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            affected = cursor.rowcount
            conn.commit()
            return affected
        finally:
            conn.close()

    def execute_with_commit(self, query: str, params: tuple = None) -> list:
        """Execute query, commit, and return results."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            conn.commit()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()


def get_db():
    """FastAPI dependency for database connection."""
    return DatabaseConnection()

