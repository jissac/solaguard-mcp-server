"""
Biblical Reference Validation

Specialized validation for biblical references including book/chapter/verse
range validation against database constraints.
"""

import logging
from typing import Dict, List, Optional, Tuple

from ..database.connection import get_database_manager

logger = logging.getLogger(__name__)


class ReferenceValidationError(Exception):
    """Specific exception for biblical reference validation errors."""
    pass


async def validate_book_exists(book_id: str) -> Dict[str, str]:
    """
    Validate that a book exists in the database.
    
    Args:
        book_id: Book identifier (e.g., "JHN", "GEN")
        
    Returns:
        Dictionary with book information
        
    Raises:
        ReferenceValidationError: If book doesn't exist
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT id, name, testament, author, genre FROM books WHERE id = ?",
                (book_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                # Get similar book names for suggestions
                cursor = await conn.execute(
                    "SELECT id, name FROM books WHERE name LIKE ? OR id LIKE ? LIMIT 5",
                    (f"%{book_id}%", f"%{book_id}%")
                )
                similar = await cursor.fetchall()
                
                if similar:
                    suggestions = [f"{row[1]} ({row[0]})" for row in similar]
                    raise ReferenceValidationError(
                        f"Book '{book_id}' not found. Did you mean: {', '.join(suggestions)}?"
                    )
                else:
                    raise ReferenceValidationError(f"Book '{book_id}' not found")
            
            return {
                "id": row[0],
                "name": row[1],
                "testament": row[2],
                "author": row[3],
                "genre": row[4]
            }
    
    except ReferenceValidationError:
        raise
    except Exception as e:
        logger.error(f"Book validation failed for '{book_id}': {e}")
        raise ReferenceValidationError(f"Unable to validate book '{book_id}'")


async def validate_chapter_range(book_id: str, chapter: int) -> Dict[str, int]:
    """
    Validate that a chapter exists for the given book.
    
    Args:
        book_id: Book identifier
        chapter: Chapter number
        
    Returns:
        Dictionary with chapter information
        
    Raises:
        ReferenceValidationError: If chapter is out of range
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            # Get chapter range for this book
            cursor = await conn.execute(
                "SELECT MIN(chapter), MAX(chapter) FROM verses WHERE book_id = ?",
                (book_id,)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] is None:
                raise ReferenceValidationError(f"No chapters found for book '{book_id}'")
            
            min_chapter, max_chapter = row
            
            if chapter < min_chapter or chapter > max_chapter:
                if min_chapter == max_chapter:
                    raise ReferenceValidationError(
                        f"Book '{book_id}' only has chapter {min_chapter}"
                    )
                else:
                    raise ReferenceValidationError(
                        f"Book '{book_id}' has chapters {min_chapter}-{max_chapter}, not {chapter}"
                    )
            
            return {
                "chapter": chapter,
                "min_chapter": min_chapter,
                "max_chapter": max_chapter
            }
    
    except ReferenceValidationError:
        raise
    except Exception as e:
        logger.error(f"Chapter validation failed for '{book_id}' {chapter}: {e}")
        raise ReferenceValidationError(f"Unable to validate chapter {chapter}")


async def validate_verse_range(book_id: str, chapter: int, verse: int, end_verse: Optional[int] = None) -> Dict[str, int]:
    """
    Validate that verse(s) exist for the given book and chapter.
    
    Args:
        book_id: Book identifier
        chapter: Chapter number
        verse: Starting verse number
        end_verse: Ending verse number (for ranges)
        
    Returns:
        Dictionary with verse information
        
    Raises:
        ReferenceValidationError: If verse is out of range
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            # Get verse range for this chapter
            cursor = await conn.execute(
                "SELECT MIN(verse), MAX(verse) FROM verses WHERE book_id = ? AND chapter = ?",
                (book_id, chapter)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] is None:
                raise ReferenceValidationError(
                    f"No verses found for {book_id} {chapter}"
                )
            
            min_verse, max_verse = row
            
            # Validate starting verse
            if verse < min_verse or verse > max_verse:
                raise ReferenceValidationError(
                    f"{book_id} {chapter} has verses {min_verse}-{max_verse}, not {verse}"
                )
            
            # Validate ending verse if provided
            if end_verse is not None:
                if end_verse < verse:
                    raise ReferenceValidationError(
                        f"End verse {end_verse} cannot be before start verse {verse}"
                    )
                
                if end_verse > max_verse:
                    raise ReferenceValidationError(
                        f"{book_id} {chapter} has verses {min_verse}-{max_verse}, not {end_verse}"
                    )
            
            return {
                "verse": verse,
                "end_verse": end_verse,
                "min_verse": min_verse,
                "max_verse": max_verse
            }
    
    except ReferenceValidationError:
        raise
    except Exception as e:
        logger.error(f"Verse validation failed for '{book_id}' {chapter}:{verse}: {e}")
        raise ReferenceValidationError(f"Unable to validate verse {verse}")


async def get_book_chapter_verse_ranges() -> Dict[str, Dict]:
    """
    Get complete book/chapter/verse ranges for validation.
    
    Returns:
        Dictionary mapping book_id to chapter/verse ranges
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    b.id,
                    b.name,
                    MIN(v.chapter) as min_chapter,
                    MAX(v.chapter) as max_chapter,
                    COUNT(DISTINCT v.chapter) as chapter_count,
                    COUNT(v.verse) as total_verses
                FROM books b
                LEFT JOIN verses v ON b.id = v.book_id
                GROUP BY b.id, b.name
                ORDER BY b.canonical_order
            """)
            
            ranges = {}
            for row in await cursor.fetchall():
                book_id, name, min_ch, max_ch, ch_count, total_verses = row
                ranges[book_id] = {
                    "name": name,
                    "min_chapter": min_ch or 1,
                    "max_chapter": max_ch or 1,
                    "chapter_count": ch_count or 0,
                    "total_verses": total_verses or 0
                }
            
            return ranges
    
    except Exception as e:
        logger.error(f"Failed to get book ranges: {e}")
        return {}


async def get_chapter_verse_ranges(book_id: str) -> Dict[int, Dict]:
    """
    Get verse ranges for each chapter in a book.
    
    Args:
        book_id: Book identifier
        
    Returns:
        Dictionary mapping chapter number to verse ranges
    """
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT 
                    chapter,
                    MIN(verse) as min_verse,
                    MAX(verse) as max_verse,
                    COUNT(verse) as verse_count
                FROM verses 
                WHERE book_id = ?
                GROUP BY chapter
                ORDER BY chapter
            """, (book_id,))
            
            ranges = {}
            for row in await cursor.fetchall():
                chapter, min_verse, max_verse, verse_count = row
                ranges[chapter] = {
                    "min_verse": min_verse,
                    "max_verse": max_verse,
                    "verse_count": verse_count
                }
            
            return ranges
    
    except Exception as e:
        logger.error(f"Failed to get chapter ranges for '{book_id}': {e}")
        return {}