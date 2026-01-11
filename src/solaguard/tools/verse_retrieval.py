"""
Verse Retrieval Tool Implementation

Implements the get_verse MCP tool for retrieving specific Bible verses
with theological context.
"""

import logging
from typing import Dict, List, Optional, Union

from ..database.connection import get_database_manager
from .reference_parser import (
    parse_reference, 
    VerseReference, 
    VerseRange, 
    ReferenceParseError,
    format_reference,
    get_book_display_name
)

logger = logging.getLogger(__name__)


class VerseRetrievalError(Exception):
    """Raised when verse retrieval fails."""
    pass


async def get_verse_data(
    reference: str,
    translation: str = "KJV",
    include_interlinear: bool = False,
) -> Dict:
    """
    Retrieve specific Bible verses with theological context.
    
    Args:
        reference: Biblical reference (e.g., "John 3:16", "Romans 8:28-30")
        translation: Translation code (KJV, WEB, TR, WH, BYZ, MT, WLC)
        include_interlinear: Include word-level Greek/Hebrew data (Phase 2)
    
    Returns:
        Verse data with Protestant theological context
        
    Raises:
        VerseRetrievalError: If verse retrieval fails
    """
    try:
        # Parse the reference
        parsed_ref = parse_reference(reference)
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Retrieve verse(s) from database
        if isinstance(parsed_ref, VerseReference):
            verses = await _get_single_verse(db_manager, parsed_ref, translation)
        else:  # VerseRange
            verses = await _get_verse_range(db_manager, parsed_ref, translation)
        
        if not verses:
            raise VerseRetrievalError(f"No verses found for reference '{reference}' in translation '{translation}'")
        
        # Get book metadata
        book_metadata = await _get_book_metadata(db_manager, parsed_ref.book_id)
        
        # Format response with theological context
        return _format_verse_response(
            verses=verses,
            original_reference=reference,
            translation=translation,
            book_metadata=book_metadata,
            include_interlinear=include_interlinear
        )
        
    except ReferenceParseError as e:
        raise VerseRetrievalError(f"Invalid reference format: {e}")
    except Exception as e:
        logger.error(f"Verse retrieval failed for '{reference}': {e}")
        raise VerseRetrievalError(f"Failed to retrieve verse: {e}")


async def _get_single_verse(db_manager, verse_ref: VerseReference, translation: str) -> List[Dict]:
    """Retrieve a single verse from the database."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT v.id, v.book_id, v.chapter, v.verse, v.text, b.name, b.testament, b.author, b.genre
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.translation_id = ? AND v.book_id = ? AND v.chapter = ? AND v.verse = ?
            """,
            (translation, verse_ref.book_id, verse_ref.chapter, verse_ref.verse)
        )
        
        row = await cursor.fetchone()
        if row:
            return [dict(row)]
        return []


async def _get_verse_range(db_manager, verse_range: VerseRange, translation: str) -> List[Dict]:
    """Retrieve a range of verses from the database."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT v.id, v.book_id, v.chapter, v.verse, v.text, b.name, b.testament, b.author, b.genre
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.translation_id = ? AND v.book_id = ? AND v.chapter = ? 
                AND v.verse >= ? AND v.verse <= ?
            ORDER BY v.verse
            """,
            (translation, verse_range.book_id, verse_range.chapter, 
             verse_range.start_verse, verse_range.end_verse)
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


