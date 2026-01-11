"""
SolaGuard Database Connection Management

Handles database connections, connection pooling, and ensures read-only access
during runtime as per requirements.
"""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections with connection pooling and read-only enforcement.
    """
    
    def __init__(self, db_path: Path, max_connections: int = 10):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            max_connections: Maximum number of concurrent connections
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self._connection_semaphore = asyncio.Semaphore(max_connections)
        self._is_initialized = False
        
    async def initialize(self) -> None:
        """Initialize database manager and validate schema."""
        if self._is_initialized:
            return
            
        logger.info(f"Initializing database manager for {self.db_path}")
        
        # Validate database exists and has correct schema
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        # Test connection and validate schema
        async with self.get_connection() as conn:
            # Verify critical tables exist
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('verses', 'books', 'translations')"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            if len(tables) < 3:
                raise RuntimeError(f"Database schema incomplete. Found tables: {tables}")
        
        self._is_initialized = True
        logger.info("Database manager initialized successfully")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Get a database connection with automatic cleanup.
        
        Yields:
            aiosqlite.Connection: Database connection (read-only)
        """
        async with self._connection_semaphore:
            try:
                # Open connection in read-only mode
                conn = await aiosqlite.connect(
                    self.db_path,
                    timeout=30.0,
                    check_same_thread=False,
                )
                
                # Configure connection for read-only access
                await conn.execute("PRAGMA query_only = ON")
                await conn.execute("PRAGMA foreign_keys = ON")
                
                # Set row factory for easier data access
                conn.row_factory = aiosqlite.Row
                
                yield conn
                
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise
            finally:
                if 'conn' in locals():
                    await conn.close()
    
    async def health_check(self) -> dict:
        """
        Perform database health check.
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            async with self.get_connection() as conn:
                # Test basic query
                cursor = await conn.execute("SELECT COUNT(*) FROM verses")
                verse_count = (await cursor.fetchone())[0]
                
                # Test FTS5 search - check if table exists first
                try:
                    cursor = await conn.execute("SELECT COUNT(*) FROM verses_fts")
                    fts_count = (await cursor.fetchone())[0]
                except Exception:
                    # FTS5 table might not exist or be empty
                    fts_count = 0
                
                # Get database file size
                db_size = self.db_path.stat().st_size
                
                return {
                    "status": "healthy",
                    "verse_count": verse_count,
                    "fts_index_count": fts_count,
                    "database_size_mb": round(db_size / (1024 * 1024), 2),
                    "max_connections": self.max_connections,
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "verse_count": 0,
                "fts_index_count": 0,
                "database_size_mb": 0,
                "max_connections": self.max_connections,
            }
    
    async def get_database_stats(self) -> dict:
        """
        Get comprehensive database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            async with self.get_connection() as conn:
                stats = {}
                
                # Table counts
                tables = ["translations", "books", "verses", "words", "strongs_dictionary", "cross_references"]
                for table in tables:
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = (await cursor.fetchone())[0]
                
                # Available translations
                cursor = await conn.execute("SELECT id, name FROM translations ORDER BY id")
                stats["available_translations"] = dict(await cursor.fetchall())
                
                # Testament distribution
                cursor = await conn.execute("SELECT testament, COUNT(*) FROM books GROUP BY testament")
                stats["testament_distribution"] = dict(await cursor.fetchall())
                
                # Most recent verses (if any)
                cursor = await conn.execute(
                    "SELECT book_id, COUNT(*) as verse_count FROM verses GROUP BY book_id ORDER BY verse_count DESC LIMIT 5"
                )
                stats["top_books_by_verse_count"] = dict(await cursor.fetchall())
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager: The global database manager
        
    Raises:
        RuntimeError: If database manager is not initialized
    """
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call initialize_database() first.")
    return _db_manager


async def initialize_database(db_path: Path, max_connections: int = 10) -> None:
    """
    Initialize the global database manager.
    
    Args:
        db_path: Path to SQLite database file
        max_connections: Maximum number of concurrent connections
    """
    global _db_manager
    _db_manager = DatabaseManager(db_path, max_connections)
    await _db_manager.initialize()


async def close_database() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager:
        # Connections are automatically closed by context managers
        _db_manager = None
        logger.info("Database manager closed")


# Convenience functions for common operations
async def execute_query(query: str, params: tuple = ()) -> list:
    """
    Execute a read-only query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of query results
    """
    db_manager = get_database_manager()
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(query, params)
        return await cursor.fetchall()


async def execute_search_query(query: str, params: tuple = ()) -> list:
    """
    Execute an FTS5 search query and return results.
    
    Args:
        query: FTS5 search query
        params: Query parameters
        
    Returns:
        List of search results with relevance scores
    """
    db_manager = get_database_manager()
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(query, params)
        return await cursor.fetchall()


if __name__ == "__main__":
    # For testing connection management
    import asyncio
    from .schema import create_schema
    
    async def test_connection():
        # Create test database
        test_db = Path("test_connection.db")
        create_schema(test_db)
        
        try:
            # Initialize database manager
            await initialize_database(test_db)
            
            # Test health check
            db_manager = get_database_manager()
            health = await db_manager.health_check()
            print(f"✅ Health check: {health}")
            
            # Test stats
            stats = await db_manager.get_database_stats()
            print(f"📊 Database stats: {stats}")
            
            # Test query
            results = await execute_query("SELECT COUNT(*) FROM books")
            print(f"📚 Book count: {results[0][0]}")
            
        finally:
            await close_database()
            test_db.unlink(missing_ok=True)
    
    asyncio.run(test_connection())