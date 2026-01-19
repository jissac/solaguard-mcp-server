"""
Cross-Reference Discovery Tool Implementation

Implements the get_cross_references MCP tool for finding thematically related
Bible passages with translation-agnostic logic.
"""

import logging
from typing import Dict, List, Optional, Tuple

from ..database.connection import get_database_manager
from ..context import wrap_cross_reference_response, wrap_error_response, ContextType
from .reference_parser import (
    parse_reference, 
    VerseReference, 
    ReferenceParseError,
    format_reference
)

logger = logging.getLogger(__name__)


class CrossReferenceError(Exception):
    """Raised when cross-reference discovery fails."""
    pass


async def get_cross_references_data(
    reference: str,
    translation: str = "KJV",
    limit: int = 10,
) -> Dict:
    """
    Find thematically related Bible passages using translation-agnostic logic.
    
    Args:
        reference: Biblical reference (e.g., "John 3:16", "Genesis 1:1")
        translation: Translation to return results in (KJV, BSB, etc.)
        limit: Maximum number of cross-references to return
    
    Returns:
        Cross-reference data with Protestant theological context
        
    Raises:
        CrossReferenceError: If cross-reference discovery fails
    """
    try:
        # Parse the reference (validation handled at server level)
        parsed_ref = parse_reference(reference)
        
        # Only support single verses for cross-references (not ranges)
        if not isinstance(parsed_ref, VerseReference):
            return wrap_error_response(
                "Cross-references only support single verses, not verse ranges",
                "Please use a single verse reference like 'John 3:16'",
                ContextType.CROSS_REFERENCE
            )
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Find the source verse (translation-agnostic lookup)
        source_verse = await _find_source_verse(db_manager, parsed_ref)
        if not source_verse:
            return wrap_error_response(
                f"Source verse not found: {reference}",
                "Please check your reference format (e.g., 'John 3:16')",
                ContextType.CROSS_REFERENCE
            )
        
        # Get cross-references using KJV as the reference translation
        cross_refs = await _get_cross_references(db_manager, source_verse, limit)
        
        if not cross_refs:
            return wrap_error_response(
                f"No cross-references found for {reference}",
                "This verse may not have traditional cross-references in our database",
                ContextType.CROSS_REFERENCE
            )
        
        # Convert cross-references to requested translation
        translated_refs = await _translate_cross_references(
            db_manager, cross_refs, translation
        )
        
        # Get source verse in requested translation for context
        source_in_translation = await _get_verse_in_translation(
            db_manager, parsed_ref, translation
        )
        
        # Format response with theological context
        return _format_cross_reference_response(
            source_verse=source_in_translation,
            cross_references=translated_refs,
            original_reference=reference,
            translation=translation,
            total_found=len(cross_refs)
        )
        
    except ReferenceParseError as e:
        return wrap_error_response(
            f"Invalid reference format: {e}",
            "Please use format like 'John 3:16' or 'Genesis 1:1'",
            ContextType.CROSS_REFERENCE
        )
    except Exception as e:
        logger.error(f"Cross-reference discovery failed for '{reference}': {e}")
        raise CrossReferenceError(f"Failed to find cross-references: {e}")


async def _find_source_verse(db_manager, verse_ref: VerseReference) -> Optional[Dict]:
    """
    Find the source verse using translation-agnostic lookup.
    Tries KJV first (where cross-references are stored), then falls back to any translation.
    """
    async with db_manager.get_connection() as conn:
        # First try KJV (where cross-references are linked)
        cursor = await conn.execute(
            """
            SELECT v.id, v.book_id, v.chapter, v.verse, v.text, v.translation_id,
                   b.name, b.testament, b.author, b.genre
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.translation_id = 'KJV' AND v.book_id = ? AND v.chapter = ? AND v.verse = ?
            """,
            (verse_ref.book_id, verse_ref.chapter, verse_ref.verse)
        )
        
        row = await cursor.fetchone()
        if row:
            return dict(row)
        
        # Fallback: try any translation for this verse
        cursor = await conn.execute(
            """
            SELECT v.id, v.book_id, v.chapter, v.verse, v.text, v.translation_id,
                   b.name, b.testament, b.author, b.genre
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.book_id = ? AND v.chapter = ? AND v.verse = ?
            LIMIT 1
            """,
            (verse_ref.book_id, verse_ref.chapter, verse_ref.verse)
        )
        
        row = await cursor.fetchone()
        return dict(row) if row else None


