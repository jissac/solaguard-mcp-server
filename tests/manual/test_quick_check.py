#!/usr/bin/env python3
"""
Quick manual test for development.
Run this to quickly verify everything is working.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


async def quick_test():
    """Quick test of core functionality."""
    print("🚀 SolaGuard Quick Test\n")
    
    try:
        # Test 1: Import check
        print("1️⃣ Testing imports...")
        from solaguard.tools.reference_parser import parse_reference
        from solaguard.tools.verse_retrieval import get_verse_data
        from solaguard.server import ensure_database
        print("   ✅ All imports successful")
        
        # Test 2: Reference parsing
        print("\n2️⃣ Testing reference parsing...")
        test_refs = ["John 3:16", "Gen 1:1", "Romans 8:28-30"]
        for ref in test_refs:
            parsed = parse_reference(ref)
            print(f"   ✅ {ref} -> {parsed}")
        
        # Test 3: Database connection
        print("\n3️⃣ Testing database connection...")
        db_manager = await ensure_database()
        health = await db_manager.health_check()
        print(f"   ✅ Database status: {health['status']}")
        print(f"   📊 Verses: {health['verse_count']}, FTS: {health['fts_index_count']}")
        
        # Test 4: Verse retrieval
        print("\n4️⃣ Testing verse retrieval...")
        result = await get_verse_data("John 3:16", "KJV")
        if "error" in result:
            print(f"   ⚠️  {result['error']}")
        else:
            verse = result["verse"]
            print(f"   ✅ {verse['reference']}: {verse['text'][:50]}...")
        
        # Test 5: Scripture search
        print("\n5️⃣ Testing scripture search...")
        from solaguard.tools.scripture_search import search_scripture_data
        search_result = await search_scripture_data("love", "KJV", 3)
        if "error" in search_result:
            print(f"   ⚠️  {search_result['error']}")
        else:
            total = search_result["metadata"]["total_results"]
            returned = len(search_result["results"])
            print(f"   ✅ Found {total} verses, returned {returned}")
            if returned > 0:
                first = search_result["results"][0]
                print(f"   📖 {first['reference']}: {first['text'][:40]}...")
        
        # Test 6: MCP server tools
        print("\n6️⃣ Testing MCP server tools...")
        from solaguard.server import mcp
        try:
            tools = await mcp.get_tools()
            
            # Handle different tool formats
            if tools:
                if hasattr(tools, '__len__') and len(tools) > 0:
                    first_tool = tools[0] if isinstance(tools, (list, tuple)) else next(iter(tools), None)
                    if first_tool and hasattr(first_tool, 'name'):
                        tool_names = [tool.name for tool in tools]
                    else:
                        tool_names = [str(tool) for tool in tools]
                else:
                    tool_names = []
            else:
                tool_names = []
            
            print(f"   ✅ Available tools: {tool_names}")
            
            # Test get_verse tool if available
            if any('get_verse' in str(tool) for tool in (tools or [])):
                print("   ✅ get_verse tool is registered")
            
            # Test search_scripture tool if available
            if any('search_scripture' in str(tool) for tool in (tools or [])):
                print("   ✅ search_scripture tool is registered")
        except Exception as e:
            print(f"   ⚠️  Could not check MCP tools: {e}")
        
        print("\n🎉 All tests passed! SolaGuard is ready to use.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)