"""
Strong's Word Study Tool Implementation

Implements the get_strongs MCP tool for Hebrew and Greek word studies
using Strong's Concordance numbers with comprehensive verse occurrences.
"""

import logging
from typing import Dict, List, Optional, Tuple
import re

from ..database.connection import get_database_manager
from ..context import wrap_strongs_response, wrap_error_response, ContextType
from .reference_parser import format_reference

logger = logging.getLogger(__name__)


class StrongsStudyError(Exception):
    """Raised when Strong's word study fails."""
    pass


async def get_strongs_data(
    strongs_number: str,
    translation: str = "KJV",
    limit: int = 20,
) -> Dict:
    """
    Perform Hebrew or Greek word study using Strong's Concordance numbers.
    
    Args:
        strongs_number: Strong's number (e.g., "G25", "H157", "g25", "h157")
        translation: Translation to return verse results in (KJV, BSB, etc.)
        limit: Maximum number of verse occurrences to return (1-100)
    
    Returns:
        Strong's word study data with Protestant theological context
        
    Raises:
        StrongsStudyError: If Strong's word study fails
    """
    try:
        # Validate and normalize Strong's number
        normalized_strongs = _normalize_strongs_number(strongs_number)
        if not normalized_strongs:
            return wrap_error_response(
                f"Invalid Strong's number format: {strongs_number}",
                "Please use format like 'G25', 'H157', 'g25', or 'h157'",
                ContextType.STRONGS_STUDY
            )
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Get Strong's dictionary entry
        strongs_entry = await _get_strongs_entry(db_manager, normalized_strongs)
        if not strongs_entry:
            return wrap_error_response(
                f"Strong's number not found: {normalized_strongs}",
                f"Please check the Strong's number. We support G1-G5624 (Greek) and H1-H8674 (Hebrew)",
                ContextType.STRONGS_STUDY
            )
        
        # Get verse occurrences
        verse_occurrences = await _get_verse_occurrences(
            db_manager, normalized_strongs, translation, limit
        )
        
        # Get related Strong's numbers (cross-references)
        related_strongs = await _get_related_strongs(db_manager, normalized_strongs)
        
        # Get usage statistics
        usage_stats = await _get_usage_statistics(db_manager, normalized_strongs)
        
        # Format response with theological context
        return _format_strongs_response(
            strongs_entry=strongs_entry,
            verse_occurrences=verse_occurrences,
            related_strongs=related_strongs,
            usage_stats=usage_stats,
            original_number=strongs_number,
            translation=translation,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Strong's word study failed for '{strongs_number}': {e}")
        raise StrongsStudyError(f"Failed to perform word study: {e}")


def _normalize_strongs_number(strongs_number: str) -> Optional[str]:
    """
    Normalize Strong's number to standard format (G1234 or H1234).
    
    Args:
        strongs_number: Input Strong's number in various formats
        
    Returns:
        Normalized Strong's number or None if invalid
    """
    if not strongs_number:
        return None
    
    # Remove whitespace and convert to uppercase
    clean_number = strongs_number.strip().upper()
    
    # Check if already in correct format
    if re.match(r'^[GH]\d+$', clean_number):
        return clean_number
    
    # Try to extract number and language
    match = re.match(r'^([GH]?)(\d+)$', clean_number)
    if match:
        prefix, number = match.groups()
        
        # If no prefix, try to determine from number range
        if not prefix:
            num = int(number)
            if 1 <= num <= 5624:
                prefix = 'G'  # Greek range
            elif 1 <= num <= 8674:
                prefix = 'H'  # Hebrew range
            else:
                return None  # Out of range
        
        return f"{prefix}{number}"
    
    return None


async def _get_strongs_entry(db_manager, strongs_number: str) -> Optional[Dict]:
    """Get Strong's dictionary entry."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT number, word, transliteration, pronunciation, definition, 
                   part_of_speech, notes, theological_significance, language,
                   created_at, updated_at
            FROM strongs_dictionary
            WHERE number = ?
            """,
            (strongs_number,)
        )
        
        row = await cursor.fetchone()
        return dict(row) if row else None