async def _get_cross_references(db_manager, source_verse: Dict, limit: int) -> List[Dict]:
    """
    Get cross-references for the source verse.
    Uses the KJV verse ID to find cross-references.
    """
    async with db_manager.get_connection() as conn:
        # If source verse is not KJV, find the corresponding KJV verse
        kjv_verse_id = source_verse["id"]
        if source_verse["translation_id"] != "KJV":
            cursor = await conn.execute(
                """
                SELECT id FROM verses
                WHERE translation_id = 'KJV' AND book_id = ? AND chapter = ? AND verse = ?
                """,
                (source_verse["book_id"], source_verse["chapter"], source_verse["verse"])
            )
            kjv_row = await cursor.fetchone()
            if kjv_row:
                kjv_verse_id = kjv_row[0]
            else:
                return []  # No KJV verse found, no cross-references available
        
        # Get cross-references using the KJV verse ID
        cursor = await conn.execute(
            """
            SELECT cr.to_verse_id, cr.relationship_type, cr.relevance_score,
                   v.book_id, v.chapter, v.verse, v.text,
                   b.name, b.testament, b.author, b.genre
            FROM cross_references cr
            JOIN verses v ON cr.to_verse_id = v.id
            JOIN books b ON v.book_id = b.id
            WHERE cr.from_verse_id = ? AND v.translation_id = 'KJV'
            ORDER BY cr.relevance_score DESC, b.canonical_order, v.chapter, v.verse
            LIMIT ?
            """,
            (kjv_verse_id, limit)
        )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def _translate_cross_references(
    db_manager, cross_refs: List[Dict], target_translation: str
) -> List[Dict]:
    """
    Translate cross-references to the requested translation.
    Falls back to KJV if target translation doesn't have the verse.
    """
    translated_refs = []
    
    async with db_manager.get_connection() as conn:
        for ref in cross_refs:
            # Try to get the verse in the target translation
            cursor = await conn.execute(
                """
                SELECT v.id, v.text, v.translation_id
                FROM verses v
                WHERE v.translation_id = ? AND v.book_id = ? AND v.chapter = ? AND v.verse = ?
                """,
                (target_translation, ref["book_id"], ref["chapter"], ref["verse"])
            )
            
            translated_row = await cursor.fetchone()
            
            if translated_row:
                # Use the translated version
                ref_copy = ref.copy()
                ref_copy["text"] = translated_row[1]
                ref_copy["translation_id"] = translated_row[2]
                translated_refs.append(ref_copy)
            else:
                # Fall back to KJV (original)
                ref_copy = ref.copy()
                ref_copy["translation_id"] = "KJV"
                translated_refs.append(ref_copy)
    
    return translated_refs


