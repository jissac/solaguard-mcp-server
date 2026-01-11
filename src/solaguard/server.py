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
        logging.StreamHandler(sys.stdout),
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
    
    # Setup rate limiting
    setup_rate_limiting()
    
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()