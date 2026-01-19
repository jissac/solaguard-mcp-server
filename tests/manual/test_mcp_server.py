#!/usr/bin/env python3
"""
Test MCP Server Integration

Quick test to verify all MCP tools are properly integrated.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.server import ensure_database
from solaguard.database import initialize_database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_server_tools():
    """Test that all MCP tools can be imported and initialized."""
    
    # Initialize database
    db_path = Path("data/bible.db")
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return False
    
    try:
        await initialize_database(db_path)
        await ensure_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False
    
    # Test tool imports
    tools_to_test = [
        ("get_verse", "solaguard.tools.verse_retrieval"),
        ("search_scripture", "solaguard.tools.scripture_search"), 
        ("get_cross_references", "solaguard.tools.cross_references"),
        ("get_strongs", "solaguard.tools.strongs_study"),
        ("get_book_info", "solaguard.tools.book_info"),
    ]
    
    print("\n" + "="*60)
    print("MCP SERVER TOOL INTEGRATION TEST")
    print("="*60)
    
    success_count = 0
    
    for tool_name, module_name in tools_to_test:
        try:
            # Import the module
            __import__(module_name)
            print(f"✅ {tool_name}: Module imported successfully")
            success_count += 1
        except Exception as e:
            print(f"❌ {tool_name}: Import failed - {e}")
    
    # Test server module
    try:
        from solaguard import server
        print(f"✅ Server module: Imported successfully")
        success_count += 1
    except Exception as e:
        print(f"❌ Server module: Import failed - {e}")
    
    print(f"\n📊 Results: {success_count}/{len(tools_to_test) + 1} tools ready")
    
    if success_count == len(tools_to_test) + 1:
        print("🎉 All MCP tools are properly integrated!")
        return True
    else:
        print("⚠️  Some tools have integration issues")
        return False


async def test_context_integration():
    """Test that theological context is properly integrated."""
    
    print("\n" + "="*60)
    print("THEOLOGICAL CONTEXT INTEGRATION TEST")
    print("="*60)
    
    try:
        from solaguard.context import (
            ContextType, wrap_verse_response, wrap_search_response,
            wrap_cross_reference_response, wrap_strongs_response, wrap_error_response
        )
        
        # Test each context type
        context_functions = [
            ("ContextType.VERSE_RETRIEVAL", ContextType.VERSE_RETRIEVAL),
            ("ContextType.SCRIPTURE_SEARCH", ContextType.SCRIPTURE_SEARCH),
            ("ContextType.CROSS_REFERENCE", ContextType.CROSS_REFERENCE),
            ("ContextType.STRONGS_STUDY", ContextType.STRONGS_STUDY),
            ("ContextType.ERROR_RESPONSE", ContextType.ERROR_RESPONSE),
        ]
        
        for name, context_type in context_functions:
            print(f"✅ {name}: Available")
        
        # Test wrapper functions
        wrapper_functions = [
            ("wrap_verse_response", wrap_verse_response),
            ("wrap_search_response", wrap_search_response),
            ("wrap_cross_reference_response", wrap_cross_reference_response),
            ("wrap_strongs_response", wrap_strongs_response),
            ("wrap_error_response", wrap_error_response),
        ]
        
        for name, func in wrapper_functions:
            print(f"✅ {name}: Available")
        
        print("🎉 All theological context functions are integrated!")
        return True
        
    except Exception as e:
        print(f"❌ Context integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting MCP Server Integration Tests")
    
    # Test tool integration
    tools_success = await test_server_tools()
    
    # Test context integration
    context_success = await test_context_integration()
    
    # Overall result
    if tools_success and context_success:
        logger.info("🎉 MCP Server is fully integrated and ready!")
        print("\n" + "="*60)
        print("🎯 NEXT STEPS:")
        print("1. Run 'uv run python src/solaguard/server.py' to start the MCP server")
        print("2. Test with MCP client tools")
        print("3. All 5 MCP tools are ready:")
        print("   - get_verse: Retrieve specific Bible verses")
        print("   - search_scripture: Full-text search across Scripture")
        print("   - get_cross_references: Find related passages")
        print("   - get_strongs: Hebrew/Greek word studies")
        print("   - get_book_info: Biblical book metadata and context")
        print("="*60)
        return True
    else:
        logger.error("❌ MCP Server integration has issues")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)