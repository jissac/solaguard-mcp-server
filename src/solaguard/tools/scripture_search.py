"""
Scripture Search Tool Implementation

Implements the search_scripture MCP tool for full-text search across biblical content
with enhanced metadata and theological context.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from ..database.connection import get_database_manager
from ..context import wrap_search_response, wrap_error_response, ContextType

logger = logging.getLogger(__name__)


class ScriptureSearchError(Exception):
    """Raised when scripture search fails."""
    pass


async def search_scripture_data(
    query: str,
    translation: str = "KJV",
    limit: int = 10,
) -> Dict:
    """
    Full-text search across biblical content with enhanced metadata.
    
    Args:
        query: Search terms (supports phrases with quotes, boolean operators)
        translation: Translation to search
        limit: Maximum results to return
    
    Returns:
        Search results with book metadata for AI analysis
        
    Raises:
        ScriptureSearchError: If search fails
    """
    try:
        # Validate and sanitize query
        sanitized_query = _sanitize_search_query(query)
        if not sanitized_query:
            raise ScriptureSearchError("Empty or invalid search query")
        
        # Get database manager
        db_manager = get_database_manager()
        
        # Perform FTS5 search
        search_results = await _execute_fts5_search(
            db_manager, sanitized_query, translation, limit
        )
        
        # Get enhanced metadata
        metadata = await _get_search_metadata(db_manager, search_results, translation)
        
        # Format response with theological context
        return _format_search_response(
            results=search_results,
            query=query,
            translation=translation,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Scripture search failed for '{query}': {e}")
        raise ScriptureSearchError(f"Search failed: {e}")


def _sanitize_search_query(query: str) -> str:
    """
    Sanitize search query to prevent FTS5 injection and ensure valid syntax.
    
    Args:
        query: Raw search query
        
    Returns:
        Sanitized query safe for FTS5
    """
    if not query or not query.strip():
        return ""
    
    # Remove potentially dangerous characters but preserve search functionality
    query = query.strip()
    
    # Handle quoted phrases (preserve them)
    quoted_phrases = re.findall(r'"([^"]*)"', query)
    
    # Remove quotes temporarily and clean the rest
    query_without_quotes = re.sub(r'"[^"]*"', "QUOTED_PHRASE", query)
    
    # Remove or escape potentially dangerous FTS5 characters
    # Keep: letters, numbers, spaces, basic punctuation, boolean operators
    query_without_quotes = re.sub(r'[^\w\s\-\.\,\!\?\:\;\(\)\'\"ANDORNOT]', ' ', query_without_quotes)
    
    # Restore quoted phrases
    for phrase in quoted_phrases:
        # Clean the phrase content
        clean_phrase = re.sub(r'[^\w\s\-\.\,\!\?\:\;\(\)\'\"ANDORNOT]', ' ', phrase)
        query_without_quotes = query_without_quotes.replace("QUOTED_PHRASE", f'"{clean_phrase}"', 1)
    
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query_without_quotes).strip()
    
    # Ensure query is not empty after sanitization
    if not query or query.isspace():
        return ""
    
    return query


async def _execute_fts5_search(
    db_manager, query: str, translation: str, limit: int
) -> List[Dict]:
    """
    Execute FTS5 search query against verses.
    
    Args:
        db_manager: Database manager instance
        query: Sanitized search query
        translation: Translation to search
        limit: Maximum results
        
    Returns:
        List of search results with relevance scores
    """
    async with db_manager.get_connection() as conn:
        # FTS5 search with BM25 ranking and book metadata
        search_sql = """
        SELECT 
            v.id,
            v.book_id,
            v.chapter,
            v.verse,
            v.text,
            b.name as book_name,
            b.testament,
            b.author,
            b.genre,
            b.canonical_order,
            bm25(verses_fts) as relevance_score,
            snippet(verses_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
        FROM verses_fts
        JOIN verses v ON verses_fts.rowid = v.id
        JOIN books b ON v.book_id = b.id
        WHERE verses_fts MATCH ? 
            AND v.translation_id = ?
        ORDER BY bm25(verses_fts)
        LIMIT ?
        """
        
        cursor = await conn.execute(search_sql, (query, translation, limit))
        rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


async def _get_search_metadata(
    db_manager, search_results: List[Dict], translation: str
) -> Dict:
    """
    Get enhanced metadata for search results.
    
    Args:
        db_manager: Database manager instance
        search_results: Search results from FTS5
        translation: Translation searched
        
    Returns:
        Enhanced metadata dictionary
    """
    if not search_results:
        return {
            "total_results": 0,
            "books_found": [],
            "testament_distribution": {"OT": 0, "NT": 0},
            "genre_distribution": {},
            "author_distribution": {},
        }
    
    # Extract unique books from results
    books_found = list(set(result["book_id"] for result in search_results))
    
    # Calculate testament distribution
    testament_counts = {"OT": 0, "NT": 0}
    genre_counts = {}
    author_counts = {}
    
    for result in search_results:
        testament = result["testament"]
        genre = result["genre"]
        author = result["author"]
        
        testament_counts[testament] = testament_counts.get(testament, 0) + 1
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
        author_counts[author] = author_counts.get(author, 0) + 1
    
    # Get book names for found books
    async with db_manager.get_connection() as conn:
        if books_found:
            placeholders = ",".join("?" * len(books_found))
            cursor = await conn.execute(
                f"SELECT id, name FROM books WHERE id IN ({placeholders}) ORDER BY canonical_order",
                books_found
            )
            book_names = dict(await cursor.fetchall())
        else:
            book_names = {}
    
    return {
        "total_results": len(search_results),
        "books_found": [{"id": book_id, "name": book_names.get(book_id, book_id)} for book_id in books_found],
        "testament_distribution": testament_counts,
        "genre_distribution": genre_counts,
        "author_distribution": author_counts,
    }


def _format_search_response(
    results: List[Dict],
    query: str,
    translation: str,
    metadata: Dict
) -> Dict:
    """
    Format search response with theological context.
    
    Args:
        results: Search results from database
        query: Original search query
        translation: Translation searched
        metadata: Enhanced metadata
        
    Returns:
        Formatted search response
    """
    # Format individual results
    formatted_results = []
    for result in results:
        formatted_result = {
            "reference": f"{result['book_name']} {result['chapter']}:{result['verse']}",
            "book_id": result["book_id"],
            "book_name": result["book_name"],
            "chapter": result["chapter"],
            "verse": result["verse"],
            "text": result["text"],
            "snippet": result.get("snippet", result["text"]),
            "relevance_score": round(result.get("relevance_score", 0.0), 3),
            "metadata": {
                "testament": result["testament"],
                "author": result["author"],
                "genre": result["genre"],
                "canonical_order": result["canonical_order"]
            }
        }
        formatted_results.append(formatted_result)
    
    # Prepare response data
    response_data = {
        "query": query,
        "translation": translation,
        "results": formatted_results,
        "metadata": {
            "total_results": metadata["total_results"],
            "results_returned": len(formatted_results),
            "books_found": metadata["books_found"],
            "testament_distribution": metadata["testament_distribution"],
            "genre_distribution": metadata["genre_distribution"],
            "author_distribution": metadata["author_distribution"],
            "search_performance": {
                "fts5_enabled": True,
                "bm25_ranking": True,
                "snippet_highlighting": True
            }
        }
    }
    
    # Wrap with centralized theological context
    return wrap_search_response(
        response_data,
        query=query,
        total_results=metadata["total_results"],
        books_found=metadata["books_found"],
        testament_distribution=metadata["testament_distribution"],
        genre_distribution=metadata["genre_distribution"],
        translation=translation
    )


# Validation functions
async def validate_search_translation(translation: str) -> bool:
    """Check if a translation is available for search."""
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


async def get_search_statistics() -> Dict:
    """Get search-related database statistics."""
    try:
        db_manager = get_database_manager()
        async with db_manager.get_connection() as conn:
            stats = {}
            
            # Total searchable verses
            cursor = await conn.execute("SELECT COUNT(*) FROM verses")
            stats["total_verses"] = (await cursor.fetchone())[0]
            
            # FTS5 index status
            try:
                cursor = await conn.execute("SELECT COUNT(*) FROM verses_fts")
                stats["fts_indexed_verses"] = (await cursor.fetchone())[0]
                stats["fts5_available"] = True
            except Exception:
                stats["fts_indexed_verses"] = 0
                stats["fts5_available"] = False
            
            # Available translations
            cursor = await conn.execute("SELECT id FROM translations ORDER BY id")
            stats["available_translations"] = [row[0] for row in await cursor.fetchall()]
            
            return stats
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Test the search functionality
    import asyncio
    
    async def test_search():
        try:
            # Test search
            result = await search_scripture_data("love", "KJV", 5)
            print("Search test:")
            print(f"Query: {result['query']}")
            print(f"Results: {result['metadata']['total_results']}")
            for r in result['results'][:2]:  # Show first 2
                print(f"  {r['reference']}: {r['text'][:50]}...")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Uncomment to test (requires database setup)
    # asyncio.run(test_search())