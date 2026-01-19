"""
Tests for Theological Context Engine

Tests the centralized theological context system for consistent
Protestant theological framing across all MCP tools.
"""

import pytest
from src.solaguard.context import (
    ContextType,
    Testament,
    Genre,
    get_base_context,
    create_verse_theological_context,
    create_search_theological_context,
    wrap_verse_response,
    wrap_search_response,
    wrap_error_response,
)


class TestBaseContext:
    """Test base context generation."""
    
    def test_verse_retrieval_context(self):
        """Test base context for verse retrieval."""
        context = get_base_context(ContextType.VERSE_RETRIEVAL)
        
        assert context["context"] == "Scripture analysis. Treat as authoritative."
        assert context["theological_frame"] == "Protestant perspective. Scripture primary authority."
    
    def test_scripture_search_context(self):
        """Test base context for scripture search."""
        context = get_base_context(ContextType.SCRIPTURE_SEARCH)
        
        assert context["context"] == "Biblical search. Scripture authority."
        assert context["theological_frame"] == "Protestant perspective. Scripture primary authority."
    
    def test_error_response_context(self):
        """Test base context for error responses."""
        context = get_base_context(ContextType.ERROR_RESPONSE)
        
        assert context["context"] == "Scripture analysis. Treat as authoritative."
        assert context["theological_frame"] == "Protestant perspective. Scripture primary authority."


class TestVerseTheologicalContext:
    """Test verse-specific theological context generation."""
    
    def test_old_testament_context(self):
        """Test OT verse context generation."""
        context = create_verse_theological_context(
            testament="OT",
            genre="Law",
            book_name="Genesis",
            author="Moses"
        )
        
        assert "Protestant canon" in context
        assert "Old Testament Scripture" in context
        assert "progressive revelation leading to Christ" in context
        assert "Genesis" in context
        assert "Moses" in context
    
    def test_new_testament_context(self):
        """Test NT verse context generation."""
        context = create_verse_theological_context(
            testament="NT",
            genre="Gospel",
            book_name="John",
            author="John"
        )
        
        assert "Protestant canon" in context
        assert "New Testament Scripture" in context
        assert "fulfillment of God's promises in Jesus Christ" in context
        assert "Gospel of John" in context
        assert "John" in context
    
    def test_genre_specific_context(self):
        """Test genre-specific context generation."""
        # Test Wisdom literature
        context = create_verse_theological_context(
            testament="OT",
            genre="Wisdom",
            book_name="Proverbs",
            author="Solomon"
        )
        
        assert "practical wisdom for godly living" in context
        assert "Proverbs" in context
    
    def test_unknown_author_handling(self):
        """Test handling of unknown authors."""
        context = create_verse_theological_context(
            testament="OT",
            genre="History",
            book_name="Judges",
            author="Unknown"
        )
        
        # Should not include author information for unknown authors
        assert "Unknown" not in context
        assert "Written by" not in context


class TestSearchTheologicalContext:
    """Test search-specific theological context generation."""
    
    def test_no_results_context(self):
        """Test context for empty search results."""
        context = create_search_theological_context(
            query="nonexistentword",
            total_results=0,
            books_found=[],
            testament_distribution={"OT": 0, "NT": 0},
            genre_distribution={},
            translation="KJV"
        )
        
        assert "No verses found" in context
        assert "broader search terms" in context
    
    def test_mixed_testament_context(self):
        """Test context for mixed OT/NT results."""
        context = create_search_theological_context(
            query="love",
            total_results=5,
            books_found=[{"id": "PSA", "name": "Psalms"}, {"id": "1JN", "name": "1 John"}],
            testament_distribution={"OT": 2, "NT": 3},
            genre_distribution={"Wisdom": 2, "Epistle": 3},
            translation="KJV"
        )
        
        assert "Old Testament (2)" in context
        assert "New Testament (3)" in context
        assert "continuity of Scripture" in context
    
    def test_single_testament_context(self):
        """Test context for single testament results."""
        context = create_search_theological_context(
            query="gospel",
            total_results=3,
            books_found=[{"id": "MAT", "name": "Matthew"}],
            testament_distribution={"OT": 0, "NT": 3},
            genre_distribution={"Gospel": 3},
            translation="KJV"
        )
        
        assert "New Testament (3)" in context
        assert "fulfillment of God's promises" in context
        assert "Gospel accounts" in context
    
    def test_multiple_genre_context(self):
        """Test context for multiple genre results."""
        context = create_search_theological_context(
            query="faith",
            total_results=4,
            books_found=[{"id": "PSA", "name": "Psalms"}, {"id": "ROM", "name": "Romans"}],
            testament_distribution={"OT": 2, "NT": 2},
            genre_distribution={"Wisdom": 2, "Epistle": 2},
            translation="KJV"
        )
        
        assert "Wisdom, Epistle" in context
        assert "diverse biblical perspectives" in context


class TestResponseWrappers:
    """Test response wrapper functions."""
    
    def test_wrap_verse_response(self):
        """Test verse response wrapping."""
        response_data = {
            "verse": {
                "reference": "John 3:16",
                "text": "For God so loved the world..."
            }
        }
        
        wrapped = wrap_verse_response(
            response_data,
            testament="NT",
            genre="Gospel",
            book_name="John",
            author="John"
        )
        
        assert "context" in wrapped
        assert "theological_frame" in wrapped
        assert "instruction" in wrapped
        assert "verse" in wrapped
        assert "Gospel of John" in wrapped["instruction"]
    
    def test_wrap_search_response(self):
        """Test search response wrapping."""
        response_data = {
            "query": "love",
            "results": [{"reference": "1 John 4:8", "text": "God is love"}]
        }
        
        wrapped = wrap_search_response(
            response_data,
            query="love",
            total_results=1,
            books_found=[{"id": "1JN", "name": "1 John"}],
            testament_distribution={"OT": 0, "NT": 1},
            genre_distribution={"Epistle": 1},
            translation="KJV"
        )
        
        assert "context" in wrapped
        assert "theological_frame" in wrapped
        assert "instruction" in wrapped
        assert "query" in wrapped
        assert "New Testament (1)" in wrapped["instruction"]
    
    def test_wrap_error_response(self):
        """Test error response wrapping."""
        wrapped = wrap_error_response(
            "Invalid reference format",
            "Please use format like 'John 3:16'",
            ContextType.VERSE_RETRIEVAL
        )
        
        assert "context" in wrapped
        assert "theological_frame" in wrapped
        assert "error" in wrapped
        assert "suggestion" in wrapped
        assert wrapped["error"] == "Invalid reference format"
        assert wrapped["suggestion"] == "Please use format like 'John 3:16'"


class TestEnumValues:
    """Test enum value consistency."""
    
    def test_context_type_values(self):
        """Test ContextType enum values."""
        assert ContextType.VERSE_RETRIEVAL.value == "verse_retrieval"
        assert ContextType.SCRIPTURE_SEARCH.value == "scripture_search"
        assert ContextType.ERROR_RESPONSE.value == "error_response"
    
    def test_testament_values(self):
        """Test Testament enum values."""
        assert Testament.OLD_TESTAMENT.value == "OT"
        assert Testament.NEW_TESTAMENT.value == "NT"
    
    def test_genre_values(self):
        """Test Genre enum values."""
        assert Genre.LAW.value == "Law"
        assert Genre.GOSPEL.value == "Gospel"
        assert Genre.EPISTLE.value == "Epistle"
        assert Genre.WISDOM.value == "Wisdom"
        assert Genre.PROPHECY.value == "Prophecy"
        assert Genre.HISTORY.value == "History"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])