async def _get_verse_occurrences(
    db_manager, strongs_number: str, translation: str, limit: int
) -> List[Dict]:
    """
    Get verse occurrences for a Strong's number in the requested translation.
    Uses translation-agnostic logic similar to cross-references.
    """
    async with db_manager.get_connection() as conn:
        # First get occurrences from the words table (linked to verses)
        cursor = await conn.execute(
            """
            SELECT DISTINCT w.verse_id, v.book_id, v.chapter, v.verse, 
                   b.name, b.testament, b.canonical_order,
                   w.text as word_text, w.english_equiv
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            JOIN books b ON v.book_id = b.id
            WHERE w.strongs = ? AND v.translation_id = 'KJV'
            ORDER BY b.canonical_order, v.chapter, v.verse
            LIMIT ?
            """,
            (strongs_number, limit * 2)  # Get more to account for translation misses
        )
        
        kjv_occurrences = await cursor.fetchall()
        
        # Now get the same verses in the requested translation
        translated_occurrences = []
        for occurrence in kjv_occurrences:
            # Get verse in requested translation
            cursor = await conn.execute(
                """
                SELECT v.text, v.translation_id
                FROM verses v
                WHERE v.book_id = ? AND v.chapter = ? AND v.verse = ? AND v.translation_id = ?
                """,
                (occurrence[1], occurrence[2], occurrence[3], translation)
            )
            
            translated_row = await cursor.fetchone()
            
            if translated_row:
                # Use translated version
                verse_text = translated_row[0]
                verse_translation = translated_row[1]
            else:
                # Fall back to KJV
                cursor = await conn.execute(
                    """
                    SELECT v.text, v.translation_id
                    FROM verses v
                    WHERE v.book_id = ? AND v.chapter = ? AND v.verse = ? AND v.translation_id = 'KJV'
                    """,
                    (occurrence[1], occurrence[2], occurrence[3])
                )
                kjv_row = await cursor.fetchone()
                verse_text = kjv_row[0] if kjv_row else "Text not available"
                verse_translation = "KJV"
            
            translated_occurrences.append({
                "verse_id": occurrence[0],
                "book_id": occurrence[1],
                "chapter": occurrence[2],
                "verse": occurrence[3],
                "book_name": occurrence[4],
                "testament": occurrence[5],
                "canonical_order": occurrence[6],
                "word_text": occurrence[7],
                "english_equiv": occurrence[8],
                "verse_text": verse_text,
                "translation": verse_translation
            })
            
            # Stop when we reach the requested limit
            if len(translated_occurrences) >= limit:
                break
        
        return translated_occurrences


async def _get_related_strongs(db_manager, strongs_number: str) -> List[Dict]:
    """Get related Strong's numbers via cross-references."""
    async with db_manager.get_connection() as conn:
        # Get related Strong's numbers from lexicon cross-references
        cursor = await conn.execute(
            """
            SELECT lcr.to_strongs, sd.word, sd.transliteration, sd.definition, lcr.context
            FROM lexicon_cross_references lcr
            JOIN strongs_dictionary sd ON lcr.to_strongs = sd.number
            WHERE lcr.from_strongs = ?
            ORDER BY sd.number
            LIMIT 10
            """,
            (strongs_number,)
        )
        
        related = await cursor.fetchall()
        return [dict(row) for row in related]


async def _get_usage_statistics(db_manager, strongs_number: str) -> Dict:
    """Get usage statistics for a Strong's number."""
    async with db_manager.get_connection() as conn:
        # Total occurrences
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM words WHERE strongs = ?",
            (strongs_number,)
        )
        total_occurrences = (await cursor.fetchone())[0]
        
        # Unique verses
        cursor = await conn.execute(
            "SELECT COUNT(DISTINCT verse_id) FROM words WHERE strongs = ?",
            (strongs_number,)
        )
        unique_verses = (await cursor.fetchone())[0]
        
        # Testament distribution
        cursor = await conn.execute(
            """
            SELECT b.testament, COUNT(DISTINCT w.verse_id) as verse_count
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            JOIN books b ON v.book_id = b.id
            WHERE w.strongs = ?
            GROUP BY b.testament
            """,
            (strongs_number,)
        )
        testament_dist = dict(await cursor.fetchall())
        
        # Book distribution (top 5)
        cursor = await conn.execute(
            """
            SELECT b.name, COUNT(DISTINCT w.verse_id) as verse_count
            FROM words w
            JOIN verses v ON w.verse_id = v.id
            JOIN books b ON v.book_id = b.id
            WHERE w.strongs = ?
            GROUP BY b.id, b.name
            ORDER BY verse_count DESC
            LIMIT 5
            """,
            (strongs_number,)
        )
        book_dist = await cursor.fetchall()
        
        return {
            "total_occurrences": total_occurrences,
            "unique_verses": unique_verses,
            "testament_distribution": testament_dist,
            "top_books": [{"book": row[0], "verses": row[1]} for row in book_dist]
        }


