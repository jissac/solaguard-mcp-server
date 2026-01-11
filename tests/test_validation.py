"""
Tests for Input Validation System

Tests the centralized input validation system for consistent error handling
and helpful user feedback across all MCP tools.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.solaguard.validation import (
    ValidationError,
    validate_biblical_reference,
    validate_translation,
    validate_search_query,
    validate_search_limit,
    sanitize_search_query,
    get_validation_suggestions,
)


class TestValidationError:
    """Test ValidationError exception class."""
    
    def test_validation_error_creation(self):
        """Test ValidationError creation with all parameters."""
        error = ValidationError(
            "Invalid input",
            "Please try again",
            "reference"
        )
        
        assert error.message == "Invalid input"
        assert error.suggestion == "Please try again"
        assert error.field == "reference"
        assert str(error) == "Invalid input"
    
    def test_validation_error_to_dict(self):
        """Test ValidationError conversion to dictionary."""
        error = ValidationError(
            "Invalid input",
            "Please try again",
            "reference"
        )
        
        result = error.to_dict()
        expected = {
            "error": "Invalid input",
            "suggestion": "Please try again",
            "field": "reference"
        }
        
        assert result == expected
    
    def test_validation_error_minimal(self):
        """Test ValidationError with minimal parameters."""
        error = ValidationError("Invalid input")
        
        result = error.to_dict()
        assert result["error"] == "Invalid input"
        assert "suggestion" not in result
        assert "field" not in result


class TestBiblicalReferenceValidation:
    """Test biblical reference validation."""
    
    @pytest.mark.asyncio
    async def test_validate_empty_reference(self):
        """Test validation of empty reference."""
        with pytest.raises(ValidationError) as exc_info:
            await validate_biblical_reference("")
        
        error = exc_info.value
        assert "cannot be empty" in error.message
        assert "John 3:16" in error.suggestion
        assert error.field == "reference"
    
    @pytest.mark.asyncio
    async def test_validate_whitespace_reference(self):
        """Test validation of whitespace-only reference."""
        with pytest.raises(ValidationError) as exc_info:
            await validate_biblical_reference("   ")
        
        error = exc_info.value
        assert "cannot be empty" in error.message
    
    @pytest.mark.asyncio
    async def test_validate_too_long_reference(self):
        """Test validation of overly long reference."""
        long_ref = "A" * 60
        
        with pytest.raises(ValidationError) as exc_info:
            await validate_biblical_reference(long_ref)
        
        error = exc_info.value
        assert "too long" in error.message
    
    @pytest.mark.asyncio
    async def test_validate_invalid_format_reference(self):
        """Test validation of invalid format reference."""
        with patch('src.solaguard.validation.validators.parse_reference') as mock_parse:
            from src.solaguard.tools.reference_parser import ReferenceParseError
            mock_parse.side_effect = ReferenceParseError("Invalid format")
            
            with pytest.raises(ValidationError) as exc_info:
                await validate_biblical_reference("invalid format")
            
            error = exc_info.value
            assert "Invalid biblical reference format" in error.message
            assert "John 3:16" in error.suggestion
    
    @pytest.mark.asyncio
    async def test_validate_valid_reference(self):
        """Test validation of valid reference."""
        with patch('src.solaguard.validation.validators.parse_reference') as mock_parse:
            with patch('src.solaguard.validation.validators._validate_reference_against_database') as mock_db_validate:
                # Mock successful parsing
                mock_ref = AsyncMock()
                mock_ref.book_id = "JHN"
                mock_ref.chapter = 3
                mock_ref.verse = 16
                mock_parse.return_value = mock_ref
                
                # Mock successful database validation
                mock_db_validate.return_value = None
                
                result = await validate_biblical_reference("John 3:16")
                
                assert result["book_id"] == "JHN"
                assert result["chapter"] == 3
                assert result["verse"] == 16
                assert result["original"] == "John 3:16"


class TestTranslationValidation:
    """Test translation validation."""
    
    @pytest.mark.asyncio
    async def test_validate_empty_translation(self):
        """Test validation of empty translation."""
        with pytest.raises(ValidationError) as exc_info:
            await validate_translation("")
        
        error = exc_info.value
        assert "cannot be empty" in error.message
        assert "KJV" in error.suggestion
    
    @pytest.mark.asyncio
    async def test_validate_invalid_format_translation(self):
        """Test validation of invalid format translation."""
        with pytest.raises(ValidationError) as exc_info:
            await validate_translation("invalid-format!")
        
        error = exc_info.value
        assert "Invalid translation format" in error.message
        assert "uppercase" in error.suggestion
    
    @pytest.mark.asyncio
    async def test_validate_nonexistent_translation(self):
        """Test validation of non-existent translation."""
        with patch('src.solaguard.validation.validators.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            
            # Mock translation doesn't exist
            mock_cursor.fetchone.side_effect = [(0,), [("KJV",), ("WEB",)]]
            mock_cursor.fetchall.return_value = [("KJV",), ("WEB",)]
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            with pytest.raises(ValidationError) as exc_info:
                await validate_translation("XYZ")  # Valid format but doesn't exist
            
            error = exc_info.value
            assert "not available" in error.message
            assert "KJV, WEB" in error.suggestion
    
    @pytest.mark.asyncio
    async def test_validate_valid_translation(self):
        """Test validation of valid translation."""
        with patch('src.solaguard.validation.validators.get_database_manager') as mock_db:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = (1,)  # Translation exists
            mock_conn.execute.return_value = mock_cursor
            mock_db.return_value.get_connection.return_value.__aenter__.return_value = mock_conn
            
            result = await validate_translation("kjv")  # Test case normalization
            assert result == "KJV"


class TestSearchQueryValidation:
    """Test search query validation."""
    
    def test_validate_empty_query(self):
        """Test validation of empty query."""
        with pytest.raises(ValidationError) as exc_info:
            validate_search_query("")
        
        error = exc_info.value
        assert "cannot be empty" in error.message
        assert "love" in error.suggestion
    
    def test_validate_too_long_query(self):
        """Test validation of overly long query."""
        long_query = "A" * 250
        
        with pytest.raises(ValidationError) as exc_info:
            validate_search_query(long_query)
        
        error = exc_info.value
        assert "too long" in error.message
        assert "200 characters" in error.suggestion
    
    def test_validate_valid_query(self):
        """Test validation of valid query."""
        result = validate_search_query("love")
        assert result == "love"
    
    def test_validate_query_with_quotes(self):
        """Test validation of query with quoted phrases."""
        result = validate_search_query('"love one another"')
        assert result == '"love one another"'
    
    def test_validate_query_sanitization(self):
        """Test that query sanitization is applied."""
        # This should be sanitized by removing dangerous characters
        result = validate_search_query("love & peace")
        assert "&" not in result  # Should be sanitized out


class TestSearchLimitValidation:
    """Test search limit validation."""
    
    def test_validate_string_limit(self):
        """Test validation of string limit (should convert)."""
        result = validate_search_limit("10")
        assert result == 10
    
    def test_validate_invalid_string_limit(self):
        """Test validation of invalid string limit."""
        with pytest.raises(ValidationError) as exc_info:
            validate_search_limit("invalid")
        
        error = exc_info.value
        assert "must be a number" in error.message
    
    def test_validate_too_low_limit(self):
        """Test validation of too low limit."""
        with pytest.raises(ValidationError) as exc_info:
            validate_search_limit(0)
        
        error = exc_info.value
        assert "at least 1" in error.message
    
    def test_validate_too_high_limit(self):
        """Test validation of too high limit."""
        with pytest.raises(ValidationError) as exc_info:
            validate_search_limit(100)
        
        error = exc_info.value
        assert "cannot exceed 50" in error.message
    
    def test_validate_valid_limit(self):
        """Test validation of valid limit."""
        result = validate_search_limit(25)
        assert result == 25


class TestQuerySanitization:
    """Test search query sanitization."""
    
    def test_sanitize_empty_query(self):
        """Test sanitization of empty query."""
        assert sanitize_search_query("") == ""
        assert sanitize_search_query("   ") == ""
    
    def test_sanitize_basic_query(self):
        """Test sanitization of basic query."""
        assert sanitize_search_query("love") == "love"
        assert sanitize_search_query("  love  ") == "love"
    
    def test_sanitize_quoted_phrases(self):
        """Test sanitization preserves quoted phrases."""
        result = sanitize_search_query('"love one another"')
        assert result == '"love one another"'
    
    def test_sanitize_boolean_operators(self):
        """Test sanitization preserves boolean operators."""
        result = sanitize_search_query("love AND peace")
        assert result == "love AND peace"
        
        result = sanitize_search_query("love OR joy")
        assert result == "love OR joy"
        
        result = sanitize_search_query("love NOT hate")
        assert result == "love NOT hate"
    
    def test_sanitize_dangerous_characters(self):
        """Test sanitization removes dangerous characters."""
        result = sanitize_search_query("love & peace")
        assert "&" not in result
        
        result = sanitize_search_query("love; DROP TABLE")
        assert ";" not in result
        assert "DROP" not in result or result == "love DROP TABLE"  # May be kept as word
    
    def test_sanitize_normalize_whitespace(self):
        """Test sanitization normalizes whitespace."""
        result = sanitize_search_query("love    peace")
        assert result == "love peace"


class TestValidationSuggestions:
    """Test validation suggestion system."""
    
    def test_reference_format_suggestions(self):
        """Test reference format suggestions."""
        suggestions = get_validation_suggestions("reference_format")
        
        assert any("John 3:16" in s for s in suggestions)
        assert any("Romans 8:28-30" in s for s in suggestions)
        assert any("abbreviated" in s for s in suggestions)
    
    def test_search_query_suggestions(self):
        """Test search query suggestions."""
        suggestions = get_validation_suggestions("search_query")
        
        assert any("love" in s for s in suggestions)
        assert any("quotes" in s for s in suggestions)
        assert any("boolean" in s for s in suggestions)
    
    def test_translation_suggestions(self):
        """Test translation suggestions."""
        suggestions = get_validation_suggestions("translation")
        
        assert any("KJV" in s for s in suggestions)
        assert any("uppercase" in s for s in suggestions)
    
    def test_unknown_error_type_suggestions(self):
        """Test suggestions for unknown error type."""
        suggestions = get_validation_suggestions("unknown_type")
        
        assert len(suggestions) == 1
        assert "check your input format" in suggestions[0]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])