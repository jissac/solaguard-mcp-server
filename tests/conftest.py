"""
Pytest configuration and fixtures for SolaGuard tests.
"""

import pytest
import tempfile
import sqlite3
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.database.schema import create_schema


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = Path(tmp_file.name)
    
    # Create schema
    create_schema(db_path)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def temp_db_with_verses():
    """Create a temporary database with sample verses for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = Path(tmp_file.name)
    
    # Create schema
    create_schema(db_path)
    
    # Add sample verses
    sample_verses = [
        ("KJV", "JHN", 3, 16, "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."),
        ("KJV", "JHN", 3, 17, "For God sent not his Son into the world to condemn the world; but that the world through him might be saved."),
        ("WEB", "JHN", 3, 16, "For God so loved the world, that he gave his one and only Son, that whoever believes in him should not perish, but have eternal life."),
        ("KJV", "GEN", 1, 1, "In the beginning God created the heaven and the earth."),
        ("KJV", "PSA", 23, 1, "The LORD is my shepherd; I shall not want."),
        ("KJV", "ROM", 8, 28, "And we know that all things work together for good to them that love God, to them who are the called according to his purpose."),
    ]
    
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO verses (translation_id, book_id, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
            sample_verses
        )
        conn.execute("INSERT INTO verses_fts(verse_id, book_id, text) SELECT id, book_id, text FROM verses")
        conn.commit()
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_verse_data():
    """Sample verse data for testing."""
    return {
        "id": 1,
        "book_id": "JHN",
        "chapter": 3,
        "verse": 16,
        "text": "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
        "name": "John",
        "testament": "NT",
        "author": "John",
        "genre": "Gospel"
    }


@pytest.fixture
def sample_book_metadata():
    """Sample book metadata for testing."""
    return {
        "id": "JHN",
        "name": "John",
        "testament": "NT",
        "author": "John",
        "genre": "Gospel",
        "canonical_order": 43
    }


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)