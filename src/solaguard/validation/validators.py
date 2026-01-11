"""
Core Input Validators

Centralized validation functions for all MCP tool inputs with consistent
error handling and helpful user feedback.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Union

from ..database.connection import get_database_manager
from ..tools.reference_parser import parse_reference, ReferenceParseError

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors with helpful suggestions."""
    
    def __init__(self, message: str, suggestion: str = "", field: str = ""):
        self.message = message
        self.suggestion = suggestion
        self.field = field
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for consistent error responses."""
        result = {"error": self.message}
        if self.suggestion:
            result["suggestion"] = self.suggestion
        if self.field:
            result["field"] = self.field
        return result


async def validate_biblical_reference(reference: str) -> Dict[str, Union[str, int]]:
    """
    Validate a biblical reference string and return parsed components.
    
    Args:
        reference: Biblical reference string (e.g., "John 3:16", "Romans 8:28-30")
        
    Returns:
        Dictionary with validated reference components
        
    Raises:
        ValidationError: If reference is invalid with helpful suggestions
    """
    if not reference or not reference.strip():
        raise ValidationError(
            "Biblical reference cannot be empty",
            "Please provide a reference like 'John 3:16' or 'Romans 8:28-30'",
            "reference"
        )
    
    reference = reference.strip()
    
    # Check for obviously invalid formats
    if len(reference) > 50:
        raise ValidationError(
            "Biblical reference is too long",
            "Please use a shorter format like 'John 3:16' or 'Romans 8:28-30'",
            "reference"
        )
    
    # Try to parse the reference
    try:
        parsed_ref = parse_reference(reference)
    except ReferenceParseError as e:
        # Convert parse error to validation error with suggestions
        suggestion = _get_reference_format_suggestion(reference)
        raise ValidationError(
            f"Invalid biblical reference format: {e}",
            suggestion,
            "reference"
        )
    
    # Validate against database (check if book exists, chapter/verse ranges)
    try:
        await _validate_reference_against_database(parsed_ref)
    except ValidationError:
        raise  # Re-raise validation errors as-is
    except Exception as e:
        logger.error(f"Database validation failed for '{reference}': {e}")
        raise ValidationError(
            "Unable to validate reference against database",
            "Please try again or check if the database is available",
            "reference"
        )
    
    return {
        "book_id": parsed_ref.book_id,
        "chapter": parsed_ref.chapter,
        "verse": parsed_ref.verse,
        "end_verse": getattr(parsed_ref, 'end_verse', None),
        "original": reference,
        "formatted": str(parsed_ref)
    }


async def validate_translation(translation: str) -> str:
    """
    Validate a translation code and return normalized version.
    
    Args:
        translation: Translation code (e.g., "KJV", "WEB")
        
    Returns:
        Normalized translation code
        
    Raises:
        ValidationError: If translation is invalid with available options
    """
    if not translation or not translation.strip():
        raise ValidationError(
            "Translation cannot be empty",
            "Please specify a translation like 'KJV' or 'WEB'",
            "translation"
        )
    
    translation = translation.strip().upper()
    
    # Check format
    if not re.match(r'^[A-Z0-9]{2,5}$', translation):
        raise ValidationError(
            "Invalid translation format",
            "Translation codes should be 2-5 uppercase letters/numbers (e.g., 'KJV', 'WEB')",
            "translation"
        )
    
    # Check against database
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM translations WHERE id = ?",
                (translation,)
            )
            count = (await cursor.fetchone())[0]
            
            if count == 0:
                # Get available translations for suggestion
                cursor = await conn.execute("SELECT id FROM translations ORDER BY id")
                available = [row[0] for row in await cursor.fetchall()]
                
                raise ValidationError(
                    f"Translation '{translation}' is not available",
                    f"Available translations: {', '.join(available)}",
                    "translation"
                )
    
    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Translation validation failed for '{translation}': {e}")
        raise ValidationError(
            "Unable to validate translation",
            "Please try again or check if the database is available",
            "translation"
        )
    
    return translation


def validate_search_query(query: str) -> str:
    """
    Validate and sanitize a search query.
    
    Args:
        query: Search query string
        
    Returns:
        Sanitized query string
        
    Raises:
        ValidationError: If query is invalid with helpful suggestions
    """
    if not query or not query.strip():
        raise ValidationError(
            "Search query cannot be empty",
            "Please enter search terms like 'love', 'faith', or \"love one another\"",
            "query"
        )
    
    query = query.strip()
    
    # Check length
    if len(query) > 200:
        raise ValidationError(
            "Search query is too long",
            "Please use shorter search terms (maximum 200 characters)",
            "query"
        )
    
    # Sanitize the query
    try:
        sanitized = sanitize_search_query(query)
        if not sanitized:
            raise ValidationError(
                "Search query contains only invalid characters",
                "Please use letters, numbers, and basic punctuation",
                "query"
            )
    except Exception as e:
        logger.error(f"Query sanitization failed for '{query}': {e}")
        raise ValidationError(
            "Unable to process search query",
            "Please try simpler search terms",
            "query"
        )
    
    return sanitized


def validate_search_limit(limit: int) -> int:
    """
    Validate search result limit.
    
    Args:
        limit: Maximum number of results to return
        
    Returns:
        Validated limit value
        
    Raises:
        ValidationError: If limit is invalid
    """
    if not isinstance(limit, int):
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            raise ValidationError(
                "Search limit must be a number",
                "Please use a number between 1 and 50",
                "limit"
            )
    
    if limit < 1:
        raise ValidationError(
            "Search limit must be at least 1",
            "Please use a number between 1 and 50",
            "limit"
        )
    
    if limit > 50:
        raise ValidationError(
            "Search limit cannot exceed 50",
            "Please use a number between 1 and 50 for better performance",
            "limit"
        )
    
    return limit


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query to prevent FTS5 injection and ensure valid syntax.
    
    Args:
        query: Raw search query
        
    Returns:
        Sanitized query safe for FTS5
    """
    if not query or not query.strip():
        return ""
    
    # Remove potentially dangerous characters but preserve search functionality
    query = query.strip()
    
    # Handle quoted phrases (preserve them)
    quoted_phrases = re.findall(r'"([^"]*)"', query)
    
    # Remove quotes temporarily and clean the rest
    query_without_quotes = re.sub(r'"[^"]*"', "QUOTED_PHRASE", query)
    
    # Remove dangerous FTS5 characters while preserving search functionality
    # Keep: letters, numbers, spaces, basic punctuation, boolean operators
    # Remove: &, ;, <, >, |, *, +, -, =, etc. that could be dangerous
    query_without_quotes = re.sub(r'[&;|<>=+*\\]', ' ', query_without_quotes)
    
    # Keep safe punctuation and boolean operators
    query_without_quotes = re.sub(r'[^\w\s\-\.\,\!\?\:\;\(\)\'\"ANDORNOT]', ' ', query_without_quotes)
    
    # Restore quoted phrases
    for phrase in quoted_phrases:
        # Clean the phrase content (remove dangerous chars from inside quotes too)
        clean_phrase = re.sub(r'[&;|<>=+*\\]', ' ', phrase)
        clean_phrase = re.sub(r'[^\w\s\-\.\,\!\?\:\;\(\)\'\"ANDORNOT]', ' ', clean_phrase)
        query_without_quotes = query_without_quotes.replace("QUOTED_PHRASE", f'"{clean_phrase}"', 1)
    
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query_without_quotes).strip()
    
    # Ensure query is not empty after sanitization
    if not query or query.isspace():
        return ""
    
    return query


