"""
Verse Retrieval Tool Implementation

Implements the get_verse MCP tool for retrieving specific Bible verses
with theological context.
"""

import logging
from typing import Dict, List, Optional, Union

from ..database.connection import get_database_manager
from ..context import wrap_verse_response, wrap_error_response, ContextType
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
    include_definitions: bool = False,
) -> Dict:
    """
    Retrieve specific Bible verses with theological context.
    
    Args:
        reference: Biblical reference (e.g., "John 3:16", "Romans 8:28-30")
        translation: Translation code (KJV, WEB, TR, WH, BYZ, MT, WLC)
        include_interlinear: Include word-level Greek/Hebrew data with Strong's numbers
        include_definitions: Include Strong's definitions for each word (only with interlinear)
    
    Returns:
        Verse data with Protestant theological context
        
    Raises:
        VerseRetrievalError: If verse retrieval fails
    """
    try:
        # Parse the reference (validation handled at server level)
        parsed_ref = parse_reference(reference)
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Retrieve verse(s) from database
        if isinstance(parsed_ref, VerseReference):
            verses = await _get_single_verse(db_manager, parsed_ref, translation)
        else:  # VerseRange
            verses = await _get_verse_range(db_manager, parsed_ref, translation)
        
        if not verses:
            return wrap_error_response(
                f"No verses found for reference '{reference}' in {translation}",
                "The reference exists but no verse text is available in this translation",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Fetch interlinear data if requested
        if include_interlinear:
            for verse in verses:
                interlinear_words = await _get_interlinear_data(
                    db_manager, 
                    verse["id"],
                    include_definitions=include_definitions
                )
                verse["interlinear_words"] = interlinear_words
        
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
        return wrap_error_response(
            f"Invalid reference format: {e}",
            "Please use format like 'John 3:16' or 'Romans 8:28-30'",
            ContextType.VERSE_RETRIEVAL
        )
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


async def _get_interlinear_data(db_manager, verse_id: int, include_definitions: bool = False) -> List[Dict]:
    """Retrieve word-level interlinear data for a verse."""
    async with db_manager.get_connection() as conn:
        # Build query based on whether definitions are needed
        if include_definitions:
            query = """
                SELECT 
                    w.sequence,
                    w.text,
                    w.normalized,
                    w.strongs,
                    w.morphology,
                    w.english_equiv,
                    COALESCE(w.transliteration, sd.transliteration) as transliteration,
                    sd.word as original_word,
                    sd.pronunciation,
                    sd.definition,
                    sd.part_of_speech
                FROM words w
                LEFT JOIN strongs_dictionary sd ON w.strongs = sd.number
                WHERE w.verse_id = ?
                ORDER BY w.sequence
            """
        else:
            query = """
                SELECT 
                    w.sequence,
                    w.text,
                    w.normalized,
                    w.strongs,
                    w.morphology,
                    w.english_equiv,
                    COALESCE(w.transliteration, sd.transliteration) as transliteration,
                    sd.word as original_word,
                    sd.pronunciation
                FROM words w
                LEFT JOIN strongs_dictionary sd ON w.strongs = sd.number
                WHERE w.verse_id = ?
                ORDER BY w.sequence
            """
        
        cursor = await conn.execute(query, (verse_id,))
        
        rows = await cursor.fetchall()
        words = []
        for row in rows:
            word_data = {
                "sequence": row[0],
                "text": row[1],
                "english": row[5] if row[5] else row[1],  # Use english_equiv or fallback to text
            }
            
            # Add optional fields only if they exist
            if row[3]:  # strongs
                word_data["strongs"] = row[3]
            if row[6]:  # transliteration (from join or words table)
                word_data["transliteration"] = row[6]
            if row[7]:  # original_word (Hebrew/Greek from Strong's)
                word_data["original"] = row[7]
            if row[8]:  # pronunciation
                word_data["pronunciation"] = row[8]
            
            # Add definition and part of speech if requested and available
            if include_definitions and len(row) > 9:
                if row[9]:  # definition
                    word_data["definition"] = row[9]
                if row[10]:  # part_of_speech
                    word_data["part_of_speech"] = row[10]
            
            if row[2]:  # normalized
                word_data["normalized"] = row[2]
            if row[4]:  # morphology
                word_data["morphology"] = row[4]
            
            words.append(word_data)
        
        return words


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
        return wrap_error_response(
            f"No verses found for reference '{original_reference}'",
            "Please check your reference format (e.g., 'John 3:16', 'Romans 8:28-30')",
            ContextType.VERSE_RETRIEVAL
        )
    
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
        
        # Add interlinear data if requested and available
        if include_interlinear and "interlinear_words" in verse_data:
            if verse_data["interlinear_words"]:
                verse_info["interlinear"] = {
                    "available": True,
                    "word_count": len(verse_data["interlinear_words"]),
                    "words": verse_data["interlinear_words"]
                }
            else:
                verse_info["interlinear"] = {
                    "available": False,
                    "note": "Interlinear data not available for this verse"
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
    
    # Prepare response data
    response_data = {
        "verse": verse_display,
        "metadata": {
            "translation": translation,
            "passage_type": passage_type,
            "verse_count": len(formatted_verses),
            "interlinear_included": include_interlinear,
            "book_metadata": {
                "testament": book_metadata.get("testament", "Unknown"),
                "author": book_metadata.get("author", "Unknown"),
                "genre": book_metadata.get("genre", "Unknown"),
                "canonical_order": book_metadata.get("canonical_order", 0)
            }
        }
    }
    
    # Wrap with centralized theological context
    return wrap_verse_response(
        response_data,
        testament=book_metadata.get("testament", "Unknown"),
        genre=book_metadata.get("genre", "Unknown"),
        book_name=book_metadata.get("name", "Unknown"),
        author=book_metadata.get("author")
    )


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