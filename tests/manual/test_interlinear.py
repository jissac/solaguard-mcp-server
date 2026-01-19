#!/usr/bin/env python3
"""
Test script for interlinear data functionality.

Tests the get_verse tool with include_interlinear=True to verify
word-level Greek/Hebrew data is properly retrieved and formatted.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.verse_retrieval import get_verse_data
from solaguard.database.connection import initialize_database


async def test_interlinear():
    """Test interlinear data retrieval."""
    
    # Initialize database
    db_path = Path(__file__).parent.parent / "data" / "bible.db"
    await initialize_database(db_path)
    
    print("=" * 80)
    print("Testing Interlinear Data Functionality")
    print("=" * 80)
    print()
    
    # Test 1: Single verse without interlinear
    print("Test 1: John 3:16 (without interlinear)")
    print("-" * 80)
    result = await get_verse_data("John 3:16", "KJV", include_interlinear=False)
    if "verse" in result:
        print(f"Reference: {result['verse']['reference']}")
        print(f"Text: {result['verse']['text']}")
        print(f"Interlinear included: {result['metadata'].get('interlinear_included', False)}")
    else:
        print(f"Error: {result}")
    print()
    
    # Test 2: Single verse with interlinear
    print("Test 2: John 3:16 (with interlinear)")
    print("-" * 80)
    result = await get_verse_data("John 3:16", "KJV", include_interlinear=True)
    if "verse" in result:
        print(f"Reference: {result['verse']['reference']}")
        print(f"Text: {result['verse']['text']}")
        print(f"Interlinear included: {result['metadata'].get('interlinear_included', False)}")
        
        if "interlinear" in result["verse"]:
            interlinear = result["verse"]["interlinear"]
            if interlinear.get("available"):
                print(f"\nWord count: {interlinear['word_count']}")
                print("\nWord-by-word breakdown:")
                strongs_header = "Strong's"
                print(f"{'Seq':<5} {'English':<15} {strongs_header:<10} {'Transliteration':<20} {'Original':<15}")
                print("-" * 75)
                for word in interlinear["words"][:10]:  # Show first 10 words
                    seq = word.get("sequence", "")
                    eng = word.get("english", "")
                    strongs = word.get("strongs", "")
                    trans = word.get("transliteration", "")
                    orig = word.get("original", "")
                    print(f"{seq:<5} {eng:<15} {strongs:<10} {trans:<20} {orig:<15}")
                
                if len(interlinear["words"]) > 10:
                    print(f"... and {len(interlinear['words']) - 10} more words")
            else:
                print(f"\nNote: {interlinear.get('note', 'No interlinear data')}")
    else:
        print(f"Error: {result}")
    print()
    
    # Test 3: Verse range with interlinear
    print("Test 3: Romans 8:28-30 (with interlinear)")
    print("-" * 80)
    result = await get_verse_data("Romans 8:28-30", "KJV", include_interlinear=True)
    if "verse" in result:
        print(f"Reference: {result['verse']['reference']}")
        print(f"Verse count: {result['metadata']['verse_count']}")
        print(f"Interlinear included: {result['metadata'].get('interlinear_included', False)}")
        
        if "individual_verses" in result["verse"]:
            for verse in result["verse"]["individual_verses"]:
                print(f"\n{verse['reference']}:")
                if "interlinear" in verse and verse["interlinear"].get("available"):
                    print(f"  Word count: {verse['interlinear']['word_count']}")
                    # Show first 5 words of each verse
                    for word in verse["interlinear"]["words"][:5]:
                        eng = word.get("english", "")
                        strongs = word.get("strongs", "")
                        print(f"    {eng} ({strongs})")
    else:
        print(f"Error: {result}")
    print()
    
    # Test 4: Old Testament verse with Hebrew
    print("Test 4: Genesis 1:1 (with interlinear - Hebrew)")
    print("-" * 80)
    result = await get_verse_data("Genesis 1:1", "KJV", include_interlinear=True)
    if "verse" in result:
        print(f"Reference: {result['verse']['reference']}")
        print(f"Text: {result['verse']['text']}")
        
        if "interlinear" in result["verse"]:
            interlinear = result["verse"]["interlinear"]
            if interlinear.get("available"):
                print(f"\nWord count: {interlinear['word_count']}")
                print("\nHebrew word breakdown:")
                strongs_header = "Strong's"
                print(f"{'Seq':<5} {'English':<15} {strongs_header:<10} {'Transliteration':<20}")
                print("-" * 60)
                for word in interlinear["words"]:
                    seq = word.get("sequence", "")
                    eng = word.get("english", "")
                    strongs = word.get("strongs", "")
                    trans = word.get("transliteration", "")
                    print(f"{seq:<5} {eng:<15} {strongs:<10} {trans:<20}")
            else:
                print(f"\nNote: {interlinear.get('note', 'No interlinear data')}")
    else:
        print(f"Error: {result}")
    print()
    
    print("=" * 80)
    print("Interlinear Testing Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_interlinear())
