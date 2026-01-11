"""
Theological Context Engine

Provides centralized Protestant theological framing for all MCP tool responses.
Ensures consistent biblical worldview guidance across all tools.
"""

from typing import Dict, List, Optional
from enum import Enum


class ContextType(Enum):
    """Types of theological contexts for different tool responses."""
    VERSE_RETRIEVAL = "verse_retrieval"
    SCRIPTURE_SEARCH = "scripture_search"
    ERROR_RESPONSE = "error_response"


class Testament(Enum):
    """Biblical testament classifications."""
    OLD_TESTAMENT = "OT"
    NEW_TESTAMENT = "NT"


class Genre(Enum):
    """Biblical genre classifications."""
    LAW = "Law"
    HISTORY = "History"
    WISDOM = "Wisdom"
    PROPHECY = "Prophecy"
    GOSPEL = "Gospel"
    EPISTLE = "Epistle"


def get_base_context(context_type: ContextType) -> Dict[str, str]:
    """
    Get base theological context for different tool types.
    
    Args:
        context_type: Type of context needed
        
    Returns:
        Dictionary with base context and theological frame
    """
    base_contexts = {
        ContextType.VERSE_RETRIEVAL: {
            "context": "Scripture analysis. Treat as authoritative.",
            "theological_frame": "Protestant perspective. Scripture primary authority."
        },
        ContextType.SCRIPTURE_SEARCH: {
            "context": "Biblical search. Scripture authority.",
            "theological_frame": "Protestant perspective. Scripture primary authority."
        },
        ContextType.ERROR_RESPONSE: {
            "context": "Scripture analysis. Treat as authoritative.",
            "theological_frame": "Protestant perspective. Scripture primary authority."
        }
    }
    
    return base_contexts.get(context_type, base_contexts[ContextType.ERROR_RESPONSE])


def create_verse_theological_context(
    testament: str,
    genre: str,
    book_name: str,
    author: Optional[str] = None
) -> str:
    """
    Create theological context instruction for verse retrieval.
    
    Args:
        testament: Testament classification (OT/NT)
        genre: Genre classification
        book_name: Name of the biblical book
        author: Author of the book (optional)
        
    Returns:
        Theological context instruction string
    """
    # Base Protestant theological framing
    context = "This is Scripture from the Protestant canon. Treat as divinely inspired and authoritative. "
    
    # Testament-specific context
    if testament == Testament.OLD_TESTAMENT.value:
        context += "This is Old Testament Scripture, part of God's progressive revelation leading to Christ. "
    elif testament == Testament.NEW_TESTAMENT.value:
        context += "This is New Testament Scripture, revealing the fulfillment of God's promises in Jesus Christ. "
    
    # Genre-specific context
    genre_contexts = {
        Genre.LAW.value: f"The book of {book_name} contains divine law and covenant principles that establish God's relationship with His people.",
        Genre.HISTORY.value: f"The book of {book_name} records historical events showing God's providence and faithfulness throughout history.",
        Genre.WISDOM.value: f"The book of {book_name} provides practical wisdom for godly living and understanding God's ways.",
        Genre.PROPHECY.value: f"The book of {book_name} contains prophetic messages revealing God's will and future plans.",
        Genre.GOSPEL.value: f"The Gospel of {book_name} records the life, death, and resurrection of Jesus Christ, the Son of God.",
        Genre.EPISTLE.value: f"The epistle of {book_name} provides apostolic teaching and doctrine for the church."
    }
    
    if genre in genre_contexts:
        context += f" {genre_contexts[genre]}"
    
    # Author context (if available)
    if author and author != "Unknown":
        context += f" Written by {author} under divine inspiration."
    
    context += " Apply these truths with reverence for God's Word."
    
    return context


