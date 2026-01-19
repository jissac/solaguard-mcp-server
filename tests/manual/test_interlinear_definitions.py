#!/usr/bin/env python3
"""
Test script for interlinear data with definitions.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.verse_retrieval import get_verse_data
from solaguard.database.connection import initialize_database


async def test_with_definitions():
    """Test interlinear data with definitions."""
    
    # Initialize database
    db_path = Path(__file__).parent.parent / "data" / "bible.db"
    await initialize_database(db_path)
    
    print("=" * 80)
    print("Testing Interlinear with Definitions")
    print("=" * 80)
    print()
    
    # Test: John 3:16 with definitions
    print("John 3:16 (with interlinear + definitions)")
    print("-" * 80)
    result = await get_verse_data("John 3:16", "KJV", include_interlinear=True, include_definitions=True)
    
    if "verse" in result:
        print(f"Reference: {result['verse']['reference']}")
        print(f"Text: {result['verse']['text']}")
        print()
        
        if "interlinear" in result["verse"] and result["verse"]["interlinear"].get("available"):
            interlinear = result["verse"]["interlinear"]
            print(f"Word count: {interlinear['word_count']}")
            print()
            
            # Show first 5 words with full details
            for i, word in enumerate(interlinear["words"][:5], 1):
                print(f"Word {i}: {word.get('english', '')}")
                print(f"  Strong's: {word.get('strongs', 'N/A')}")
                print(f"  Original: {word.get('original', 'N/A')}")
                print(f"  Transliteration: {word.get('transliteration', 'N/A')}")
                print(f"  Pronunciation: {word.get('pronunciation', 'N/A')}")
                if 'definition' in word:
                    # Truncate long definitions
                    definition = word['definition']
                    if len(definition) > 100:
                        definition = definition[:100] + "..."
                    print(f"  Definition: {definition}")
                if 'part_of_speech' in word:
                    print(f"  Part of Speech: {word['part_of_speech']}")
                print()
    else:
        print(f"Error: {result}")
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_with_definitions())