def _format_strongs_response(
    strongs_entry: Dict,
    verse_occurrences: List[Dict],
    related_strongs: List[Dict],
    usage_stats: Dict,
    original_number: str,
    translation: str,
    limit: int
) -> Dict:
    """Format the Strong's word study response with theological context."""
    
    # Format Strong's entry
    entry_info = {
        "strongs_number": strongs_entry["number"],
        "original_word": strongs_entry["word"],
        "transliteration": strongs_entry.get("transliteration", ""),
        "pronunciation": strongs_entry.get("pronunciation", ""),
        "definition": strongs_entry["definition"],
        "part_of_speech": strongs_entry.get("part_of_speech", ""),
        "language": strongs_entry.get("language", ""),
        "notes": strongs_entry.get("notes", ""),
        "theological_significance": strongs_entry.get("theological_significance", "")
    }
    
    # Format verse occurrences
    formatted_verses = []
    for occurrence in verse_occurrences:
        verse_info = {
            "reference": format_reference(occurrence["book_id"], occurrence["chapter"], occurrence["verse"]),
            "book_name": occurrence["book_name"],
            "testament": occurrence["testament"],
            "text": occurrence["verse_text"],
            "translation": occurrence["translation"],
            "word_in_verse": occurrence.get("word_text", ""),
            "english_equivalent": occurrence.get("english_equiv", "")
        }
        formatted_verses.append(verse_info)
    
    # Format related Strong's numbers
    formatted_related = []
    for related in related_strongs:
        related_info = {
            "strongs_number": related["to_strongs"],
            "word": related["word"],
            "transliteration": related.get("transliteration", ""),
            "definition": related["definition"][:100] + "..." if len(related["definition"]) > 100 else related["definition"],
            "relationship": related.get("context", "related")
        }
        formatted_related.append(related_info)
    
    # Determine language and testament context
    language = entry_info["language"]
    is_greek = language == "greek" or strongs_entry["number"].startswith("G")
    is_hebrew = language == "hebrew" or strongs_entry["number"].startswith("H")
    
    # Prepare response data
    response_data = {
        "strongs_entry": entry_info,
        "verse_occurrences": formatted_verses,
        "related_words": formatted_related,
        "usage_statistics": {
            "total_occurrences": usage_stats["total_occurrences"],
            "unique_verses": usage_stats["unique_verses"],
            "testament_distribution": usage_stats["testament_distribution"],
            "top_books": usage_stats["top_books"],
            "verses_shown": len(formatted_verses),
            "verses_available": usage_stats["unique_verses"]
        },
        "metadata": {
            "strongs_number": original_number,
            "language": "Greek" if is_greek else "Hebrew" if is_hebrew else "Unknown",
            "testament_focus": "New Testament" if is_greek else "Old Testament" if is_hebrew else "Both",
            "translation": translation,
            "limit_applied": limit
        }
    }
    
    # Wrap with centralized theological context
    return wrap_strongs_response(
        response_data,
        language="Greek" if is_greek else "Hebrew" if is_hebrew else "Unknown",
        strongs_number=strongs_entry["number"],
        word=strongs_entry["word"],
        occurrences=usage_stats["unique_verses"],
        translation=translation
    )


# Utility functions
async def search_strongs_by_word(word: str, language: str = "both") -> List[Dict]:
    """
    Search for Strong's numbers by original language word.
    
    Args:
        word: Original language word to search for
        language: "greek", "hebrew", or "both"
        
    Returns:
        List of matching Strong's entries
    """
    try:
        db_manager = get_database_manager()
        
        async with db_manager.get_connection() as conn:
            if language == "both":
                cursor = await conn.execute(
                    """
                    SELECT number, word, transliteration, definition, language
                    FROM strongs_dictionary
                    WHERE word LIKE ? OR transliteration LIKE ?
                    ORDER BY number
                    LIMIT 20
                    """,
                    (f"%{word}%", f"%{word}%")
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT number, word, transliteration, definition, language
                    FROM strongs_dictionary
                    WHERE (word LIKE ? OR transliteration LIKE ?) AND language = ?
                    ORDER BY number
                    LIMIT 20
                    """,
                    (f"%{word}%", f"%{word}%", language)
                )
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Strong's word search failed: {e}")
        return []


async def get_strongs_range_info(start_num: int, end_num: int, language: str) -> Dict:
    """Get information about a range of Strong's numbers."""
    try:
        db_manager = get_database_manager()
        prefix = "G" if language.lower() == "greek" else "H"
        
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT COUNT(*) as total, 
                       COUNT(CASE WHEN notes IS NOT NULL AND notes != '' THEN 1 END) as with_notes,
                       COUNT(CASE WHEN theological_significance IS NOT NULL AND theological_significance != '' THEN 1 END) as with_theology
                FROM strongs_dictionary
                WHERE number BETWEEN ? AND ?
                """,
                (f"{prefix}{start_num}", f"{prefix}{end_num}")
            )
            
            stats = dict(await cursor.fetchone())
            return {
                "range": f"{prefix}{start_num}-{prefix}{end_num}",
                "language": language.title(),
                **stats
            }
            
    except Exception as e:
        logger.error(f"Strong's range info failed: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Test the Strong's word study (requires database)
    import asyncio
    
    async def test_strongs_study():
        try:
            # Test Greek word (agape - love)
            result = await get_strongs_data("G25", "KJV", limit=5)
            print("Greek word study (G25 - agape):")
            print(f"Word: {result['strongs_entry']['original_word']}")
            print(f"Definition: {result['strongs_entry']['definition'][:100]}...")
            print(f"Occurrences: {result['usage_statistics']['unique_verses']}")
            print()
            
            # Test Hebrew word (ahab - love)
            result = await get_strongs_data("H157", "BSB", limit=3)
            print("Hebrew word study (H157 - ahab):")
            print(f"Word: {result['strongs_entry']['original_word']}")
            print(f"Definition: {result['strongs_entry']['definition'][:100]}...")
            print(f"Occurrences: {result['usage_statistics']['unique_verses']}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Uncomment to test (requires database setup)
    # asyncio.run(test_strongs_study())