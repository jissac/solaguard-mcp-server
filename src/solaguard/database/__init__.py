"""
SolaGuard Database Operations

This package handles all database operations including connection management,
schema creation, and data access for biblical texts and metadata.
"""

from .connection import (
    DatabaseManager,
    get_database_manager,
    initialize_database,
    close_database,
    execute_query,
    execute_search_query,
)
from .schema import (
    create_schema,
    validate_schema,
    get_database_info,
    INITIAL_TRANSLATIONS,
    INITIAL_BOOKS,
)

__all__ = [
    # Connection management
    "DatabaseManager",
    "get_database_manager", 
    "initialize_database",
    "close_database",
    "execute_query",
    "execute_search_query",
    # Schema management
    "create_schema",
    "validate_schema", 
    "get_database_info",
    "INITIAL_TRANSLATIONS",
    "INITIAL_BOOKS",
]