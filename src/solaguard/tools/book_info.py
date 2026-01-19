"""
Book Information Tool Implementation

Implements the get_book_info MCP tool for retrieving biblical book metadata
including author, genre, testament, canonical order, and chapter/verse counts.
"""

import logging
from typing import Dict, List, Optional
import re

from ..database.connection import get_database_manager
from ..context import wrap_verse_response, wrap_error_response, ContextType
from .reference_parser import normalize_book_name

logger = logging.getLogger(__name__)


class BookInfoError(Exception):
    """Raised when book information retrieval fails."""
    pass


async def get_book_info_data(
    book_name: str,
    include_stats: bool = True,
) -> Dict:
    """
    Retrieve comprehensive biblical book information and metadata.
    
    Args:
        book_name: Book name (e.g., "Genesis", "Gen", "John", "1 Corinthians")
        include_stats: Include chapter/verse statistics
    
    Returns:
        Book information with Protestant theological context
        
    Raises:
        BookInfoError: If book information retrieval fails
    """
    try:
        # Normalize book name to standard format
        normalized_book = await _normalize_book_name(book_name)
        if not normalized_book:
            return wrap_error_response(
                f"Book not found: {book_name}",
                "Please check the book name. Try full names (Genesis, Exodus) or common abbreviations (Gen, Ex, Matt, John)",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Get book metadata
        book_metadata = await _get_book_metadata(db_manager, normalized_book)
        if not book_metadata:
            return wrap_error_response(
                f"Book metadata not found: {normalized_book}",
                f"The book '{book_name}' was recognized but metadata is missing from our database",
                ContextType.VERSE_RETRIEVAL
            )
        
        # Get book statistics if requested
        book_stats = None
        if include_stats:
            book_stats = await _get_book_statistics(db_manager, normalized_book)
        
        # Get related books (same author, genre, testament)
        related_books = await _get_related_books(db_manager, book_metadata)
        
        # Format response with theological context
        return _format_book_info_response(
            book_metadata=book_metadata,
            book_stats=book_stats,
            related_books=related_books,
            original_query=book_name,
            include_stats=include_stats
        )
        
    except Exception as e:
        logger.error(f"Book info retrieval failed for '{book_name}': {e}")
        raise BookInfoError(f"Failed to retrieve book information: {e}")


async def _normalize_book_name(book_name: str) -> Optional[str]:
    """
    Normalize book name to database book ID format.
    
    Args:
        book_name: Input book name in various formats
        
    Returns:
        Normalized book ID or None if not found
    """
    if not book_name:
        return None
    
    try:
        # Use existing reference parser logic
        normalized = normalize_book_name(book_name.strip())
        return normalized
    except Exception:
        # If reference parser fails, try direct database lookup
        db_manager = get_database_manager()
        
        async with db_manager.get_connection() as conn:
            # Try exact name match (case insensitive)
            cursor = await conn.execute(
                "SELECT id FROM books WHERE LOWER(name) = LOWER(?)",
                (book_name.strip(),)
            )
            result = await cursor.fetchone()
            if result:
                return result[0]
            
            # Try partial name match
            cursor = await conn.execute(
                "SELECT id FROM books WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{book_name.strip()}%",)
            )
            result = await cursor.fetchone()
            if result:
                return result[0]
        
        return None


async def _get_book_metadata(db_manager, book_id: str) -> Optional[Dict]:
    """Get comprehensive book metadata."""
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
        return dict(row) if row else None


async def _get_book_statistics(db_manager, book_id: str) -> Dict:
    """Get book statistics (chapter count, verse count, etc.)."""
    async with db_manager.get_connection() as conn:
        # Get chapter and verse counts
        cursor = await conn.execute(
            """
            SELECT 
                COUNT(DISTINCT chapter) as chapter_count,
                COUNT(*) as verse_count,
                MIN(chapter) as first_chapter,
                MAX(chapter) as last_chapter,
                COUNT(DISTINCT translation_id) as translation_count
            FROM verses
            WHERE book_id = ?
            """,
            (book_id,)
        )
        
        stats = dict(await cursor.fetchone())
        
        # Get verses per chapter breakdown
        cursor = await conn.execute(
            """
            SELECT chapter, COUNT(*) as verses
            FROM verses
            WHERE book_id = ? AND translation_id = 'KJV'
            GROUP BY chapter
            ORDER BY chapter
            """,
            (book_id,)
        )
        
        chapter_breakdown = await cursor.fetchall()
        stats["chapters"] = [{"chapter": row[0], "verses": row[1]} for row in chapter_breakdown]
        
        # Get available translations
        cursor = await conn.execute(
            """
            SELECT DISTINCT v.translation_id, t.name
            FROM verses v
            JOIN translations t ON v.translation_id = t.id
            WHERE v.book_id = ?
            ORDER BY v.translation_id
            """,
            (book_id,)
        )
        
        translations = await cursor.fetchall()
        stats["available_translations"] = [{"id": row[0], "name": row[1]} for row in translations]
        
        return stats


