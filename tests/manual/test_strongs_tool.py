#!/usr/bin/env python3
"""
Test Strong's Word Study Tool

Tests the get_strongs MCP tool functionality with various Strong's numbers.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.strongs_study import get_strongs_data, StrongsStudyError
from solaguard.database import initialize_database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_strongs_tool():
    """Test the Strong's word study tool with various inputs."""
    
    # Initialize database
    db_path = Path("data/bible.db")
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.info("Run 'uv run python scripts/ingest_bible.py' first")
        return False
    
    try:
        await initialize_database(db_path)
        logger.info(f"✅ Database initialized: {db_path}")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False
    
    # Test cases
    test_cases = [
        {
            "name": "Greek word - agape (love)",
            "strongs": "G25",
            "translation": "KJV",
            "limit": 5
        },
        {
            "name": "Hebrew word - ahab (love)",
            "strongs": "H157", 
            "translation": "BSB",
            "limit": 3
        },
        {
            "name": "Greek word - logos (word)",
            "strongs": "G3056",
            "translation": "KJV",
            "limit": 10
        },
        {
            "name": "Hebrew word - elohim (God)",
            "strongs": "H430",
            "translation": "KJV",
            "limit": 8
        },
        {
            "name": "Lowercase format test",
            "strongs": "g25",
            "translation": "KJV",
            "limit": 2
        },
        {
            "name": "Number only format test",
            "strongs": "157",
            "translation": "KJV",
            "limit": 2
        },
        {
            "name": "Invalid Strong's number",
            "strongs": "G99999",
            "translation": "KJV",
            "limit": 5
        },
        {
            "name": "Invalid format",
            "strongs": "invalid",
            "translation": "KJV",
            "limit": 5
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    print("\n" + "="*80)
    print("STRONG'S WORD STUDY TOOL TEST")
    print("="*80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] Testing: {test_case['name']}")
        print(f"Strong's: {test_case['strongs']}, Translation: {test_case['translation']}, Limit: {test_case['limit']}")
        print("-" * 60)
        
        try:
            result = await get_strongs_data(
                strongs_number=test_case['strongs'],
                translation=test_case['translation'],
                limit=test_case['limit']
            )
            
            # Check if it's an error response
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                print(f"💡 Suggestion: {result['suggestion']}")
                if "invalid" in test_case['name'].lower():
                    print("✅ Expected error for invalid input")
                    success_count += 1
            else:
                # Success response
                entry = result.get('strongs_entry', {})
                stats = result.get('usage_statistics', {})
                verses = result.get('verse_occurrences', [])
                related = result.get('related_words', [])
                
                print(f"✅ Strong's Number: {entry.get('strongs_number', 'N/A')}")
                print(f"📖 Original Word: {entry.get('original_word', 'N/A')}")
                print(f"🔤 Transliteration: {entry.get('transliteration', 'N/A')}")
                print(f"📝 Definition: {entry.get('definition', 'N/A')[:100]}...")
                print(f"🌍 Language: {entry.get('language', 'N/A')}")
                print(f"📊 Total Occurrences: {stats.get('total_occurrences', 0)}")
                print(f"📄 Unique Verses: {stats.get('unique_verses', 0)}")
                print(f"📚 Verses Shown: {len(verses)}")
                print(f"🔗 Related Words: {len(related)}")
                
                # Show first verse occurrence
                if verses:
                    first_verse = verses[0]
                    print(f"📖 First Occurrence: {first_verse.get('reference', 'N/A')}")
                    print(f"   Text: {first_verse.get('text', 'N/A')[:80]}...")
                
                # Show theological context
                if 'instruction' in result:
                    print(f"⛪ Theological Context: {result['instruction'][:100]}...")
                
                success_count += 1
                
        except StrongsStudyError as e:
            print(f"❌ Strong's Study Error: {e}")
            if "invalid" in test_case['name'].lower():
                print("✅ Expected error for invalid input")
                success_count += 1
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False


async def test_search_functions():
    """Test additional Strong's search functions."""
    
    print("\n" + "="*80)
    print("STRONG'S SEARCH FUNCTIONS TEST")
    print("="*80)
    
    try:
        from solaguard.tools.strongs_study import search_strongs_by_word, get_strongs_range_info
        
        # Test word search
        print("\n[1] Testing word search for 'love':")
        results = await search_strongs_by_word("love", "both")
        print(f"✅ Found {len(results)} Strong's entries containing 'love'")
        for result in results[:3]:  # Show first 3
            print(f"   {result['number']}: {result['word']} ({result['language']})")
        
        # Test range info
        print("\n[2] Testing Greek range info (G1-G100):")
        range_info = await get_strongs_range_info(1, 100, "greek")
        print(f"✅ Range info: {range_info}")
        
        print("\n[3] Testing Hebrew range info (H1-H100):")
        range_info = await get_strongs_range_info(1, 100, "hebrew")
        print(f"✅ Range info: {range_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Search functions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting Strong's Word Study Tool Tests")
    
    # Test main tool
    tool_success = await test_strongs_tool()
    
    # Test search functions
    search_success = await test_search_functions()
    
    # Overall result
    if tool_success and search_success:
        logger.info("🎉 All Strong's tool tests completed successfully!")
        return True
    else:
        logger.error("❌ Some Strong's tool tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)