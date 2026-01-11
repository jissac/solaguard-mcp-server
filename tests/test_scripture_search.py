"""
Tests for Scripture Search Tool

Tests the search_scripture MCP tool functionality including FTS5 search,
query sanitization, and theological context generation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from src.solaguard.tools.scripture_search import (
    search_scripture_data,
    ScriptureSearchError,
    validate_search_translation,
    get_search_statistics,
)
from src.solaguard.validation.validators import sanitize_search_query


class TestQuerySanitization:
    """Test search query sanitization."""
    
    def test_basic_query_sanitization(self):
        """Test basic query cleaning."""
        assert sanitize_search_query("love") == "love"
        assert sanitize_search_query("  love  ") == "love"
        assert sanitize_search_query("") == ""
        assert sanitize_search_query("   ") == ""
    
    def test_quoted_phrase_preservation(self):
        """Test that quoted phrases are preserved."""
        assert sanitize_search_query('"love one another"') == '"love one another"'
        assert sanitize_search_query('love "one another" peace') == 'love "one another" peace'
    
    def test_boolean_operator_preservation(self):
        """Test that boolean operators are preserved."""
        assert sanitize_search_query("love AND peace") == "love AND peace"
        assert sanitize_search_query("love OR joy") == "love OR joy"
        assert sanitize_search_query("love NOT hate") == "love NOT hate"
    
    def test_dangerous_character_removal(self):
        """Test that potentially dangerous characters are removed."""
        # Test SQL injection attempts
        assert ";" not in sanitize_search_query("love; DROP TABLE verses;")
        assert "'" not in sanitize_search_query("love' OR 1=1--")
        
        # Test FTS5 injection attempts
        dangerous_query = "love NEAR/5 peace"
        sanitized = sanitize_search_query(dangerous_query)
        assert "NEAR" not in sanitized or sanitized == dangerous_query  # Either removed or kept if safe
    
    def test_empty_after_sanitization(self):
        """Test queries that become empty after sanitization."""
        assert sanitize_search_query(";;;") == ""
        assert sanitize_search_query("'''") == ""


class TestSearchValidation:
    """Test search validation functions."""
    
    @pytest.mark.asyncio
    async def test_validate_search_translation_success(self):
        """Test successful translation validation."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = (1,)  # Translation exists
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await validate_search_translation("KJV")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_search_translation_failure(self):
        """Test failed translation validation."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = (0,)  # Translation doesn't exist
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await validate_search_translation("INVALID")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_search_statistics(self):
        """Test search statistics retrieval."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            
            # Mock multiple queries
            mock_cursor.fetchone.side_effect = [(31102,), (31102,)]  # Total verses, FTS indexed
            mock_cursor.fetchall.return_value = [("KJV",), ("WEB",)]  # Available translations
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            stats = await get_search_statistics()
            
            assert stats["total_verses"] == 31102
            assert stats["fts_indexed_verses"] == 31102
            assert stats["fts5_available"] is True
            assert "KJV" in stats["available_translations"]
            assert "WEB" in stats["available_translations"]


