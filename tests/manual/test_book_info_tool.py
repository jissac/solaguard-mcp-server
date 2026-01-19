#!/usr/bin/env python3
"""
Test Book Information Tool

Tests the get_book_info MCP tool functionality with various book names.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.book_info import get_book_info_data, search_books_by_criteria, get_canon_overview
from solaguard.database import initialize_database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_book_info_tool():
    """Test the book information tool with various inputs."""
    
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
            "name": "Full name - Genesis",
            "book": "Genesis",
            "include_stats": True
        },
        {
            "name": "Abbreviation - Gen",
            "book": "Gen",
            "include_stats": True
        },
        {
            "name": "New Testament - John",
            "book": "John",
            "include_stats": True
        },
        {
            "name": "Numbered book - 1 Corinthians",
            "book": "1 Corinthians",
            "include_stats": True
        },
        {
            "name": "Abbreviation - 1 Cor",
            "book": "1 Cor",
            "include_stats": False
        },
        {
            "name": "Psalms (large book)",
            "book": "Psalms",
            "include_stats": True
        },
        {
            "name": "Short book - Philemon",
            "book": "Philemon",
            "include_stats": True
        },
        {
            "name": "Case insensitive - revelation",
            "book": "revelation",
            "include_stats": True
        },
        {
            "name": "Invalid book name",
            "book": "InvalidBook",
            "include_stats": True
        },
        {
            "name": "Partial match - Corin",
            "book": "Corin",
            "include_stats": False
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    print("\n" + "="*80)
    print("BOOK INFORMATION TOOL TEST")
    print("="*80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] Testing: {test_case['name']}")
        print(f"Book: '{test_case['book']}', Include Stats: {test_case['include_stats']}")
        print("-" * 60)
        
        try:
            result = await get_book_info_data(
                book_name=test_case['book'],
                include_stats=test_case['include_stats']
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
                book_info = result.get('book_info', {})
                
                print(f"✅ Book ID: {book_info.get('book_id', 'N/A')}")
                print(f"📖 Name: {book_info.get('name', 'N/A')}")
                print(f"📜 Testament: {book_info.get('testament', 'N/A')}")
                print(f"✍️  Author: {book_info.get('author', 'N/A')}")
                print(f"📚 Genre: {book_info.get('genre', 'N/A')}")
                print(f"🔢 Canonical Order: {book_info.get('canonical_order', 'N/A')}")
                print(f"📍 Position: {book_info.get('position_description', 'N/A')}")
                
                # Show statistics if included
                if test_case['include_stats'] and 'statistics' in book_info:
                    stats = book_info['statistics']
                    print(f"📊 Chapters: {stats.get('chapters', 0)}")
                    print(f"📄 Verses: {stats.get('verses', 0)}")
                    print(f"🌍 Translations: {stats.get('available_translations', 0)}")
                
                # Show related books
                if 'related_books' in book_info:
                    related = book_info['related_books']
                    same_author = related.get('same_author', [])
                    same_genre = related.get('same_genre', [])
                    
                    if same_author:
                        print(f"👥 Same Author: {len(same_author)} books")
                    if same_genre:
                        print(f"📖 Same Genre: {len(same_genre)} books")
                
                # Show context
                if 'context' in book_info:
                    context = book_info['context']
                    print(f"🕰️  Period: {context.get('historical_period', 'N/A')}")
                    print(f"📝 Literary Type: {context.get('literary_type', 'N/A')}")
                    themes = context.get('theological_themes', [])
                    if themes:
                        print(f"⛪ Themes: {', '.join(themes[:3])}...")
                
                # Show theological context
                if 'instruction' in result:
                    print(f"🙏 Theological Context: {result['instruction'][:100]}...")
                
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
    
    if success_count >= total_tests - 1:  # Allow 1 failure for invalid book
        print("🎉 Book info tool tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False


async def test_search_functions():
    """Test additional book search functions."""
    
    print("\n" + "="*80)
    print("BOOK SEARCH FUNCTIONS TEST")
    print("="*80)
    
    try:
        # Test search by criteria
        print("\n[1] Testing search by testament (OT):")
        ot_books = await search_books_by_criteria(testament="OT")
        print(f"✅ Found {len(ot_books)} Old Testament books")
        
        print("\n[2] Testing search by author (Moses):")
        moses_books = await search_books_by_criteria(author="Moses")
        print(f"✅ Found {len(moses_books)} books by Moses:")
        for book in moses_books[:3]:
            print(f"   {book['name']} ({book['id']})")
        
        print("\n[3] Testing search by genre (Gospel):")
        gospel_books = await search_books_by_criteria(genre="Gospel")
        print(f"✅ Found {len(gospel_books)} Gospel books:")
        for book in gospel_books:
            print(f"   {book['name']} ({book['id']})")
        
        print("\n[4] Testing canon overview:")
        overview = await get_canon_overview()
        print(f"✅ Canon Overview:")
        print(f"   Total Books: {overview.get('total_books', 0)}")
        testaments = overview.get('testaments', {})
        print(f"   Old Testament: {testaments.get('old_testament', 0)} books")
        print(f"   New Testament: {testaments.get('new_testament', 0)} books")
        
        genres = overview.get('genres', [])
        print(f"   Genres: {len(genres)} different genres")
        
        authors = overview.get('top_authors', [])
        print(f"   Top Authors: {len(authors)} authors with multiple books")
        if authors:
            print(f"   Most prolific: {authors[0]['author']} ({authors[0]['books']} books)")
        
        return True
        
    except Exception as e:
        print(f"❌ Search functions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting Book Information Tool Tests")
    
    # Test main tool
    tool_success = await test_book_info_tool()
    
    # Test search functions
    search_success = await test_search_functions()
    
    # Overall result
    if tool_success and search_success:
        logger.info("🎉 All book info tool tests completed successfully!")
        print("\n" + "="*60)
        print("🎯 BOOK INFO TOOL READY:")
        print("- Comprehensive book metadata (author, genre, testament)")
        print("- Chapter/verse statistics")
        print("- Related books discovery")
        print("- Historical and theological context")
        print("- Flexible book name recognition")
        print("- Protestant theological framing")
        print("="*60)
        return True
    else:
        logger.error("❌ Some book info tool tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)