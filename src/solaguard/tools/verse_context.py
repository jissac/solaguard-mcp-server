"""
Verse Context Tool Implementation

Implements the get_verse_context MCP tool for retrieving verses with
surrounding context to aid interpretation.
"""

import logging
from typing import Dict, List, Optional

from ..database.connection import get_database_manager
from ..context import wrap_verse_response, wrap_error_response, ContextType
from .reference_parser import (
    parse_reference, 
    VerseReference, 
    VerseRange,
    ReferenceParseError,
    format_reference
)

logger = logging.getLogger(__name__)


class VerseContextError(Exception):
    """Raised when verse context retrieval fails."""
    pass


async def get_verse_context_data(
    reference: str,
    before: int = 2,
    after: int = 2,
    translation: str = "KJV"
) -> Dict:
    """
    Get a verse with surrounding context for better interpretation.
    
    Args:
        reference: Verse reference (e.g., "John 3:16")
        before: Number of verses before (default: 2, max: 10)
        after: Number of verses after (default: 2, max: 10)
        translation: Bible translation (default: KJV)
    
    Returns:
        The requested verse plus surrounding verses for context.
        Target verse is marked with 'is_target': True
        
    Raises:
        VerseContextError: If context retrieval fails
    """
    try:
        # Validate parameters
        before = max(0, min(before, 10))  # Clamp 0-10
        after = max(0, min(after, 10))    # Clamp 0-10
        
        # Parse the reference - must be a single verse
        parsed_ref = parse_reference(reference)
        
        if isinstance(parsed_ref, VerseRange):
            return wrap_error_response(
                "get_verse_context requires a single verse reference, not a range",
                f"Use 'John 3:16' instead of '{reference}'. For ranges, use get_verse()",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Calculate context range
        start_verse = max(1, parsed_ref.verse - before)
        end_verse = parsed_ref.verse + after
        
        # Check chapter boundaries
        chapter_info = await _get_chapter_info(
            db_manager, 
            parsed_ref.book_id, 
            parsed_ref.chapter,
            translation
        )
        
        if not chapter_info:
            return wrap_error_response(
                f"Chapter not found: {parsed_ref.book_id} {parsed_ref.chapter}",
                "Please check your reference",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Adjust end_verse to not exceed chapter
        end_verse = min(end_verse, chapter_info['max_verse'])
        
        # Retrieve verses
        verses = await _get_verse_range_with_metadata(
            db_manager,
            parsed_ref.book_id,
            parsed_ref.chapter,
            start_verse,
            end_verse,
            translation
        )
        
        if not verses:
            return wrap_error_response(
                f"No verses found for reference '{reference}' in {translation}",
                "The reference exists but no verse text is available in this translation",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Mark the target verse
        target_found = False
        for verse in verses:
            if verse['verse'] == parsed_ref.verse:
                verse['is_target'] = True
                target_found = True
            else:
                verse['is_target'] = False
        
        if not target_found:
            return wrap_error_response(
                f"Target verse {reference} not found in database",
                "The verse may not exist in this translation",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Get book metadata
        book_metadata = await _get_book_metadata(db_manager, parsed_ref.book_id)
        
        # Format response
        return _format_context_response(
            verses=verses,
            target_reference=reference,
            context_range=f"{parsed_ref.book_id} {parsed_ref.chapter}:{start_verse}-{end_verse}",
            translation=translation,
            book_metadata=book_metadata,
            at_chapter_start=(start_verse == 1),
            at_chapter_end=(end_verse == chapter_info['max_verse'])
        )
        
    except ReferenceParseError as e:
        return wrap_error_response(
            f"Invalid reference format: {e}",
            "Please use format like 'John 3:16' (single verse only)",
            ContextType.VERSE_RETRIEVAL
        )
    except Exception as e:
        logger.error(f"Verse context retrieval failed for '{reference}': {e}")
        raise VerseContextError(f"Failed to retrieve verse context: {e}")


async def _get_chapter_info(
    db_manager,
    book_id: str,
    chapter: int,
    translation: str
) -> Optional[Dict]:
    """Get information about a chapter (verse count, etc)."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT MIN(verse) as min_verse, MAX(verse) as max_verse, COUNT(*) as verse_count
            FROM verses
            WHERE book_id = ? AND chapter = ? AND translation_id = ?
            """,
            (book_id, chapter, translation)
        )
        
        row = await cursor.fetchone()
        if row and row['verse_count'] > 0:
            return dict(row)
        return None


async def _get_verse_range_with_metadata(
    db_manager,
    book_id: str,
    chapter: int,
    start_verse: int,
    end_verse: int,
    translation: str
) -> List[Dict]:
    """Retrieve a range of verses with book metadata."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT 
                v.id, v.book_id, v.chapter, v.verse, v.text,
                b.name, b.testament, b.author, b.genre
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.translation_id = ? 
                AND v.book_id = ? 
                AND v.chapter = ? 
                AND v.verse >= ? 
                AND v.verse <= ?
            ORDER BY v.verse
            """,
            (translation, book_id, chapter, start_verse, end_verse)
        )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def _get_book_metadata(db_manager, book_id: str) -> Dict:
    """Get metadata for a book."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT id, name, testament, author, genre, canonical_order
            FROM books
            WHERE id = ?
            """,
            (book_id,)
        )
        
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return {}


def _format_context_response(
    verses: List[Dict],
    target_reference: str,
    context_range: str,
    translation: str,
    book_metadata: Dict,
    at_chapter_start: bool,
    at_chapter_end: bool
) -> Dict:
    """Format the verse context response."""
    
    # Format verses for response
    formatted_verses = []
    target_verse_data = None
    
    for verse_data in verses:
        verse_info = {
            "reference": format_reference(
                verse_data["book_id"], 
                verse_data["chapter"], 
                verse_data["verse"]
            ),
            "book_id": verse_data["book_id"],
            "book_name": verse_data["name"],
            "chapter": verse_data["chapter"],
            "verse": verse_data["verse"],
            "text": verse_data["text"],
            "is_target": verse_data.get("is_target", False)
        }
        
        if verse_info["is_target"]:
            target_verse_data = verse_info
        
        formatted_verses.append(verse_info)
    
    # Build context notes
    context_notes = []
    if at_chapter_start:
        context_notes.append("Context starts at beginning of chapter")
    if at_chapter_end:
        context_notes.append("Context extends to end of chapter")
    
    # Prepare response data
    response_data = {
        "target_verse": target_verse_data,
        "context_verses": formatted_verses,
        "metadata": {
            "target_reference": target_reference,
            "context_range": context_range,
            "translation": translation,
            "verse_count": len(formatted_verses),
            "context_notes": context_notes if context_notes else None,
            "book_metadata": {
                "testament": book_metadata.get("testament", "Unknown"),
                "author": book_metadata.get("author", "Unknown"),
                "genre": book_metadata.get("genre", "Unknown"),
                "canonical_order": book_metadata.get("canonical_order", 0)
            }
        },
        "interpretation_note": "Reading verses in context helps prevent misinterpretation. The target verse is marked with 'is_target': true"
    }
    
    # Wrap with centralized theological context
    return wrap_verse_response(
        response_data,
        testament=book_metadata.get("testament", "Unknown"),
        genre=book_metadata.get("genre", "Unknown"),
        book_name=book_metadata.get("name", "Unknown"),
        author=book_metadata.get("author")
    )
