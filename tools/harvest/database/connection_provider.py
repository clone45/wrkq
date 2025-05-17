# File: harvest/database/connection_provider.py

import logging
from pathlib import Path
from typing import Optional
from .connection import SQLiteDBConnection

logger = logging.getLogger(__name__)

class DBConnectionProvider:
    """
    Singleton provider for database connections to ensure consistency
    across all components that need database access.
    """
    _instance = None
    _connection: Optional[SQLiteDBConnection] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBConnectionProvider, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, db_path: Path) -> None:
        """Initialize the database connection."""
        if self._connection is not None:
            logger.warning(f"Database connection already initialized. Reinitializing with: {db_path}")
            self._connection.close()
        
        logger.info(f"Initializing database connection with: {db_path}")
        self._connection = SQLiteDBConnection(db_path)
        
    def get_connection(self) -> Optional[SQLiteDBConnection]:
        """Get the shared database connection."""
        if self._connection is None:
            logger.error("Database connection requested but not initialized!")
            return None
        return self._connection
    
    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")