async def _get_verse_in_translation(
    db_manager, verse_ref: VerseReference, translation: str
) -> Optional[Dict]:
    """Get the source verse in the requested translation."""
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT v.id, v.book_id, v.chapter, v.verse, v.text, v.translation_id,
                   b.name, b.testament, b.author, b.genre
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.translation_id = ? AND v.book_id = ? AND v.chapter = ? AND v.verse = ?
            """,
            (translation, verse_ref.book_id, verse_ref.chapter, verse_ref.verse)
        )
        
        row = await cursor.fetchone()
        return dict(row) if row else None


def _format_cross_reference_response(
    source_verse: Optional[Dict],
    cross_references: List[Dict],
    original_reference: str,
    translation: str,
    total_found: int
) -> Dict:
    """Format the cross-reference response with theological context."""
    
    # Format source verse
    if source_verse:
        source_info = {
            "reference": format_reference(source_verse["book_id"], source_verse["chapter"], source_verse["verse"]),
            "book_name": source_verse["name"],
            "text": source_verse["text"],
            "translation": source_verse["translation_id"]
        }
        book_metadata = {
            "testament": source_verse.get("testament", "Unknown"),
            "author": source_verse.get("author", "Unknown"),
            "genre": source_verse.get("genre", "Unknown")
        }
    else:
        source_info = {
            "reference": original_reference,
            "book_name": "Unknown",
            "text": "Source verse not available in requested translation",
            "translation": translation
        }
        book_metadata = {
            "testament": "Unknown",
            "author": "Unknown", 
            "genre": "Unknown"
        }
    
    # Format cross-references
    formatted_refs = []
    for ref in cross_references:
        ref_info = {
            "reference": format_reference(ref["book_id"], ref["chapter"], ref["verse"]),
            "book_name": ref["name"],
            "text": ref["text"],
            "translation": ref["translation_id"],
            "relationship_type": ref.get("relationship_type", "traditional"),
            "relevance_score": ref.get("relevance_score", 1.0),
            "book_metadata": {
                "testament": ref.get("testament", "Unknown"),
                "author": ref.get("author", "Unknown"),
                "genre": ref.get("genre", "Unknown")
            }
        }
        formatted_refs.append(ref_info)
    
    # Group cross-references by testament for analysis
    ot_refs = [r for r in formatted_refs if r["book_metadata"]["testament"] == "OT"]
    nt_refs = [r for r in formatted_refs if r["book_metadata"]["testament"] == "NT"]
    
    # Prepare response data
    response_data = {
        "source_verse": source_info,
        "cross_references": formatted_refs,
        "metadata": {
            "translation": translation,
            "total_found": total_found,
            "returned_count": len(formatted_refs),
            "testament_distribution": {
                "old_testament": len(ot_refs),
                "new_testament": len(nt_refs)
            },
            "relationship_types": list(set(r.get("relationship_type", "traditional") for r in formatted_refs)),
            "book_metadata": book_metadata
        }
    }
    
    # Wrap with centralized theological context
    return wrap_cross_reference_response(
        response_data,
        testament=book_metadata.get("testament", "Unknown"),
        genre=book_metadata.get("genre", "Unknown"),
        book_name=source_info.get("book_name", "Unknown"),
        cross_ref_count=len(formatted_refs)
    )


# Utility functions
async def get_cross_reference_stats(verse_reference: str) -> Dict:
    """Get statistics about cross-references for a verse."""
    try:
        parsed_ref = parse_reference(verse_reference)
        if not isinstance(parsed_ref, VerseReference):
            return {"error": "Only single verses supported"}
        
        db_manager = get_database_manager()
        source_verse = await _find_source_verse(db_manager, parsed_ref)
        
        if not source_verse:
            return {"error": "Verse not found"}
        
        async with db_manager.get_connection() as conn:
            # Get KJV verse ID for cross-reference lookup
            kjv_verse_id = source_verse["id"]
            if source_verse["translation_id"] != "KJV":
                cursor = await conn.execute(
                    """
                    SELECT id FROM verses
                    WHERE translation_id = 'KJV' AND book_id = ? AND chapter = ? AND verse = ?
                    """,
                    (source_verse["book_id"], source_verse["chapter"], source_verse["verse"])
                )
                kjv_row = await cursor.fetchone()
                if kjv_row:
                    kjv_verse_id = kjv_row[0]
            
            # Count total cross-references
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM cross_references WHERE from_verse_id = ?",
                (kjv_verse_id,)
            )
            total_count = (await cursor.fetchone())[0]
            
            return {
                "verse": verse_reference,
                "total_cross_references": total_count,
                "has_cross_references": total_count > 0
            }
            
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Test the cross-reference discovery (requires database)
    import asyncio
    
    async def test_cross_references():
        try:
            # Test Genesis 1:1 (should have many cross-references)
            result = await get_cross_references_data("Genesis 1:1", "KJV", limit=5)
            print("Genesis 1:1 cross-references:")
            print(f"Source: {result['source_verse']['reference']} - {result['source_verse']['text'][:50]}...")
            print(f"Found {result['metadata']['total_found']} cross-references:")
            
            for i, ref in enumerate(result['cross_references'], 1):
                print(f"  {i}. {ref['reference']} - {ref['text'][:50]}...")
            print()
            
            # Test stats
            stats = await get_cross_reference_stats("Genesis 1:1")
            print(f"Stats: {stats}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Uncomment to test (requires database setup)
    # asyncio.run(test_cross_references())