"""
SolaGuard Input Validation System

Provides centralized input validation for all MCP tools with consistent
error handling and helpful user feedback.
"""

from .validators import (
    ValidationError,
    validate_biblical_reference,
    validate_translation,
    validate_search_query,
    validate_search_limit,
    sanitize_search_query,
    get_validation_suggestions,
)

from .reference_validator import (
    ReferenceValidationError,
    validate_book_exists,
    validate_chapter_range,
    validate_verse_range,
    get_book_chapter_verse_ranges,
)

__all__ = [
    # Core validation
    "ValidationError",
    "validate_biblical_reference",
    "validate_translation", 
    "validate_search_query",
    "validate_search_limit",
    "sanitize_search_query",
    "get_validation_suggestions",
    
    # Reference validation
    "ReferenceValidationError",
    "validate_book_exists",
    "validate_chapter_range", 
    "validate_verse_range",
    "get_book_chapter_verse_ranges",
]