async def _get_related_books(db_manager, book_metadata: Dict) -> Dict:
    """Get books related by author, genre, and testament."""
    book_id = book_metadata["id"]
    author = book_metadata.get("author")
    genre = book_metadata.get("genre")
    testament = book_metadata["testament"]
    
    related = {
        "same_author": [],
        "same_genre": [],
        "same_testament_count": 0
    }
    
    async with db_manager.get_connection() as conn:
        # Books by same author
        if author and author != "Unknown":
            cursor = await conn.execute(
                """
                SELECT id, name, canonical_order
                FROM books
                WHERE author = ? AND id != ?
                ORDER BY canonical_order
                """,
                (author, book_id)
            )
            
            same_author = await cursor.fetchall()
            related["same_author"] = [
                {"id": row[0], "name": row[1], "canonical_order": row[2]}
                for row in same_author
            ]
        
        # Books in same genre
        if genre:
            cursor = await conn.execute(
                """
                SELECT id, name, canonical_order
                FROM books
                WHERE genre = ? AND id != ?
                ORDER BY canonical_order
                LIMIT 10
                """,
                (genre, book_id)
            )
            
            same_genre = await cursor.fetchall()
            related["same_genre"] = [
                {"id": row[0], "name": row[1], "canonical_order": row[2]}
                for row in same_genre
            ]
        
        # Count books in same testament
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM books WHERE testament = ?",
            (testament,)
        )
        
        related["same_testament_count"] = (await cursor.fetchone())[0]
    
    return related


def _format_book_info_response(
    book_metadata: Dict,
    book_stats: Optional[Dict],
    related_books: Dict,
    original_query: str,
    include_stats: bool
) -> Dict:
    """Format the book information response with theological context."""
    
    # Format basic book information
    book_info = {
        "book_id": book_metadata["id"],
        "name": book_metadata["name"],
        "testament": "Old Testament" if book_metadata["testament"] == "OT" else "New Testament",
        "testament_code": book_metadata["testament"],
        "author": book_metadata.get("author", "Unknown"),
        "genre": book_metadata.get("genre", "Unknown"),
        "canonical_order": book_metadata["canonical_order"],
        "position_description": _get_position_description(book_metadata["canonical_order"], book_metadata["testament"])
    }
    
    # Add statistics if included
    if book_stats:
        book_info["statistics"] = {
            "chapters": book_stats["chapter_count"],
            "verses": book_stats["verse_count"],
            "available_translations": len(book_stats["available_translations"]),
            "chapter_breakdown": book_stats["chapters"][:5],  # First 5 chapters
            "translations": book_stats["available_translations"]
        }
        
        # Add total chapter breakdown if more than 5 chapters
        if book_stats["chapter_count"] > 5:
            book_info["statistics"]["total_chapters"] = book_stats["chapter_count"]
            book_info["statistics"]["chapter_breakdown_note"] = f"Showing first 5 of {book_stats['chapter_count']} chapters"
    
    # Add related books
    book_info["related_books"] = {
        "same_author": related_books["same_author"][:5],  # Limit to 5
        "same_genre": related_books["same_genre"][:5],   # Limit to 5
        "testament_info": {
            "testament": book_info["testament"],
            "total_books_in_testament": related_books["same_testament_count"]
        }
    }
    
    # Add contextual information
    book_info["context"] = {
        "historical_period": _get_historical_period(book_metadata),
        "literary_type": _get_literary_description(book_metadata.get("genre", "")),
        "theological_themes": _get_theological_themes(book_metadata)
    }
    
    # Prepare response data
    response_data = {
        "book_info": book_info,
        "query": {
            "original": original_query,
            "normalized": book_metadata["id"],
            "include_stats": include_stats
        }
    }
    
    # Wrap with theological context
    return wrap_verse_response(
        response_data,
        testament=book_metadata["testament"],
        genre=book_metadata.get("genre", "Unknown"),
        book_name=book_metadata["name"],
        author=book_metadata.get("author")
    )


