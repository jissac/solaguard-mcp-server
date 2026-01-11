"""
Unit tests for verse retrieval functionality.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.verse_retrieval import (
    get_verse_data,
    validate_translation_exists,
    get_available_translations,
    VerseRetrievalError,
    _format_verse_response,
)
from solaguard.context.theological import wrap_verse_response


class TestVerseRetrieval:
    """Test cases for verse retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_verse_data_single_verse(self):
        """Test retrieving a single verse."""
        # Mock database manager and connection
        mock_db_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        # Mock verse data
        mock_verse_data = {
            "id": 1,
            "book_id": "JHN",
            "chapter": 3,
            "verse": 16,
            "text": "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
            "name": "John",
            "testament": "NT",
            "author": "John",
            "genre": "Gospel"
        }
        
        mock_cursor.fetchone.return_value = mock_verse_data
        mock_cursor.fetchall.return_value = [mock_verse_data]
        mock_conn.execute.return_value = mock_cursor
        mock_db_manager.get_connection.return_value.__aenter__.return_value = mock_conn
        
        # Mock book metadata
        mock_book_data = {
            "id": "JHN",
            "name": "John",
            "testament": "NT",
            "author": "John",
            "genre": "Gospel",
            "canonical_order": 43
        }
        
        # Patch get_database_manager
        with pytest.MonkeyPatch().context() as m:
            m.setattr("solaguard.tools.verse_retrieval.get_database_manager", lambda: mock_db_manager)
            
            # Mock the database calls to return our test data
            async def mock_get_single_verse(*args):
                return [mock_verse_data]
            
            async def mock_get_book_metadata(*args):
                return mock_book_data
            
            m.setattr("solaguard.tools.verse_retrieval._get_single_verse", mock_get_single_verse)
            m.setattr("solaguard.tools.verse_retrieval._get_book_metadata", mock_get_book_metadata)
            
            # Test the function
            result = await get_verse_data("John 3:16", "KJV")
            
            # Verify result structure
            assert "verse" in result
            assert "context" in result
            assert "theological_frame" in result
            assert "metadata" in result
            
            verse = result["verse"]
            assert verse["reference"] == "John 3:16"
            assert verse["book_id"] == "JHN"
            assert verse["chapter"] == 3
            assert verse["verse"] == 16
            assert "For God so loved the world" in verse["text"]
    
    @pytest.mark.asyncio
    async def test_get_verse_data_invalid_reference(self):
        """Test handling of invalid references."""
        with pytest.raises(VerseRetrievalError) as exc_info:
            await get_verse_data("Invalid 99:99", "KJV")
        
        assert "Invalid reference format" in str(exc_info.value)
    
    def test_format_verse_response_single_verse(self):
        """Test formatting a single verse response."""
        verses = [{
            "id": 1,
            "book_id": "JHN",
            "chapter": 3,
            "verse": 16,
            "text": "For God so loved the world...",
            "name": "John"
        }]
        
        book_metadata = {
            "testament": "NT",
            "author": "John",
            "genre": "Gospel",
            "canonical_order": 43
        }
        
        result = _format_verse_response(
            verses=verses,
            original_reference="John 3:16",
            translation="KJV",
            book_metadata=book_metadata
        )
        
        assert result["verse"]["reference"] == "John 3:16"
        assert result["metadata"]["passage_type"] == "single_verse"
        assert result["metadata"]["verse_count"] == 1
        assert result["metadata"]["book_metadata"]["testament"] == "NT"
    
    def test_format_verse_response_verse_range(self):
        """Test formatting a verse range response."""
        verses = [
            {
                "id": 1,
                "book_id": "JHN",
                "chapter": 3,
                "verse": 16,
                "text": "For God so loved the world...",
                "name": "John"
            },
            {
                "id": 2,
                "book_id": "JHN",
                "chapter": 3,
                "verse": 17,
                "text": "For God sent not his Son...",
                "name": "John"
            }
        ]
        
        book_metadata = {
            "testament": "NT",
            "author": "John",
            "genre": "Gospel",
            "canonical_order": 43
        }
        
        result = _format_verse_response(
            verses=verses,
            original_reference="John 3:16-17",
            translation="KJV",
            book_metadata=book_metadata
        )
        
        assert result["verse"]["verse_range"] == "16-17"
        assert result["metadata"]["passage_type"] == "verse_range"
        assert result["metadata"]["verse_count"] == 2
        assert "[16]" in result["verse"]["text"]
        assert "[17]" in result["verse"]["text"]
    
    def test_create_theological_context(self):
        """Test theological context creation."""
        # Test Old Testament context
        ot_metadata = {
            "testament": "OT",
            "genre": "Law",
            "author": "Moses"
        }
        
        context = wrap_verse_response({
            "reference": "Genesis 1:1",
            "verses": [{"text": "In the beginning God created the heaven and the earth."}],
            "metadata": ot_metadata
        }, "Genesis 1:1", "KJV")
        
        context_str = str(context)
        assert "Old Testament Scripture" in context_str
        assert "Law" in context_str or "Mosaic" in context_str
        assert "King James Version" in context_str
        
        # Test New Testament context
        nt_metadata = {
            "testament": "NT",
            "genre": "Gospel",
            "author": "John"
        }
        
        context = wrap_verse_response({
            "reference": "John 3:16",
            "verses": [{"text": "For God so loved the world..."}],
            "metadata": nt_metadata
        }, "John 3:16", "WEB")
        
        context_str = str(context)
        assert "New Testament Scripture" in context_str
        assert "Gospel" in context_str
        assert "World English Bible" in context_str


class TestValidationFunctions:
    """Test validation and utility functions."""
    
    @pytest.mark.asyncio
    async def test_validate_translation_exists(self):
        """Test translation validation."""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        # Mock successful validation
        mock_cursor.fetchone.return_value = (1,)  # Count = 1
        mock_conn.execute.return_value = mock_cursor
        mock_db_manager.get_connection.return_value.__aenter__.return_value = mock_conn
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("solaguard.tools.verse_retrieval.get_database_manager", lambda: mock_db_manager)
            
            result = await validate_translation_exists("KJV")
            assert result is True
        
        # Mock failed validation
        mock_cursor.fetchone.return_value = (0,)  # Count = 0
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("solaguard.tools.verse_retrieval.get_database_manager", lambda: mock_db_manager)
            
            result = await validate_translation_exists("INVALID")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_available_translations(self):
        """Test getting available translations."""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        
        # Mock translation data
        mock_cursor.fetchall.return_value = [("KJV",), ("WEB",), ("TR",)]
        mock_conn.execute.return_value = mock_cursor
        mock_db_manager.get_connection.return_value.__aenter__.return_value = mock_conn
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("solaguard.tools.verse_retrieval.get_database_manager", lambda: mock_db_manager)
            
            result = await get_available_translations()
            assert result == ["KJV", "WEB", "TR"]


if __name__ == "__main__":
    pytest.main([__file__])