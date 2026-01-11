"""
SolaGuard Theological Context Engine

This package provides the theological context framework that automatically
injects Protestant theological framing into all MCP tool responses.
"""

from .theological import (
    ContextType,
    Testament,
    Genre,
    get_base_context,
    create_verse_theological_context,
    create_search_theological_context,
    create_error_context,
    wrap_response_with_context,
    wrap_verse_response,
    wrap_search_response,
    wrap_error_response,
)

__all__ = [
    "ContextType",
    "Testament", 
    "Genre",
    "get_base_context",
    "create_verse_theological_context",
    "create_search_theological_context",
    "create_error_context",
    "wrap_response_with_context",
    "wrap_verse_response",
    "wrap_search_response",
    "wrap_error_response",
]