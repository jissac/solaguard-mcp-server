"""
SolaGuard MCP Server

Main server implementation using FastMCP framework.
"""

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP

# Configure logging
log_level = os.getenv("SOLAGUARD_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("SolaGuard")

# Global database manager
_db_manager = None


async def ensure_database():
    """Ensure database is initialized."""
    global _db_manager
    if _db_manager is None:
        logger.info("🚀 Starting SolaGuard MCP Server")
        logger.info("📖 Bible-Anchored Theology — Sola Scriptura Enforced")
        logger.info("🔗 Universal theological infrastructure for AI applications")
        
        # Initialize database connection
        from .database import initialize_database, get_database_manager
        
        db_path = Path(os.getenv("SOLAGUARD_DATABASE_PATH", "data/bible_mock.db"))
        
        try:
            await initialize_database(db_path)
            _db_manager = get_database_manager()
            logger.info(f"📚 Database initialized: {db_path}")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            logger.info("💡 Run 'python scripts/generate_mock_data.py' to create test database")
            raise
    
    return _db_manager


@mcp.tool()
async def get_verse(
    reference: str,
    translation: str = "KJV",
    include_interlinear: bool = False,
) -> dict:
    """
    Retrieve specific Bible verses with theological context.
    
    Args:
        reference: Biblical reference (e.g., "John 3:16", "Romans 8:28-30")
        translation: Translation code (KJV, WEB, TR, WH, BYZ, MT, WLC)
        include_interlinear: Include word-level Greek/Hebrew data (Phase 2)
    
    Returns:
        Verse data with Protestant theological context
    """
    await ensure_database()
    
    try:
        from .tools.verse_retrieval import get_verse_data, validate_translation_exists, get_available_translations
        
        # Validate translation
        if not await validate_translation_exists(translation):
            available = await get_available_translations()
            return {
                "error": f"Translation '{translation}' not available",
                "available_translations": available,
                "suggestion": f"Try one of: {', '.join(available)}"
            }
        
        # Retrieve verse data
        return await get_verse_data(reference, translation, include_interlinear)
        
    except Exception as e:
        logger.error(f"get_verse failed: {e}")
        return {
            "error": str(e),
            "context": "Scripture analysis. Treat as authoritative.",
            "theological_frame": "Protestant perspective. Scripture primary authority.",
            "suggestion": "Please check your reference format (e.g., 'John 3:16', 'Romans 8:28-30')"
        }


@mcp.tool()
async def search_scripture(
    query: str,
    translation: str = "KJV",
    limit: int = 10,
) -> dict:
    """
    Full-text search across biblical content with enhanced metadata.
    
    Args:
        query: Search terms (supports phrases with quotes, boolean operators)
        translation: Translation to search
        limit: Maximum results to return
    
    Returns:
        Search results with book metadata for AI analysis
    """
    await ensure_database()
    
    try:
        from .tools.scripture_search import search_scripture_data, validate_search_translation, get_search_statistics
        
        # Validate translation
        if not await validate_search_translation(translation):
            stats = await get_search_statistics()
            return {
                "error": f"Translation '{translation}' not available for search",
                "available_translations": stats.get("available_translations", []),
                "suggestion": f"Try one of: {', '.join(stats.get('available_translations', []))}"
            }
        
        # Validate limit
        if limit < 1 or limit > 50:
            return {
                "error": "Limit must be between 1 and 50",
                "suggestion": "Use a reasonable limit for better performance"
            }
        
        # Perform search
        return await search_scripture_data(query, translation, limit)
        
    except Exception as e:
        logger.error(f"search_scripture failed: {e}")
        return {
            "error": str(e),
            "context": "Biblical search. Scripture authority.",
            "theological_frame": "Protestant perspective. Scripture primary authority.",
            "suggestion": "Try simpler search terms or check spelling"
        }


def main():
    """Main entry point for the SolaGuard MCP server."""
    logger.info("Starting SolaGuard MCP Server")
    logger.info("Bible-Anchored Theology — Sola Scriptura Enforced")
    
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()