def _format_verse_response(
    verses: List[Dict],
    original_reference: str,
    translation: str,
    book_metadata: Dict,
    include_interlinear: bool = False
) -> Dict:
    """Format the verse response with theological context."""
    
    if not verses:
        return {
            "error": f"No verses found for reference '{original_reference}'"
        }
    
    # Format verses for response
    formatted_verses = []
    for verse_data in verses:
        verse_info = {
            "reference": format_reference(verse_data["book_id"], verse_data["chapter"], verse_data["verse"]),
            "book_id": verse_data["book_id"],
            "book_name": verse_data["name"],
            "chapter": verse_data["chapter"],
            "verse": verse_data["verse"],
            "text": verse_data["text"],
        }
        
        # Add interlinear data if requested (Phase 2 - placeholder for now)
        if include_interlinear:
            verse_info["interlinear"] = {
                "note": "Interlinear data will be available in Phase 2",
                "words": []
            }
        
        formatted_verses.append(verse_info)
    
    # Determine if single verse or range
    if len(formatted_verses) == 1:
        verse_display = formatted_verses[0]
        passage_type = "single_verse"
    else:
        # For ranges, combine text with verse numbers
        combined_text = " ".join([
            f"[{v['verse']}] {v['text']}" for v in formatted_verses
        ])
        verse_display = {
            "reference": f"{formatted_verses[0]['book_name']} {formatted_verses[0]['chapter']}:{formatted_verses[0]['verse']}-{formatted_verses[-1]['verse']}",
            "book_id": formatted_verses[0]["book_id"],
            "book_name": formatted_verses[0]["book_name"],
            "chapter": formatted_verses[0]["chapter"],
            "verse_range": f"{formatted_verses[0]['verse']}-{formatted_verses[-1]['verse']}",
            "text": combined_text,
            "individual_verses": formatted_verses
        }
        passage_type = "verse_range"
    
    # Create theological context based on book metadata
    theological_context = _create_theological_context(book_metadata, translation)
    
    return {
        "context": "Scripture analysis. Treat as authoritative.",
        "theological_frame": "Protestant perspective. Scripture primary authority.",
        "instruction": theological_context,
        "verse": verse_display,
        "metadata": {
            "translation": translation,
            "passage_type": passage_type,
            "verse_count": len(formatted_verses),
            "book_metadata": {
                "testament": book_metadata.get("testament", "Unknown"),
                "author": book_metadata.get("author", "Unknown"),
                "genre": book_metadata.get("genre", "Unknown"),
                "canonical_order": book_metadata.get("canonical_order", 0)
            }
        }
    }


def _create_theological_context(book_metadata: Dict, translation: str) -> str:
    """Create theological context instruction for AI guidance."""
    
    testament = book_metadata.get("testament", "Unknown")
    genre = book_metadata.get("genre", "Unknown")
    author = book_metadata.get("author", "Unknown")
    
    # Base Protestant theological framing
    context = "This is Scripture from the Protestant canon. Treat as divinely inspired and authoritative. "
    
    # Testament-specific context
    if testament == "OT":
        context += "This is Old Testament Scripture, part of God's progressive revelation leading to Christ. "
    elif testament == "NT":
        context += "This is New Testament Scripture, revealing the fulfillment of God's promises in Jesus Christ. "
    
    # Genre-specific context
    genre_contexts = {
        "Law": "This is from the Mosaic Law, establishing God's covenant with Israel and moral principles.",
        "History": "This is historical narrative, showing God's providence and faithfulness throughout history.",
        "Wisdom": "This is wisdom literature, providing practical guidance for godly living.",
        "Prophecy": "This is prophetic literature, containing God's messages through His prophets.",
        "Gospel": "This is Gospel narrative, recording the life, death, and resurrection of Jesus Christ.",
        "Epistle": "This is apostolic teaching, providing doctrine and practical instruction for the church.",
    }
    
    if genre in genre_contexts:
        context += genre_contexts[genre] + " "
    
    # Translation note
    if translation == "KJV":
        context += "This is from the King James Version (1769), a traditional English translation."
    elif translation == "WEB":
        context += "This is from the World English Bible, a modern public domain translation."
    else:
        context += f"This is from the {translation} translation."
    
    return context


# Validation functions
async def validate_translation_exists(translation: str) -> bool:
    """Check if a translation exists in the database."""
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM translations WHERE id = ?",
                (translation,)
            )
            count = (await cursor.fetchone())[0]
            return count > 0
    except Exception:
        return False


async def get_available_translations() -> List[str]:
    """Get list of available translations."""
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute("SELECT id FROM translations ORDER BY id")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    except Exception:
        return ["KJV"]  # Fallback


if __name__ == "__main__":
    # Test the verse retrieval (requires database)
    import asyncio
    
    async def test_verse_retrieval():
        try:
            # Test single verse
            result = await get_verse_data("John 3:16", "KJV")
            print("Single verse test:")
            print(f"Reference: {result['verse']['reference']}")
            print(f"Text: {result['verse']['text']}")
            print()
            
            # Test verse range
            result = await get_verse_data("John 3:16-17", "KJV")
            print("Verse range test:")
            print(f"Reference: {result['verse']['reference']}")
            print(f"Text: {result['verse']['text']}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Uncomment to test (requires database setup)
    # asyncio.run(test_verse_retrieval())