class TestSearchFunctionality:
    """Test main search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_scripture_data_success(self):
        """Test successful scripture search."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            
            # Mock search results
            mock_search_results = [
                {
                    "id": 1,
                    "book_id": 43,
                    "chapter": 3,
                    "verse": 16,
                    "text": "For God so loved the world, that he gave his only begotten Son...",
                    "book_name": "John",
                    "testament": "NT",
                    "author": "John",
                    "genre": "Gospel",
                    "canonical_order": 43,
                    "relevance_score": 1.5,
                    "snippet": "For God so <mark>loved</mark> the world..."
                }
            ]
            
            # Mock metadata query
            mock_cursor.fetchall.side_effect = [
                # Search results
                [tuple(result.values()) for result in mock_search_results],
                # Book names for metadata
                [(43, "John")]
            ]
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await search_scripture_data("love", "KJV", 10)
            
            # Verify response structure
            assert "context" in result
            assert "theological_frame" in result
            assert "instruction" in result
            assert "query" in result
            assert "translation" in result
            assert "results" in result
            assert "metadata" in result
            
            # Verify search results
            assert len(result["results"]) == 1
            search_result = result["results"][0]
            assert search_result["reference"] == "John 3:16"
            assert search_result["book_name"] == "John"
            assert search_result["text"] == "For God so loved the world, that he gave his only begotten Son..."
            assert search_result["relevance_score"] == 1.5
            
            # Verify metadata
            metadata = result["metadata"]
            assert metadata["total_results"] == 1
            assert metadata["results_returned"] == 1
            assert len(metadata["books_found"]) == 1
            assert metadata["books_found"][0]["name"] == "John"
    
    @pytest.mark.asyncio
    async def test_search_scripture_data_empty_query(self):
        """Test search with empty query."""
        with pytest.raises(ScriptureSearchError, match="Empty or invalid search query"):
            await search_scripture_data("", "KJV", 10)
    
    @pytest.mark.asyncio
    async def test_search_scripture_data_no_results(self):
        """Test search with no results."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            
            # Mock empty search results
            mock_cursor.fetchall.side_effect = [[], []]  # No search results, no books
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await search_scripture_data("nonexistentword", "KJV", 10)
            
            # Verify empty results
            assert result["metadata"]["total_results"] == 0
            assert len(result["results"]) == 0
            assert "No verses found" in result["instruction"]
    
    @pytest.mark.asyncio
    async def test_search_scripture_data_database_error(self):
        """Test search with database error."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            with pytest.raises(ScriptureSearchError, match="Search failed"):
                await search_scripture_data("love", "KJV", 10)


class TestTheologicalContext:
    """Test theological context generation."""
    
    @pytest.mark.asyncio
    async def test_theological_context_mixed_testament(self):
        """Test context generation for mixed OT/NT results."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            
            # Mock mixed testament results
            mock_search_results = [
                {
                    "id": 1, "book_id": 19, "chapter": 23, "verse": 1,
                    "text": "The LORD is my shepherd...", "book_name": "Psalms",
                    "testament": "OT", "author": "David", "genre": "Wisdom",
                    "canonical_order": 19, "relevance_score": 1.2, "snippet": "..."
                },
                {
                    "id": 2, "book_id": 43, "chapter": 10, "verse": 11,
                    "text": "I am the good shepherd...", "book_name": "John",
                    "testament": "NT", "author": "John", "genre": "Gospel",
                    "canonical_order": 43, "relevance_score": 1.1, "snippet": "..."
                }
            ]
            
            mock_cursor.fetchall.side_effect = [
                [tuple(result.values()) for result in mock_search_results],
                [(19, "Psalms"), (43, "John")]
            ]
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await search_scripture_data("shepherd", "KJV", 10)
            
            # Verify mixed testament context
            instruction = result["instruction"]
            assert "Old Testament (1)" in instruction
            assert "New Testament (1)" in instruction
            assert "continuity of Scripture" in instruction
    
    @pytest.mark.asyncio
    async def test_theological_context_single_genre(self):
        """Test context generation for single genre results."""
        with patch('src.solaguard.tools.scripture_search.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            
            # Mock single genre results
            mock_search_results = [
                {
                    "id": 1, "book_id": 19, "chapter": 23, "verse": 1,
                    "text": "The LORD is my shepherd...", "book_name": "Psalms",
                    "testament": "OT", "author": "David", "genre": "Wisdom",
                    "canonical_order": 19, "relevance_score": 1.2, "snippet": "..."
                }
            ]
            
            mock_cursor.fetchall.side_effect = [
                [tuple(result.values()) for result in mock_search_results],
                [(19, "Psalms")]
            ]
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await search_scripture_data("shepherd", "KJV", 10)
            
            # Verify single genre context
            instruction = result["instruction"]
            assert "wisdom literature" in instruction
            assert "practical godly guidance" in instruction


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])