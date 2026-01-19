#!/usr/bin/env python3
"""
Test script for the verse context tool.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.database import initialize_database
from solaguard.tools.verse_context import get_verse_context_data


async def test_verse_context():
    """Test the verse context tool."""
    
    # Initialize database
    db_path = Path("data/bible.db")
    await initialize_database(db_path)
    
    print("=" * 60)
    print("VERSE CONTEXT TOOL TEST")
    print("=" * 60)
    
    # Test 1: Basic context retrieval
    print("\n1️⃣ Test: John 3:16 with 2 verses before and after")
    print("-" * 60)
    result = await get_verse_context_data("John 3:16", before=2, after=2)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Context range: {result['metadata']['context_range']}")
        print(f"✅ Verse count: {result['metadata']['verse_count']}")
        print(f"\nTarget verse:")
        target = result['target_verse']
        print(f"  {target['reference']}: {target['text'][:80]}...")
        print(f"\nAll verses:")
        for v in result['context_verses']:
            marker = "→" if v['is_target'] else " "
            print(f"  {marker} {v['reference']}: {v['text'][:60]}...")
    
    # Test 2: Chapter boundary (start)
    print("\n\n2️⃣ Test: John 3:1 with 2 verses before (should start at v1)")
    print("-" * 60)
    result = await get_verse_context_data("John 3:1", before=2, after=2)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Context range: {result['metadata']['context_range']}")
        print(f"✅ Verse count: {result['metadata']['verse_count']}")
        if result['metadata'].get('context_notes'):
            print(f"✅ Notes: {result['metadata']['context_notes']}")
    
    # Test 3: Large context
    print("\n\n3️⃣ Test: Romans 8:28 with 5 verses before and after")
    print("-" * 60)
    result = await get_verse_context_data("Romans 8:28", before=5, after=5)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Context range: {result['metadata']['context_range']}")
        print(f"✅ Verse count: {result['metadata']['verse_count']}")
        print(f"\nTarget verse:")
        target = result['target_verse']
        print(f"  {target['reference']}: {target['text']}")
    
    # Test 4: Error case - range instead of single verse
    print("\n\n4️⃣ Test: Error handling - range instead of single verse")
    print("-" * 60)
    result = await get_verse_context_data("John 3:16-17", before=2, after=2)
    
    if "error" in result:
        print(f"✅ Correctly rejected: {result['error']}")
        print(f"   Suggestion: {result['suggestion']}")
    else:
        print(f"❌ Should have rejected range reference")
    
    # Test 5: Different translation
    print("\n\n5️⃣ Test: BSB translation")
    print("-" * 60)
    result = await get_verse_context_data("John 3:16", before=1, after=1, translation="BSB")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Translation: {result['metadata']['translation']}")
        print(f"✅ Context range: {result['metadata']['context_range']}")
        target = result['target_verse']
        print(f"\nTarget verse (BSB):")
        print(f"  {target['reference']}: {target['text'][:80]}...")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_verse_context())
