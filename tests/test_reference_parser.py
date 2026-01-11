"""
Unit tests for biblical reference parser.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.reference_parser import (
    parse_reference,
    VerseReference,
    VerseRange,
    ReferenceParseError,
    normalize_book_name,
    format_reference,
    get_book_display_name
)


class TestReferenceParser:
    """Test cases for biblical reference parsing."""
    
    def test_single_verse_parsing(self):
        """Test parsing single verse references."""
        test_cases = [
            ("John 3:16", "JHN", 3, 16),
            ("Gen 1:1", "GEN", 1, 1),
            ("Psalm 23:1", "PSA", 23, 1),
            ("1 Cor 13:4", "1CO", 13, 4),
            ("2 Timothy 3:16", "2TI", 3, 16),
            ("Rev 21:4", "REV", 21, 4),
        ]
        
        for ref_str, expected_book, expected_chapter, expected_verse in test_cases:
            result = parse_reference(ref_str)
            assert isinstance(result, VerseReference)
            assert result.book_id == expected_book
            assert result.chapter == expected_chapter
            assert result.verse == expected_verse
    
    def test_verse_range_parsing(self):
        """Test parsing verse range references."""
        test_cases = [
            ("Romans 8:28-30", "ROM", 8, 28, 30),
            ("1 Cor 13:4-7", "1CO", 13, 4, 7),
            ("Matt 5:3-12", "MAT", 5, 3, 12),
            ("John 3:16-17", "JHN", 3, 16, 17),
        ]
        
        for ref_str, expected_book, expected_chapter, start_verse, end_verse in test_cases:
            result = parse_reference(ref_str)
            assert isinstance(result, VerseRange)
            assert result.book_id == expected_book
            assert result.chapter == expected_chapter
            assert result.start_verse == start_verse
            assert result.end_verse == end_verse
    
    def test_invalid_references(self):
        """Test that invalid references raise appropriate errors."""
        invalid_cases = [
            "",
            "   ",
            "Invalid 3:16",
            "John",
            "John 3",
            "John 3:",
            "John 0:16",
            "John 3:0",
            "John 3:16-15",  # End before start
            "Not a reference",
        ]
        
        for invalid_ref in invalid_cases:
            with pytest.raises(ReferenceParseError):
                parse_reference(invalid_ref)
    
    def test_format_reference(self):
        """Test reference formatting."""
        test_cases = [
            ("JHN", 3, 16, "John 3:16"),
            ("GEN", 1, 1, "Genesis 1:1"),
            ("PSA", 23, 1, "Psalms 23:1"),
            ("1CO", 13, 4, "1 Corinthians 13:4"),
        ]
        
        for book_id, chapter, verse, expected in test_cases:
            result = format_reference(book_id, chapter, verse)
            assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])