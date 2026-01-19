"""
Unit tests for MCP server functionality.
"""

import pytest
import asyncio
import tempfile
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.server import ensure_database, get_verse, search_scripture
from solaguard.database.schema import create_schema


class TestServerFunctionality:
    """Test cases for MCP server functionality."""
    
    @pytest.mark.asyncio
    async def test_ensure_database(self):
        """Test database initialization in server."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Test database initialization
                db_manager = await ensure_database()
                assert db_manager is not None
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_ensure_database_missing_file(self):
        """Test database initialization with missing file."""
        non_existent_path = "/tmp/non_existent_db_12345.db"
        
        # Reset global database managers
        import solaguard.database.connection as conn_module
        import solaguard.server as server_module
        conn_module._db_manager = None
        server_module._db_manager = None
        
        with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': non_existent_path}):
            with pytest.raises(Exception):  # Will raise FileNotFoundError or similar
                await ensure_database()
    
    def test_mcp_tools_registration(self):
        """Test that MCP tools are properly registered."""
        # FastMCP tools are FunctionTool objects with a .fn attribute
        # Verify tools exist and have callable functions
        
        # Verify tools exist
        assert get_verse is not None
        assert search_scripture is not None
        
        # Verify they have callable fn attributes
        assert hasattr(get_verse, 'fn')
        assert callable(get_verse.fn)
        assert hasattr(search_scripture, 'fn')
        assert callable(search_scripture.fn)
    
    @pytest.mark.asyncio
    async def test_get_verse_tool_mock(self):
        """Test get_verse tool with mocked database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create database with test data
            create_schema(db_path)
            
            # Add test verse
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO verses (translation_id, book_id, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
                    ("KJV", "JHN", 3, 16, "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.")
                )
                conn.execute("INSERT INTO verses_fts(rowid, book_id, text) SELECT id, book_id, text FROM verses")
                conn.commit()
            
            # Reset global database manager
            import solaguard.database.connection as conn_module
            import solaguard.server as server_module
            conn_module._db_manager = None
            server_module._db_manager = None
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Test tool execution directly using .fn
                result = await get_verse.fn(reference="John 3:16", translation="KJV")
                
                # Verify result structure
                assert "verse" in result
                assert "context" in result
                assert "theological_frame" in result
                
                verse = result["verse"]
                assert verse["reference"] == "John 3:16"
                assert verse["book_id"] == "JHN"
                assert "For God so loved the world" in verse["text"]
        
        finally:
            # Cleanup
            import solaguard.database.connection as conn_module
            import solaguard.server as server_module
            if conn_module._db_manager:
                await conn_module.close_database()
            conn_module._db_manager = None
            server_module._db_manager = None
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_get_verse_tool_invalid_reference(self):
        """Test get_verse tool with invalid reference."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Test with invalid reference using .fn
                result = await get_verse.fn(reference="Invalid 99:99", translation="KJV")
                
                # Should return error
                assert "error" in result
                assert "Invalid reference format" in result["error"] or "Unknown book name" in result["error"]
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_get_verse_tool_invalid_translation(self):
        """Test get_verse tool with invalid translation."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Reset global database manager
            import solaguard.database.connection as conn_module
            import solaguard.server as server_module
            conn_module._db_manager = None
            server_module._db_manager = None
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Test with invalid translation using .fn
                result = await get_verse.fn(reference="John 3:16", translation="INVALID")
                
                # Should return error with available translations
                assert "error" in result
                # The error message might be about format or availability
                assert "translation" in result["error"].lower()
        
        finally:
            # Cleanup
            import solaguard.database.connection as conn_module
            import solaguard.server as server_module
            if conn_module._db_manager:
                await conn_module.close_database()
            conn_module._db_manager = None
            server_module._db_manager = None
            if db_path.exists():
                db_path.unlink()
    
    @pytest.mark.asyncio
    async def test_search_scripture_tool_placeholder(self):
        """Test search_scripture tool (placeholder implementation)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid database
            create_schema(db_path)
            
            # Reset global database manager
            import solaguard.database.connection as conn_module
            import solaguard.server as server_module
            conn_module._db_manager = None
            server_module._db_manager = None
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Test tool execution directly using .fn
                result = await search_scripture.fn(query="love", translation="KJV")
                
                # Verify result structure (empty results since no verses)
                assert "results" in result
                assert "context" in result
                assert "theological_frame" in result
                assert result["query"] == "love"
        
        finally:
            # Cleanup
            import solaguard.database.connection as conn_module
            import solaguard.server as server_module
            if conn_module._db_manager:
                await conn_module.close_database()
            conn_module._db_manager = None
            server_module._db_manager = None
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
