"""
SolaGuard MCP Server

Main server implementation using FastMCP framework.
"""

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from .context import wrap_error_response, ContextType
from .validation import ValidationError, validate_biblical_reference, validate_translation, validate_search_query, validate_search_limit

# Configure logging
log_level = os.getenv("SOLAGUARD_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("SolaGuard")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Store reference to the HTTP app
_http_app = None

# Global database manager
_db_manager = None


def setup_rate_limiting():
    """Setup rate limiting on the FastMCP server."""
    global _http_app
    try:
        # Get the underlying HTTP app from FastMCP
        _http_app = mcp.http_app()
        
        logger.info(f"HTTP app type: {type(_http_app)}")
        logger.info(f"HTTP app has state: {hasattr(_http_app, 'state')}")
        
        # Configure rate limiter
        _http_app.state.limiter = limiter
        logger.info("✅ Limiter added to app state")
        
        # Add custom rate limit exceeded handler
        async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
            """Custom handler for rate limit exceeded errors."""
            logger.warning(f"Rate limit exceeded for {get_remote_address(request)}: {exc.detail}")
            
            # Return user-friendly error message
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again in a few seconds.",
                    "suggestion": "Normal usage is 2-3 requests per minute. Please wait before making more requests.",
                    "retry_after": "60 seconds",
                    "context": "SolaGuard MCP Server protects against abuse while serving legitimate users."
                }
            )
        
        # Add the exception handler
        _http_app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
        logger.info("✅ Exception handler added")
        
        # Add health check endpoint for container orchestration
        @_http_app.get("/health")
        async def health_check():
            """Health check endpoint for Docker, Kubernetes, and hosting platforms."""
            try:
                # Check if database is accessible
                db_status = "unknown"
                db_path = Path(os.getenv("SOLAGUARD_DATABASE_PATH", "data/bible.db"))
                
                if db_path.exists():
                    # Try to query database
                    try:
                        await ensure_database()
                        db_manager = get_database_manager()
                        async with db_manager.get_connection() as conn:
                            cursor = await conn.execute("SELECT COUNT(*) FROM verses LIMIT 1")
                            await cursor.fetchone()
                        db_status = "connected"
                    except Exception as e:
                        logger.error(f"Database health check failed: {e}")
                        db_status = "error"
                else:
                    db_status = "missing"
                
                # Determine overall health
                is_healthy = db_status == "connected"
                status_code = 200 if is_healthy else 503
                
                return JSONResponse(
                    status_code=status_code,
                    content={
                        "status": "healthy" if is_healthy else "unhealthy",
                        "service": "SolaGuard MCP Server",
                        "version": "0.1.0",
                        "database": {
                            "status": db_status,
                            "path": str(db_path)
                        },
                        "features": {
                            "mcp_tools": 8,
                            "rate_limiting": "enabled",
                            "theological_context": "enabled"
                        }
                    }
                )
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "error": str(e)
                    }
                )
        
        logger.info("✅ Health check endpoint added at /health")
        
        # Add rate limiting middleware using the new approach
        from starlette.middleware.base import BaseHTTPMiddleware
        
        class RateLimitMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    # Check rate limit
                    await limiter.check_request(request, "20/minute")
                    response = await call_next(request)
                    return response
                except RateLimitExceeded as e:
                    return await rate_limit_handler(request, e)
        
        _http_app.add_middleware(RateLimitMiddleware)
        logger.info("✅ Middleware added")
        
        logger.info("🛡️ Rate limiting configured: 20 requests per minute per IP")
        
    except Exception as e:
        logger.error(f"Failed to setup rate limiting: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail startup if rate limiting setup fails
        pass


def get_http_app():
    """Get the configured HTTP app."""
    return _http_app


async def ensure_database():
    """Ensure database is initialized."""
    global _db_manager
    if _db_manager is None:
        logger.info("🚀 Starting SolaGuard MCP Server")
        logger.info("📖 Bible-Anchored Theology — Sola Scriptura Enforced")
        logger.info("🔗 Universal theological infrastructure for AI applications")
        
        # Initialize database connection
        from .database import initialize_database, get_database_manager
        
        db_path = Path(os.getenv("SOLAGUARD_DATABASE_PATH", "data/bible.db"))
        
        try:
            await initialize_database(db_path)
            _db_manager = get_database_manager()
            logger.info(f"📚 Database initialized: {db_path}")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            logger.info("💡 Run 'python scripts/generate_mock_data.py' to create test database")
            raise
    
    return _db_manager


def get_database_manager():
    """Get the global database manager instance."""
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
async def get_verse_context(
    reference: str,
    before: int = 2,
    after: int = 2,
    translation: str = "KJV",
) -> dict:
    """
    Get a verse with surrounding context for better interpretation.
    
    Retrieves the requested verse plus surrounding verses to provide context
    that aids in proper biblical interpretation. The target verse is marked
    for easy identification.
    
    Args:
        reference: Single verse reference (e.g., "John 3:16", "Romans 8:28")
        before: Number of verses before target (default: 2, max: 10)
        after: Number of verses after target (default: 2, max: 10)
        translation: Translation code (KJV, BSB, etc.)
    
    Returns:
        Target verse plus surrounding context, with target marked
        
    Example:
        get_verse_context("John 3:16", before=2, after=2)
        Returns John 3:14-18 with verse 16 marked as target
    """
    await ensure_database()
    
    try:
        # Validate inputs
        try:
            validated_ref = await validate_biblical_reference(reference)
            validated_translation = await validate_translation(translation)
        except ValidationError as e:
            return wrap_error_response(
                e.message,
                e.suggestion,
                ContextType.VERSE_RETRIEVAL
            )
        
        from .tools.verse_context import get_verse_context_data
        
        # Tool function handles the actual context retrieval
        return await get_verse_context_data(
            reference, 
            before, 
            after, 
            validated_translation
        )
        
    except Exception as e:
        logger.error(f"get_verse_context failed: {e}")
        return wrap_error_response(
            str(e),
            "Please check your reference format (e.g., 'John 3:16'). Use a single verse, not a range.",
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


@mcp.tool()
async def get_cross_references(
    reference: str,
    translation: str = "KJV",
    limit: int = 10,
) -> dict:
    """
    Find thematically related Bible passages with translation-agnostic logic.
    
    Args:
        reference: Biblical reference (e.g., "John 3:16", "Genesis 1:1")
        translation: Translation to return results in (KJV, BSB, etc.)
        limit: Maximum number of cross-references to return (1-50)
    
    Returns:
        Cross-reference data with Protestant theological context
    """
    await ensure_database()
    
    try:
        # Validate inputs using centralized validation
        try:
            validated_ref = await validate_biblical_reference(reference)
            validated_translation = await validate_translation(translation)
            validated_limit = max(1, min(limit, 50))  # Clamp between 1-50
        except ValidationError as e:
            return wrap_error_response(
                e.message,
                e.suggestion,
                ContextType.CROSS_REFERENCE
            )
        
        from .tools.cross_references import get_cross_references_data
        
        # Tool function handles the actual cross-reference discovery
        return await get_cross_references_data(reference, validated_translation, validated_limit)
        
    except Exception as e:
        logger.error(f"get_cross_references failed: {e}")
        return wrap_error_response(
            str(e),
            "Please check your reference format (e.g., 'John 3:16', 'Genesis 1:1')",
            ContextType.CROSS_REFERENCE
        )


@mcp.tool()
async def search_by_topic(
    topic: str,
    translation: str = "KJV",
    limit: int = 20,
    expand_cross_refs: bool = True,
) -> dict:
    """
    Search for verses related to theological topics using semantic expansion.
    
    Args:
        topic: Topic or concept to search for (e.g., "salvation", "God's love", "prayer")
        translation: Translation to return results in (KJV, BSB, etc.)
        limit: Maximum number of results to return (1-50)
        expand_cross_refs: Whether to expand results using cross-references
    
    Returns:
        Topical search results with theological context
    """
    await ensure_database()
    
    try:
        # Validate inputs using centralized validation
        try:
            validated_translation = await validate_translation(translation)
            validated_limit = max(1, min(limit, 50))  # Clamp between 1-50
        except ValidationError as e:
            return wrap_error_response(
                e.message,
                e.suggestion,
                ContextType.SCRIPTURE_SEARCH
            )
        
        from .tools.topical_search_db import search_by_topic_data
        
        # Tool function handles the actual topical search
        return await search_by_topic_data(topic, validated_translation, validated_limit, expand_cross_refs)
        
    except Exception as e:
        logger.error(f"search_by_topic failed: {e}")
        return wrap_error_response(
            str(e),
            "Try common theological topics like: salvation, love, prayer, faith, grace, sin, forgiveness",
            ContextType.SCRIPTURE_SEARCH
        )


@mcp.tool()
async def get_book_info(
    book_name: str,
    include_stats: bool = True,
) -> dict:
    """
    Retrieve comprehensive biblical book information and metadata.
    
    Args:
        book_name: Book name (e.g., "Genesis", "Gen", "John", "1 Corinthians")
        include_stats: Include chapter/verse statistics and related books
    
    Returns:
        Book metadata with Protestant theological context
    """
    await ensure_database()
    
    try:
        from .tools.book_info import get_book_info_data
        
        # Tool function handles the actual book info retrieval
        return await get_book_info_data(book_name, include_stats)
        
    except Exception as e:
        logger.error(f"get_book_info failed: {e}")
        return wrap_error_response(
            str(e),
            "Please check the book name. Try full names (Genesis, Exodus) or common abbreviations (Gen, Ex, Matt, John)",
            ContextType.VERSE_RETRIEVAL
        )


@mcp.tool()
async def get_strongs(
    strongs_number: str,
    translation: str = "KJV",
    limit: int = 20,
) -> dict:
    """
    Perform Hebrew or Greek word study using Strong's Concordance numbers.
    
    Args:
        strongs_number: Strong's number (e.g., "G25", "H157", "g25", "h157")
        translation: Translation to return verse results in (KJV, BSB, etc.)
        limit: Maximum number of verse occurrences to return (1-100)
    
    Returns:
        Strong's word study data with Protestant theological context
    """
    await ensure_database()
    
    try:
        # Validate inputs using centralized validation
        try:
            validated_translation = await validate_translation(translation)
            validated_limit = max(1, min(limit, 100))  # Clamp between 1-100
        except ValidationError as e:
            return wrap_error_response(
                e.message,
                e.suggestion,
                ContextType.STRONGS_STUDY
            )
        
        from .tools.strongs_study import get_strongs_data
        
        # Tool function handles the actual Strong's word study
        return await get_strongs_data(strongs_number, validated_translation, validated_limit)
        
    except Exception as e:
        logger.error(f"get_strongs failed: {e}")
        return wrap_error_response(
            str(e),
            "Please check your Strong's number format (e.g., 'G25', 'H157', 'g25', 'h157')",
            ContextType.STRONGS_STUDY
        )


def main():
    """Main entry point for the SolaGuard MCP server."""
    logger.info("Starting SolaGuard MCP Server")
    logger.info("Bible-Anchored Theology — Sola Scriptura Enforced")
    
    # Setup rate limiting
    setup_rate_limiting()
    
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()