def get_validation_suggestions(error_type: str, context: Dict = None) -> List[str]:
    """
    Get helpful validation suggestions based on error type.
    
    Args:
        error_type: Type of validation error
        context: Additional context for suggestions
        
    Returns:
        List of helpful suggestions
    """
    suggestions = {
        "reference_format": [
            "Use format: 'Book Chapter:Verse' (e.g., 'John 3:16')",
            "For ranges: 'Book Chapter:StartVerse-EndVerse' (e.g., 'Romans 8:28-30')",
            "Book names can be abbreviated (e.g., 'Gen', 'Matt', 'Rev')",
            "Examples: 'Genesis 1:1', 'Ps 23:1', '1 Cor 13:4-7'"
        ],
        "search_query": [
            "Use simple words: 'love', 'faith', 'hope'",
            "Use phrases in quotes: \"love one another\"",
            "Use boolean operators: 'love AND peace', 'joy OR happiness'",
            "Examples: 'salvation', 'eternal life', \"fear not\""
        ],
        "translation": [
            "Common translations: KJV, WEB, TR, WH, BYZ",
            "Use uppercase format: 'KJV' not 'kjv'",
            "Check available translations in error message"
        ]
    }
    
    return suggestions.get(error_type, ["Please check your input format"])


# Helper functions
def _get_reference_format_suggestion(reference: str) -> str:
    """Get specific suggestion based on reference format issues."""
    reference = reference.lower()
    
    if not any(char.isdigit() for char in reference):
        return "Biblical references need chapter and verse numbers (e.g., 'John 3:16')"
    
    if ':' not in reference:
        return "Use colon to separate chapter and verse (e.g., 'John 3:16')"
    
    if reference.count(':') > 1:
        return "Use only one colon between chapter and verse (e.g., 'John 3:16')"
    
    # Check for common book name issues
    words = reference.split()
    if len(words) == 0:
        return "Please include a book name (e.g., 'John', 'Genesis', 'Romans')"
    
    first_word = words[0]
    if first_word.isdigit():
        return "Start with book name, not chapter number (e.g., 'John 3:16' not '3:16')"
    
    return "Please use format: 'Book Chapter:Verse' (e.g., 'John 3:16', 'Romans 8:28-30')"


async def _validate_reference_against_database(parsed_ref) -> None:
    """Validate parsed reference against database constraints."""
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            # Check if book exists
            cursor = await conn.execute(
                "SELECT name FROM books WHERE id = ?",
                (parsed_ref.book_id,)
            )
            book_row = await cursor.fetchone()
            
            if not book_row:
                raise ValidationError(
                    f"Book '{parsed_ref.book_id}' not found",
                    "Please check the book name spelling or use a different abbreviation",
                    "reference"
                )
            
            book_name = book_row[0]
            
            # Check if chapter/verse exists in database
            cursor = await conn.execute(
                "SELECT MAX(chapter), MAX(verse) FROM verses WHERE book_id = ? GROUP BY book_id",
                (parsed_ref.book_id,)
            )
            ranges_row = await cursor.fetchone()
            
            if ranges_row:
                max_chapter, max_verse_in_db = ranges_row
                
                if parsed_ref.chapter > max_chapter:
                    raise ValidationError(
                        f"{book_name} only has {max_chapter} chapters",
                        f"Please use a chapter number between 1 and {max_chapter}",
                        "reference"
                    )
                
                # For verse validation, we'd need to check per chapter
                # For now, just do a basic sanity check
                if parsed_ref.verse > 200:  # No biblical chapter has more than ~200 verses
                    raise ValidationError(
                        f"Verse number {parsed_ref.verse} seems too high",
                        f"Please check the verse number for {book_name} {parsed_ref.chapter}",
                        "reference"
                    )
            
    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Database reference validation failed: {e}")
        # Don't fail validation for database issues - just log and continue
        pass