def create_search_theological_context(
    query: str,
    total_results: int,
    books_found: List[Dict],
    testament_distribution: Dict[str, int],
    genre_distribution: Dict[str, int],
    translation: str
) -> str:
    """
    Create theological context instruction for search results.
    
    Args:
        query: Search query
        total_results: Total number of results
        books_found: List of books found in results
        testament_distribution: Distribution across testaments
        genre_distribution: Distribution across genres
        translation: Translation used
        
    Returns:
        Theological context instruction string
    """
    context = f"Search results for '{query}' in {translation} translation. "
    
    if total_results == 0:
        context += "No verses found matching this query. Consider broader search terms or check spelling."
        return context
    
    context += f"Found {total_results} verse(s) across {len(books_found)} book(s). "
    
    # Testament distribution context
    ot_count = testament_distribution.get(Testament.OLD_TESTAMENT.value, 0)
    nt_count = testament_distribution.get(Testament.NEW_TESTAMENT.value, 0)
    
    if ot_count > 0 and nt_count > 0:
        context += f"Results span both Old Testament ({ot_count}) and New Testament ({nt_count}), showing the continuity of Scripture. "
    elif ot_count > 0:
        context += f"All results from Old Testament ({ot_count}), representing God's covenant with Israel and preparation for Christ. "
    elif nt_count > 0:
        context += f"All results from New Testament ({nt_count}), representing the fulfillment of God's promises in Jesus Christ. "
    
    # Genre distribution context
    genres = list(genre_distribution.keys())
    if len(genres) > 1:
        context += f"Results include {', '.join(genres)} literature, providing diverse biblical perspectives. "
    elif len(genres) == 1:
        genre = genres[0]
        genre_contexts = {
            Genre.LAW.value: "from the Mosaic Law, establishing God's covenant principles.",
            Genre.HISTORY.value: "from historical narrative, showing God's providence.",
            Genre.WISDOM.value: "from wisdom literature, providing practical godly guidance.",
            Genre.PROPHECY.value: "from prophetic literature, containing God's messages.",
            Genre.GOSPEL.value: "from Gospel accounts, recording Christ's life and ministry.",
            Genre.EPISTLE.value: "from apostolic teaching, providing church doctrine and instruction.",
        }
        if genre in genre_contexts:
            context += f"All results are {genre_contexts[genre]} "
    
    context += "Treat these verses as divinely inspired Scripture with full authority for doctrine and practice."
    
    return context


def create_error_context(error_type: str, suggestion: str) -> Dict[str, str]:
    """
    Create theological context for error responses.
    
    Args:
        error_type: Type of error (verse_retrieval, search, etc.)
        suggestion: Helpful suggestion for the user
        
    Returns:
        Dictionary with error context
    """
    base = get_base_context(ContextType.ERROR_RESPONSE)
    
    return {
        **base,
        "suggestion": suggestion
    }


def wrap_response_with_context(
    response_data: Dict,
    context_type: ContextType,
    **context_kwargs
) -> Dict:
    """
    Wrap a response with appropriate theological context.
    
    Args:
        response_data: The main response data
        context_type: Type of context to apply
        **context_kwargs: Additional context parameters
        
    Returns:
        Response wrapped with theological context
    """
    base_context = get_base_context(context_type)
    
    # Create instruction based on context type
    if context_type == ContextType.VERSE_RETRIEVAL:
        instruction = create_verse_theological_context(
            testament=context_kwargs.get("testament", ""),
            genre=context_kwargs.get("genre", ""),
            book_name=context_kwargs.get("book_name", ""),
            author=context_kwargs.get("author")
        )
    elif context_type == ContextType.SCRIPTURE_SEARCH:
        instruction = create_search_theological_context(
            query=context_kwargs.get("query", ""),
            total_results=context_kwargs.get("total_results", 0),
            books_found=context_kwargs.get("books_found", []),
            testament_distribution=context_kwargs.get("testament_distribution", {}),
            genre_distribution=context_kwargs.get("genre_distribution", {}),
            translation=context_kwargs.get("translation", "")
        )
    else:
        instruction = "Apply biblical principles with reverence for Scripture."
    
    return {
        **base_context,
        "instruction": instruction,
        **response_data
    }


# Convenience functions for common use cases
def wrap_verse_response(response_data: Dict, testament: str, genre: str, book_name: str, author: Optional[str] = None) -> Dict:
    """Convenience function to wrap verse retrieval responses."""
    return wrap_response_with_context(
        response_data,
        ContextType.VERSE_RETRIEVAL,
        testament=testament,
        genre=genre,
        book_name=book_name,
        author=author
    )


def wrap_search_response(
    response_data: Dict,
    query: str,
    total_results: int,
    books_found: List[Dict],
    testament_distribution: Dict[str, int],
    genre_distribution: Dict[str, int],
    translation: str
) -> Dict:
    """Convenience function to wrap search responses."""
    return wrap_response_with_context(
        response_data,
        ContextType.SCRIPTURE_SEARCH,
        query=query,
        total_results=total_results,
        books_found=books_found,
        testament_distribution=testament_distribution,
        genre_distribution=genre_distribution,
        translation=translation
    )


def wrap_error_response(error_message: str, suggestion: str, context_type: ContextType = ContextType.ERROR_RESPONSE) -> Dict:
    """Convenience function to wrap error responses."""
    base_context = get_base_context(context_type)
    return {
        **base_context,
        "error": error_message,
        "suggestion": suggestion
    }