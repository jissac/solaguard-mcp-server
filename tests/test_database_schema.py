"""
Unit tests for database schema functionality.
"""

import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.database.schema import (
    create_schema,
    validate_schema,
    get_database_info,
    INITIAL_TRANSLATIONS,
    INITIAL_BOOKS
)


class TestDatabaseSchema:
    """Test cases for database schema creation and validation."""
    
    def test_create_schema(self):
        """Test database schema creation."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create schema
            create_schema(db_path)
            
            # Verify database file exists
            assert db_path.exists()
            
            # Verify tables exist
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Check main tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in cursor.fetchall()}
                
                expected_tables = {
                    "translations", "books", "verses", "verses_fts",
                    "words", "strongs_dictionary", "cross_references"
                }
                
                assert expected_tables.issubset(tables)
                
                # Check initial data
                cursor.execute("SELECT COUNT(*) FROM translations")
                translation_count = cursor.fetchone()[0]
                assert translation_count == len(INITIAL_TRANSLATIONS)
                
                cursor.execute("SELECT COUNT(*) FROM books")
                book_count = cursor.fetchone()[0]
                assert book_count == len(INITIAL_BOOKS)
        
        finally:
            # Cleanup
            if db_path.exists():
                db_path.unlink()
    
    def test_validate_schema_valid(self):
        """Test schema validation with valid database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create valid schema
            create_schema(db_path)
            
            # Validate should pass
            assert validate_schema(db_path) is True
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_validate_schema_missing_file(self):
        """Test schema validation with missing database file."""
        non_existent_path = Path("/tmp/non_existent_db.db")
        assert validate_schema(non_existent_path) is False
    
    def test_validate_schema_incomplete(self):
        """Test schema validation with incomplete database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create incomplete database (just one table)
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE translations (id TEXT PRIMARY KEY)")
            
            # Validation should fail
            assert validate_schema(db_path) is False
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_get_database_info(self):
        """Test getting database information."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)
        
        try:
            # Create schema
            create_schema(db_path)
            
            # Get database info
            info = get_database_info(db_path)
            
            # Verify info structure
            assert "translations_count" in info
            assert "books_count" in info
            assert "verses_count" in info
            assert "available_translations" in info
            assert "testament_distribution" in info
            
            # Verify counts
            assert info["translations_count"] == len(INITIAL_TRANSLATIONS)
            assert info["books_count"] == len(INITIAL_BOOKS)
            assert info["verses_count"] == 0  # No verses in base schema
            
            # Verify available translations
            expected_translations = {t[0]: t[1] for t in INITIAL_TRANSLATIONS}
            assert info["available_translations"] == expected_translations
        
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_get_database_info_missing_file(self):
        """Test getting database info for missing file."""
        non_existent_path = Path("/tmp/non_existent_db.db")
        info = get_database_info(non_existent_path)
        
        assert "error" in info
        assert "does not exist" in info["error"]
    
    def test_initial_translations_data(self):
        """Test that initial translations data is complete."""
        # Verify we have expected translations
        translation_ids = {t[0] for t in INITIAL_TRANSLATIONS}
        expected_ids = {"KJV", "WEB", "TR", "WH", "BYZ", "MT", "WLC"}
        
        assert translation_ids == expected_ids
        
        # Verify each translation has required fields
        for translation in INITIAL_TRANSLATIONS:
            assert len(translation) == 4  # id, name, language, type
            assert translation[0]  # id not empty
            assert translation[1]  # name not empty
            assert translation[2] in ["en", "grc", "hbo"]  # valid language
            assert translation[3] in ["translation", "original"]  # valid type
    
    def test_initial_books_data(self):
        """Test that initial books data is complete."""
        # Verify we have 66 canonical books
        assert len(INITIAL_BOOKS) == 66
        
        # Verify book structure
        for book in INITIAL_BOOKS:
            assert len(book) == 6  # id, name, testament, author, genre, canonical_order
            assert book[0]  # id not empty
            assert book[1]  # name not empty
            assert book[2] in ["OT", "NT"]  # valid testament
            assert book[3]  # author not empty
            assert book[4]  # genre not empty
            assert isinstance(book[5], int)  # canonical_order is integer
            assert 1 <= book[5] <= 66  # valid canonical order
        
        # Verify canonical order is unique and complete
        orders = {book[5] for book in INITIAL_BOOKS}
        assert orders == set(range(1, 67))  # 1-66
        
        # Verify testament distribution
        ot_books = [book for book in INITIAL_BOOKS if book[2] == "OT"]
        nt_books = [book for book in INITIAL_BOOKS if book[2] == "NT"]
        
        assert len(ot_books) == 39
        assert len(nt_books) == 27


if __name__ == "__main__":
    pytest.main([__file__])