#!/usr/bin/env python3
"""
Full integration tests for SolaGuard MCP Server.
Tests the complete system with real database.
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from solaguard.server import ensure_database, mcp
from solaguard.tools.verse_retrieval import get_verse_data, validate_translation_exists, get_available_translations
from solaguard.tools.reference_parser import parse_reference, ReferenceParseError


class TestFullIntegration:
    """Full integration tests with real database."""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test that database initializes correctly."""
        db_manager = await ensure_database()
        assert db_manager is not None
        
        # Test database health
        health = await db_manager.health_check()
        assert health["status"] == "healthy"
        assert health["verse_count"] >= 0
    
    @pytest.mark.asyncio
    async def test_available_translations(self):
        """Test getting available translations."""
        await ensure_database()
        
        translations = await get_available_translations()
        assert isinstance(translations, list)
        assert len(translations) > 0
        assert "KJV" in translations
    
    @pytest.mark.asyncio
    async def test_translation_validation(self):
        """Test translation validation."""
        await ensure_database()
        
        # Valid translation
        assert await validate_translation_exists("KJV") is True
        
        # Invalid translation
        assert await validate_translation_exists("INVALID") is False
    
    @pytest.mark.asyncio
    async def test_verse_retrieval_integration(self):
        """Test full verse retrieval integration."""
        await ensure_database()
        
        test_cases = [
            ("John 3:16", "KJV"),
            ("Gen 1:1", "KJV"),
            ("Psalm 23:1", "KJV"),
            ("Romans 8:28", "KJV"),
        ]
        
        for reference, translation in test_cases:
            # Skip if translation not available
            if not await validate_translation_exists(translation):
                continue
                
            result = await get_verse_data(reference, translation)
            
            if "error" not in result:
                # Verify result structure
                assert "verse" in result
                assert "context" in result
                assert "theological_frame" in result
                assert "metadata" in result
                
                verse = result["verse"]
                assert verse["reference"]
                assert verse["text"]
                assert verse["book_id"]
                assert verse["chapter"] > 0
                assert verse["verse"] > 0
    
    @pytest.mark.asyncio
    async def test_verse_range_integration(self):
        """Test verse range retrieval integration."""
        await ensure_database()
        
        if not await validate_translation_exists("KJV"):
            pytest.skip("KJV translation not available")
        
        result = await get_verse_data("John 3:16-17", "KJV")
        
        if "error" not in result:
            verse = result["verse"]
            assert "verse_range" in verse or "individual_verses" in verse
            assert result["metadata"]["passage_type"] == "verse_range"
    
    @pytest.mark.asyncio
    async def test_mcp_tools_integration(self):
        """Test MCP tools integration."""
        await ensure_database()
        
        # Get registered tools
        tools = await mcp.get_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "get_verse" in tool_names
        assert "search_scripture" in tool_names
        
        # Test get_verse tool
        get_verse_tool = next(tool for tool in tools if tool.name == "get_verse")
        
        # Test with valid reference
        result = await get_verse_tool.fn(reference="John 3:16", translation="KJV")
        
        # Should either return verse data or error (if no data available)
        assert isinstance(result, dict)
        assert "context" in result
        assert "theological_frame" in result
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in integration."""
        await ensure_database()
        
        # Test invalid reference
        result = await get_verse_data("Invalid 99:99", "KJV")
        assert "error" in result
        
        # Test invalid translation
        tools = await mcp.get_tools()
        get_verse_tool = next(tool for tool in tools if tool.name == "get_verse")
        
        result = await get_verse_tool.fn(reference="John 3:16", translation="INVALID")
        assert "error" in result
        assert "available_translations" in result


class TestReferenceParsingIntegration:
    """Integration tests for reference parsing."""
    
    def test_reference_parsing_comprehensive(self):
        """Test comprehensive reference parsing."""
        test_cases = [
            ("John 3:16", "JHN", 3, 16),
            ("Gen 1:1", "GEN", 1, 1),
            ("Romans 8:28-30", "ROM", 8, 28, 30),
            ("1 Cor 13:4-7", "1CO", 13, 4, 7),
            ("Psalm 23:1", "PSA", 23, 1),
            ("Matt 5:3-12", "MAT", 5, 3, 12),
            ("Rev 21:4", "REV", 21, 4),
            ("1 John 4:8", "1JN", 4, 8),
            ("2 Timothy 3:16", "2TI", 3, 16),
        ]
        
        for test_case in test_cases:
            if len(test_case) == 4:  # Single verse
                ref_str, expected_book, expected_chapter, expected_verse = test_case
                result = parse_reference(ref_str)
                assert result.book_id == expected_book
                assert result.chapter == expected_chapter
                assert result.verse == expected_verse
            else:  # Verse range
                ref_str, expected_book, expected_chapter, start_verse, end_verse = test_case
                result = parse_reference(ref_str)
                assert result.book_id == expected_book
                assert result.chapter == expected_chapter
                assert result.start_verse == start_verse
                assert result.end_verse == end_verse
    
    def test_invalid_references_comprehensive(self):
        """Test invalid reference handling."""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])