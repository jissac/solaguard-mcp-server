"""
Unit tests for database connection management.
"""

import pytest
import asyncio
import tempfile
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.database.connection import (
    DatabaseManager,
    initialize_database,
    close_database,
    get_database_manager,
    execute_query,
    execute_search_query
)
from solaguard.database.schema import create_schema


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""
    
    @pytest.mark.asyncio
    async def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Initialize database manager
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            assert db_manager._is_initialized is True
            assert db_manager.db_path == db_path
            assert db_manager.max_connections == 10  # default
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_database_manager_missing_file(self):
        """Test DatabaseManager with missing database file."""
        non_existent_path = Path("/tmp/non_existent_db.db")
        
        db_manager = DatabaseManager(non_existent_path)
        
        with pytest.raises(FileNotFoundError):
            await db_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_database_manager_connection(self):
        """Test database connection management."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Initialize database manager
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            # Test connection
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM books")
                count = (await cursor.fetchone())[0]
                assert count == 66  # Should have 66 books
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_database_manager_health_check(self):
        """Test database health check."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database with some test data
            create_schema(db_path)
            
            # Add a test verse
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO verses (translation_id, book_id, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                    ("KJV", "JHN", 3, 16, "For God so loved the world...")
                )
                conn.execute("INSERT INTO verses_fts(verse_id, book_id, text) SELECT id, book_id, text FROM verses")
                conn.commit()
            
            # Initialize database manager
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            # Test health check
            health = await db_manager.health_check()
            
            assert health["status"] == "healthy"
            assert health["verse_count"] == 1
            assert health["fts_index_count"] == 1
            assert "database_size_mb" in health
            assert health["max_connections"] == 10
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_database_manager_stats(self):
        """Test database statistics."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Initialize database manager
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            
            # Test stats
            stats = await db_manager.get_database_stats()
            
            assert "translations_count" in stats
            assert "books_count" in stats
            assert "verses_count" in stats
            assert "available_translations" in stats
            assert "testament_distribution" in stats
            
            assert stats["translations_count"] == 7  # Initial translations
            assert stats["books_count"] == 66  # Initial books
            assert stats["verses_count"] == 0  # No verses initially
        
        finally:
            if db_path.exists():
                db_path.unlink()


class TestGlobalDatabaseManager:
    """Test cases for global database manager functions."""
    
    @pytest.mark.asyncio
    async def test_initialize_database(self):
        """Test global database initialization."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Initialize global database manager
            await initialize_database(db_path)
            
            # Should be able to get manager
            db_manager = get_database_manager()
            assert db_manager is not None
            assert db_manager._is_initialized is True
            
            # Cleanup
            await close_database()
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_get_database_manager_not_initialized(self):
        """Test getting database manager when not initialized."""
        # Ensure no global manager exists
        import solaguard.database.connection as conn_module
        conn_module._db_manager = None
        
        with pytest.raises(RuntimeError, match="Database manager not initialized"):
            get_database_manager()
    
    @pytest.mark.asyncio
    async def test_execute_query(self):
        """Test query execution convenience function."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Initialize global database manager
            await initialize_database(db_path)
            
            # Test query execution
            results = await execute_query("SELECT COUNT(*) FROM books")
            assert len(results) == 1
            assert results[0][0] == 66
            
            # Test parameterized query
            results = await execute_query("SELECT name FROM books WHERE id = ?", ("JHN",))
            assert len(results) == 1
            assert results[0][0] == "John"
            
            # Cleanup
            await close_database()
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_execute_search_query(self):
        """Test search query execution convenience function."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database with test data
            create_schema(db_path)
            
            # Add test verse
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO verses (translation_id, book_id, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                    ("KJV", "JHN", 3, 16, "For God so loved the world...")
                )
                conn.execute("INSERT INTO verses_fts(verse_id, book_id, text) SELECT id, book_id, text FROM verses")
                conn.commit()
            
            # Initialize global database manager
            await initialize_database(db_path)
            
            # Test search query
            results = await execute_search_query("SELECT COUNT(*) FROM verses_fts WHERE text MATCH ?", ("love",))
            assert len(results) == 1
            assert results[0][0] == 1  # Should find one verse with "love"
            
            # Cleanup
            await close_database()
        
        finally:
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])