def _get_position_description(canonical_order: int, testament: str) -> str:
    """Get descriptive position of book in canon."""
    if testament == "OT":
        if canonical_order <= 5:
            return f"Book {canonical_order} of 39 in Old Testament (Torah/Pentateuch)"
        elif canonical_order <= 17:
            return f"Book {canonical_order} of 39 in Old Testament (Historical Books)"
        elif canonical_order <= 22:
            return f"Book {canonical_order} of 39 in Old Testament (Wisdom Literature)"
        else:
            return f"Book {canonical_order} of 39 in Old Testament (Prophetic Books)"
    else:  # NT
        nt_order = canonical_order - 39
        if nt_order <= 4:
            return f"Book {nt_order} of 27 in New Testament (Gospels)"
        elif nt_order == 5:
            return f"Book {nt_order} of 27 in New Testament (Acts)"
        elif nt_order <= 26:
            return f"Book {nt_order} of 27 in New Testament (Epistles)"
        else:
            return f"Book {nt_order} of 27 in New Testament (Revelation)"


def _get_historical_period(book_metadata: Dict) -> str:
    """Get historical period description."""
    testament = book_metadata["testament"]
    canonical_order = book_metadata["canonical_order"]
    
    if testament == "OT":
        if canonical_order <= 5:
            return "Mosaic Period (c. 1500-1400 BC)"
        elif canonical_order <= 17:
            return "Kingdom Period (c. 1000-400 BC)"
        elif canonical_order <= 22:
            return "Various periods (c. 1000-400 BC)"
        else:
            return "Prophetic Period (c. 800-400 BC)"
    else:
        return "Apostolic Period (c. 50-100 AD)"


def _get_literary_description(genre: str) -> str:
    """Get literary type description."""
    descriptions = {
        "Law": "Legal and ceremonial instructions from God",
        "History": "Historical narrative of God's people",
        "Wisdom": "Practical wisdom for godly living",
        "Prophecy": "Prophetic messages and visions",
        "Gospel": "Biography of Jesus Christ's life and ministry",
        "Epistle": "Apostolic letters to churches and individuals"
    }
    return descriptions.get(genre, "Biblical literature")


def _get_theological_themes(book_metadata: Dict) -> List[str]:
    """Get major theological themes for the book."""
    book_id = book_metadata["id"]
    
    # Simplified theme mapping - in production this could be more sophisticated
    theme_map = {
        "GEN": ["Creation", "Fall", "Covenant", "Providence"],
        "EXO": ["Redemption", "Law", "Worship", "God's Presence"],
        "LEV": ["Holiness", "Sacrifice", "Priesthood", "Purity"],
        "NUM": ["Wilderness", "Faithfulness", "God's Guidance"],
        "DEU": ["Covenant Renewal", "Obedience", "Blessing and Curse"],
        "PSA": ["Worship", "Prayer", "God's Character", "Human Experience"],
        "PRO": ["Wisdom", "Fear of the Lord", "Practical Living"],
        "ISA": ["Messiah", "Judgment", "Salvation", "God's Sovereignty"],
        "JER": ["Judgment", "New Covenant", "God's Faithfulness"],
        "EZE": ["God's Glory", "Restoration", "Personal Responsibility"],
        "DAN": ["God's Kingdom", "Prophecy", "Faithfulness under Trial"],
        "MAT": ["Jesus as King", "Kingdom of Heaven", "Fulfillment of Prophecy"],
        "MAR": ["Jesus as Servant", "Discipleship", "Suffering"],
        "LUK": ["Jesus as Savior", "Compassion", "Universal Gospel"],
        "JOH": ["Jesus as God", "Eternal Life", "Love", "Truth"],
        "ACT": ["Holy Spirit", "Church Growth", "Mission", "Witness"],
        "ROM": ["Justification", "Grace", "Faith", "Sanctification"],
        "1CO": ["Church Unity", "Spiritual Gifts", "Love", "Resurrection"],
        "2CO": ["Ministry", "Suffering", "Comfort", "Giving"],
        "GAL": ["Freedom in Christ", "Faith vs. Works", "Spirit vs. Flesh"],
        "EPH": ["Unity in Christ", "Spiritual Blessings", "Christian Living"],
        "PHP": ["Joy", "Humility", "Contentment", "Christ's Example"],
        "COL": ["Christ's Supremacy", "Fullness in Christ", "New Life"],
        "1TH": ["Second Coming", "Holy Living", "Encouragement"],
        "2TH": ["Perseverance", "Work Ethic", "End Times"],
        "1TI": ["Church Leadership", "Sound Doctrine", "Godliness"],
        "2TI": ["Faithfulness", "Scripture", "Endurance"],
        "TIT": ["Church Order", "Good Works", "Sound Teaching"],
        "PHM": ["Forgiveness", "Christian Brotherhood", "Transformation"],
        "HEB": ["Christ's Superiority", "Faith", "Perseverance", "New Covenant"],
        "JAS": ["Faith and Works", "Practical Christianity", "Wisdom"],
        "1PE": ["Suffering", "Hope", "Holiness", "Submission"],
        "2PE": ["False Teachers", "Scripture", "Second Coming"],
        "1JO": ["Love", "Truth", "Assurance", "Fellowship with God"],
        "2JO": ["Truth", "Love", "Discernment"],
        "3JO": ["Hospitality", "Truth", "Christian Fellowship"],
        "JUD": ["Contending for Faith", "False Teachers", "Perseverance"],
        "REV": ["Christ's Victory", "Judgment", "New Creation", "Worship"]
    }
    
    return theme_map.get(book_id, ["God's Word", "Divine Truth", "Spiritual Growth"])


