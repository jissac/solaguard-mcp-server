#!/usr/bin/env python3
"""
Cross-Reference Tool Test Script

Quick test script to validate the cross-reference MCP tool implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.cross_references import get_cross_references_data, get_cross_reference_stats


async def test_cross_reference_tool():
    """Test the cross-reference tool with various inputs."""
    print("🔗 Testing Cross-Reference Tool")
    print("=" * 50)
    
    # Initialize database
    from solaguard.database import initialize_database
    db_path = Path("data/bible.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    await initialize_database(db_path)
    print(f"✅ Database initialized: {db_path}")
    
    # Test cases
    test_cases = [
        ("Genesis 1:1", "KJV", 5),
        ("John 3:16", "BSB", 3),
        ("Psalm 23:1", "KJV", 10),
        ("Romans 8:28", "BSB", 5),
    ]
    
    for reference, translation, limit in test_cases:
        print(f"\n📖 Testing: {reference} ({translation}, limit={limit})")
        print("-" * 40)
        
        try:
            # Get cross-references
            result = await get_cross_references_data(reference, translation, limit)
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                continue
            
            # Display results
            source = result.get("source_verse", {})
            cross_refs = result.get("cross_references", [])
            metadata = result.get("metadata", {})
            
            print(f"✅ Source: {source.get('reference', 'Unknown')}")
            print(f"   Text: {source.get('text', 'N/A')[:60]}...")
            print(f"   Translation: {source.get('translation', 'Unknown')}")
            
            print(f"\n🔍 Found {metadata.get('total_found', 0)} cross-references:")
            for i, ref in enumerate(cross_refs, 1):
                print(f"  {i}. {ref.get('reference', 'Unknown')}")
                print(f"     {ref.get('text', 'N/A')[:50]}...")
                print(f"     ({ref.get('translation', 'Unknown')}, {ref.get('relationship_type', 'unknown')})")
            
            # Show metadata
            testament_dist = metadata.get("testament_distribution", {})
            print(f"\n📊 Testament distribution: OT={testament_dist.get('old_testament', 0)}, NT={testament_dist.get('new_testament', 0)}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test statistics
    print(f"\n📈 Testing Cross-Reference Statistics")
    print("-" * 40)
    
    stat_tests = ["Genesis 1:1", "John 3:16", "Psalm 23:1"]
    for ref in stat_tests:
        try:
            stats = await get_cross_reference_stats(ref)
            print(f"{ref}: {stats.get('total_cross_references', 0)} cross-references")
        except Exception as e:
            print(f"{ref}: Error - {e}")


async def main():
    """Main test function."""
    try:
        await test_cross_reference_tool()
        print(f"\n✅ Cross-reference tool testing complete!")
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())