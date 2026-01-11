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

from solaguard.server import ensure_database, mcp
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
        non_existent_path = "/tmp/non_existent_db.db"
        
        with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': non_existent_path}):
            with pytest.raises(FileNotFoundError):
                await ensure_database()
    
    @pytest.mark.asyncio
    async def test_mcp_tools_registration(self):
        """Test that MCP tools are properly registered."""
        # Get registered tools
        tools = await mcp.get_tools()
        
        # Verify expected tools are registered
        tool_names = [tool.name for tool in tools]
        assert "get_verse" in tool_names
        assert "search_scripture" in tool_names
        
        # Verify tool signatures
        get_verse_tool = next(tool for tool in tools if tool.name == "get_verse")
        assert get_verse_tool.description is not None
        assert "reference" in str(get_verse_tool.inputSchema)
        assert "translation" in str(get_verse_tool.inputSchema)
    
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
                conn.execute("INSERT INTO verses_fts(verse_id, book_id, text) SELECT id, book_id, text FROM verses")
                conn.commit()
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Get the tool
                tools = await mcp.get_tools()
                get_verse_tool = next(tool for tool in tools if tool.name == "get_verse")
                
                # Test tool execution
                result = await get_verse_tool.fn(reference="John 3:16", translation="KJV")
                
                # Verify result structure
                assert "verse" in result
                assert "context" in result
                assert "theological_frame" in result
                
                verse = result["verse"]
                assert verse["reference"] == "John 3:16"
                assert verse["book_id"] == "JHN"
                assert "For God so loved the world" in verse["text"]
        
        finally:
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
                
                # Get the tool
                tools = await mcp.get_tools()
                get_verse_tool = next(tool for tool in tools if tool.name == "get_verse")
                
                # Test with invalid reference
                result = await get_verse_tool.fn(reference="Invalid 99:99", translation="KJV")
                
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
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Get the tool
                tools = await mcp.get_tools()
                get_verse_tool = next(tool for tool in tools if tool.name == "get_verse")
                
                # Test with invalid translation
                result = await get_verse_tool.fn(reference="John 3:16", translation="INVALID")
                
                # Should return error with available translations
                assert "error" in result
                assert "not available" in result["error"]
                assert "available_translations" in result
        
        finally:
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
            
            # Mock environment variable
            with patch.dict('os.environ', {'SOLAGUARD_DATABASE_PATH': str(db_path)}):
                # Initialize database
                await ensure_database()
                
                # Get the tool
                tools = await mcp.get_tools()
                search_tool = next(tool for tool in tools if tool.name == "search_scripture")
                
                # Test tool execution (placeholder)
                result = await search_tool.fn(query="love", translation="KJV")
                
                # Verify result structure (placeholder returns empty results)
                assert "results" in result
                assert "context" in result
                assert "theological_frame" in result
                assert result["query"] == "love"
        
        finally:
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])