# Utility functions
async def search_books_by_criteria(
    testament: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None
) -> List[Dict]:
    """
    Search for books by various criteria.
    
    Args:
        testament: "OT" or "NT"
        author: Author name
        genre: Genre classification
        
    Returns:
        List of matching books
    """
    try:
        db_manager = get_database_manager()
        
        conditions = []
        params = []
        
        if testament:
            conditions.append("testament = ?")
            params.append(testament)
        
        if author:
            conditions.append("author = ?")
            params.append(author)
        
        if genre:
            conditions.append("genre = ?")
            params.append(genre)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                f"""
                SELECT id, name, testament, author, genre, canonical_order
                FROM books
                WHERE {where_clause}
                ORDER BY canonical_order
                """,
                params
            )
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Book search failed: {e}")
        return []


async def get_canon_overview() -> Dict:
    """Get overview of the entire biblical canon."""
    try:
        db_manager = get_database_manager()
        
        async with db_manager.get_connection() as conn:
            # Testament breakdown
            cursor = await conn.execute(
                """
                SELECT testament, COUNT(*) as book_count
                FROM books
                GROUP BY testament
                ORDER BY testament
                """
            )
            testament_counts = dict(await cursor.fetchall())
            
            # Genre breakdown
            cursor = await conn.execute(
                """
                SELECT genre, COUNT(*) as book_count, testament
                FROM books
                GROUP BY genre, testament
                ORDER BY testament, genre
                """
            )
            genre_breakdown = await cursor.fetchall()
            
            # Author breakdown
            cursor = await conn.execute(
                """
                SELECT author, COUNT(*) as book_count
                FROM books
                WHERE author IS NOT NULL AND author != 'Unknown'
                GROUP BY author
                ORDER BY book_count DESC
                LIMIT 10
                """
            )
            author_breakdown = await cursor.fetchall()
            
            return {
                "total_books": sum(testament_counts.values()),
                "testaments": {
                    "old_testament": testament_counts.get("OT", 0),
                    "new_testament": testament_counts.get("NT", 0)
                },
                "genres": [
                    {"genre": row[0], "count": row[1], "testament": row[2]}
                    for row in genre_breakdown
                ],
                "top_authors": [
                    {"author": row[0], "books": row[1]}
                    for row in author_breakdown
                ]
            }
            
    except Exception as e:
        logger.error(f"Canon overview failed: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Test the book info tool (requires database)
    import asyncio
    
    async def test_book_info():
        try:
            # Test various book formats
            test_books = ["Genesis", "Gen", "John", "1 Corinthians", "Revelation", "Psalms"]
            
            for book in test_books:
                print(f"\n=== Testing: {book} ===")
                result = await get_book_info_data(book, include_stats=True)
                
                if "error" in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    book_info = result["book_info"]
                    print(f"✅ {book_info['name']} ({book_info['book_id']})")
                    print(f"   Testament: {book_info['testament']}")
                    print(f"   Author: {book_info['author']}")
                    print(f"   Genre: {book_info['genre']}")
                    print(f"   Position: {book_info['position_description']}")
                    
                    if "statistics" in book_info:
                        stats = book_info["statistics"]
                        print(f"   Chapters: {stats['chapters']}, Verses: {stats['verses']}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Uncomment to test (requires database setup)
    # asyncio.run(test_book_info())