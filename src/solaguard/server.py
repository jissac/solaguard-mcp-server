"""
SolaGuard MCP Server

Main server implementation using FastMCP framework.
"""

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from .context import wrap_error_response, ContextType
from .validation import ValidationError, validate_biblical_reference, validate_translation, validate_search_query, validate_search_limit

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
        # Validate inputs using centralized validation
        try:
            validated_ref = await validate_biblical_reference(reference)
            validated_translation = await validate_translation(translation)
        except ValidationError as e:
            return wrap_error_response(
                e.message,
                e.suggestion,
                ContextType.VERSE_RETRIEVAL
            )
        
        from .tools.verse_retrieval import get_verse_data
        
        # Tool function handles the actual retrieval
        return await get_verse_data(reference, validated_translation, include_interlinear)
        
    except Exception as e:
        logger.error(f"get_verse failed: {e}")
        return wrap_error_response(
            str(e),
            "Please check your reference format (e.g., 'John 3:16', 'Romans 8:28-30')",
            ContextType.VERSE_RETRIEVAL
        )


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
        # Validate inputs using centralized validation
        try:
            validated_query = validate_search_query(query)
            validated_translation = await validate_translation(translation)
            validated_limit = validate_search_limit(limit)
        except ValidationError as e:
            return wrap_error_response(
                e.message,
                e.suggestion,
                ContextType.SCRIPTURE_SEARCH
            )
        
        from .tools.scripture_search import search_scripture_data
        
        # Tool function handles the actual search with validated inputs
        return await search_scripture_data(validated_query, validated_translation, validated_limit)
        
    except Exception as e:
        logger.error(f"search_scripture failed: {e}")
        return wrap_error_response(
            str(e),
            "Try simpler search terms or check spelling",
            ContextType.SCRIPTURE_SEARCH
        )


def main():
    """Main entry point for the SolaGuard MCP server."""
    logger.info("Starting SolaGuard MCP Server")
    logger.info("Bible-Anchored Theology — Sola Scriptura Enforced")
    
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()