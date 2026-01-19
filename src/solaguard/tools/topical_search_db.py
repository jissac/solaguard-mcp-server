"""
Topical Search Tool - Database Implementation

Searches Naves Topical Dictionary for topics and returns related verses.
"""

import logging
from typing import List, Dict, Optional
import sqlite3

from ..context import wrap_response, ContextType
from ..database import get_database_manager

logger = logging.getLogger(__name__)


async def search_by_topic_data(
    topic: str,
    translation: str = "KJV",
    limit: int = 20,
    expand_cross_refs: bool = True,
) -> dict:
    """
    Search for verses related to theological topics.
    
    Args:
        topic: Topic or concept to search for
        translation: Translation to return results in
        limit: Maximum number of results to return
        expand_cross_refs: Whether to expand results using cross-references
        
    Returns:
        Topical search results with theological context
    """
    try:
        db_manager = get_database_manager()
        
        # Search for matching topics
        topics = await _search_topics(db_manager, topic, limit)
        
        if not topics:
            return wrap_response(
                {
                    "query": topic,
                    "topics_found": 0,
                    "results": [],
                    "message": f"No topics found matching '{topic}'",
                    "suggestions": [
                        "Try broader terms (e.g., 'love' instead of 'agape love')",
                        "Check spelling",
                        "Try common theological topics: salvation, faith, grace, prayer, sin, forgiveness"
                    ]
                },
                ContextType.SCRIPTURE_SEARCH
            )
        
        # Get verses for each topic
        results = []
        total_verses = 0
        
        for topic_data in topics:
            topic_id = topic_data['id']
            topic_name = topic_data['topic']
            
            # Get verses for this topic
            verses = await _get_topic_verses(
                db_manager,
                topic_id,
                translation,
                limit - total_verses
            )
            
            if verses:
                results.append({
                    "topic": topic_name,
                    "description": topic_data.get('description', ''),
                    "verse_count": len(verses),
                    "verses": verses
                })
                
                total_verses += len(verses)
                
                if total_verses >= limit:
                    break
        
        return wrap_response(
            {
                "query": topic,
                "topics_found": len(topics),
                "results": results,
                "total_verses": total_verses,
                "translation": translation,
                "message": f"Found {len(topics)} topics with {total_verses} related verses"
            },
            ContextType.SCRIPTURE_SEARCH
        )
        
    except Exception as e:
        logger.error(f"Topical search failed: {e}")
        raise


async def _search_topics(
    db_manager,
    query: str,
    limit: int
) -> List[Dict]:
    """
    Search for topics matching the query.
    
    Args:
        db_manager: Database manager instance
        query: Search query
        limit: Maximum results
        
    Returns:
        List of matching topics
    """
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("""
            SELECT id, topic, description
            FROM topical_index
            WHERE topic LIKE ? OR topic LIKE ?
            ORDER BY 
                CASE 
                    WHEN LOWER(topic) = LOWER(?) THEN 1
                    WHEN LOWER(topic) LIKE LOWER(?) THEN 2
                    ELSE 3
                END,
                topic
            LIMIT ?
        """, (
            f"%{query}%",
            f"%{query.replace(' ', '%')}%",
            query,
            f"{query}%",
            limit
        ))
        
        rows = await cursor.fetchall()
        
        return [
            {
                'id': row[0],
                'topic': row[1],
                'description': row[2]
            }
            for row in rows
        ]


async def _get_topic_verses(
    db_manager,
    topic_id: int,
    translation: str,
    limit: int
) -> List[Dict]:
    """
    Get verses associated with a topic.
    
    Args:
        db_manager: Database manager instance
        topic_id: Topic ID
        translation: Translation code
        limit: Maximum verses to return
        
    Returns:
        List of verse data
    """
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("""
            SELECT 
                v.book_id,
                v.chapter,
                v.verse,
                v.text,
                b.name as book_name,
                tv.relevance_score
            FROM topic_verses tv
            JOIN verses v ON tv.verse_id = v.id
            JOIN books b ON v.book_id = b.id
            WHERE tv.topic_id = ?
                AND v.translation_id = ?
            ORDER BY tv.relevance_score DESC, v.book_id, v.chapter, v.verse
            LIMIT ?
        """, (topic_id, translation, limit))
        
        rows = await cursor.fetchall()
        
        return [
            {
                'reference': f"{row[4]} {row[1]}:{row[2]}",
                'book_id': row[0],
                'chapter': row[1],
                'verse': row[2],
                'text': row[3],
                'book_name': row[4],
                'relevance': row[5]
            }
            for row in rows
        ]
