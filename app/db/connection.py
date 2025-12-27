"""
Database connection management for MS SQL Server.
"""
import pyodbc
from typing import Optional
from contextlib import contextmanager
from config.settings import settings


class DatabaseConnection:
    """Manages database connections using pyodbc."""
    
    def __init__(self):
        self.connection_string = settings.database_url
        self._connection: Optional[pyodbc.Connection] = None
    
    def connect(self) -> pyodbc.Connection:
        """Establish database connection."""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = pyodbc.connect(self.connection_string)
                self._connection.autocommit = False
            except pyodbc.Error as e:
                raise ConnectionError(f"Failed to connect to database: {str(e)}")
        return self._connection
    
    def close(self):
        """Close database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor operations."""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = ()):
        """Execute a SELECT query and return results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
    
    def execute_non_query(self, query: str, params: tuple = ()):
        """Execute INSERT, UPDATE, or DELETE query."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_scalar(self, query: str, params: tuple = ()):
        """Execute query and return single value."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else None
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False


# Global database instance
db = DatabaseConnection()


def get_db() -> DatabaseConnection:
    """Dependency injection for FastAPI routes."""
    return db
