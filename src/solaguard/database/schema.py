"""
SolaGuard Database Schema

Complete database schema implementation including all Phase 1 and Phase 2 tables.
Creates empty Phase 2 tables to prevent migration complexity later.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Database schema SQL statements
SCHEMA_SQL = """
-- Translations table: Supported Bible translations
CREATE TABLE IF NOT EXISTS translations (
    id TEXT PRIMARY KEY,           -- 'KJV', 'WEB', 'TR', 'WLC'
    name TEXT NOT NULL,            -- 'King James Version'
    language TEXT NOT NULL,        -- 'en', 'grc', 'hbo'
    type TEXT NOT NULL             -- 'translation', 'original'
);

-- Books table: Biblical books with metadata
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,           -- 'GEN', 'JHN'
    name TEXT NOT NULL,            -- 'Genesis', 'John'
    testament TEXT NOT NULL,       -- 'OT', 'NT'
    author TEXT,                   -- 'Moses', 'John', 'Paul'
    genre TEXT,                    -- 'Law', 'Gospel', 'Epistle'
    canonical_order INTEGER NOT NULL  -- 1-66
);

-- Verses table: Biblical text content
CREATE TABLE IF NOT EXISTS verses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id TEXT NOT NULL,
    book_id TEXT NOT NULL,         -- 'GEN', 'JHN'
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (translation_id) REFERENCES translations(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    UNIQUE(translation_id, book_id, chapter, verse)
);

-- Indexes for fast verse lookup
CREATE INDEX IF NOT EXISTS idx_verses_lookup ON verses(translation_id, book_id, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_verses_book ON verses(book_id);
CREATE INDEX IF NOT EXISTS idx_verses_translation ON verses(translation_id);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts USING fts5(
    verse_id,
    book_id,                       -- Enable book-specific search
    text,
    content='verses',
    content_rowid='id'
);

-- Phase 2 tables (empty for now, prevents migration complexity)

-- Words table: Interlinear data for word-level analysis
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,     -- Word order in verse
    text TEXT NOT NULL,            -- Raw word token
    normalized TEXT,               -- Lowercase/lemma form
    strongs TEXT,                  -- 'G25', 'H157'
    morphology TEXT,               -- JSON: {"pos": "verb", "tense": "aorist"}
    english_equiv TEXT,            -- Aligned English word
    transliteration TEXT,          -- Romanized form
    FOREIGN KEY (verse_id) REFERENCES verses(id)
);

CREATE INDEX IF NOT EXISTS idx_words_verse ON words(verse_id);
CREATE INDEX IF NOT EXISTS idx_words_strongs ON words(strongs);

-- Strong's dictionary: Hebrew/Greek word definitions
CREATE TABLE IF NOT EXISTS strongs_dictionary (
    number TEXT PRIMARY KEY,       -- 'G25', 'H157'
    word TEXT NOT NULL,            -- Original language word
    transliteration TEXT,          -- Romanized form
    pronunciation TEXT,            -- Phonetic guide
    definition TEXT NOT NULL,      -- English definition
    part_of_speech TEXT           -- 'verb', 'noun', etc.
);

-- Cross-references: Thematically related passages
CREATE TABLE IF NOT EXISTS cross_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_verse_id INTEGER NOT NULL,
    to_verse_id INTEGER NOT NULL,
    relationship_type TEXT,        -- 'parallel', 'quotation', 'theme'
    relevance_score REAL,          -- 0.0 to 1.0
    FOREIGN KEY (from_verse_id) REFERENCES verses(id),
    FOREIGN KEY (to_verse_id) REFERENCES verses(id)
);

CREATE INDEX IF NOT EXISTS idx_cross_refs_from ON cross_references(from_verse_id);
CREATE INDEX IF NOT EXISTS idx_cross_refs_to ON cross_references(to_verse_id);
"""

# Initial data for translations table
INITIAL_TRANSLATIONS = [
    ("KJV", "King James Version (1769)", "en", "translation"),
    ("WEB", "World English Bible", "en", "translation"),
    ("TR", "Textus Receptus", "grc", "original"),
    ("WH", "Westcott-Hort", "grc", "original"),
    ("BYZ", "Byzantine Majority Text", "grc", "original"),
    ("MT", "Masoretic Text", "hbo", "original"),
    ("WLC", "Westminster Leningrad Codex", "hbo", "original"),
]

# Initial data for books table (66 canonical Protestant books)
INITIAL_BOOKS = [
    # Old Testament
    ("GEN", "Genesis", "OT", "Moses", "Law", 1),
    ("EXO", "Exodus", "OT", "Moses", "Law", 2),
    ("LEV", "Leviticus", "OT", "Moses", "Law", 3),
    ("NUM", "Numbers", "OT", "Moses", "Law", 4),
    ("DEU", "Deuteronomy", "OT", "Moses", "Law", 5),
    ("JOS", "Joshua", "OT", "Joshua", "History", 6),
    ("JDG", "Judges", "OT", "Samuel", "History", 7),
    ("RUT", "Ruth", "OT", "Samuel", "History", 8),
    ("1SA", "1 Samuel", "OT", "Samuel", "History", 9),
    ("2SA", "2 Samuel", "OT", "Samuel", "History", 10),
    ("1KI", "1 Kings", "OT", "Jeremiah", "History", 11),
    ("2KI", "2 Kings", "OT", "Jeremiah", "History", 12),
    ("1CH", "1 Chronicles", "OT", "Ezra", "History", 13),
    ("2CH", "2 Chronicles", "OT", "Ezra", "History", 14),
    ("EZR", "Ezra", "OT", "Ezra", "History", 15),
    ("NEH", "Nehemiah", "OT", "Nehemiah", "History", 16),
    ("EST", "Esther", "OT", "Mordecai", "History", 17),
    ("JOB", "Job", "OT", "Moses", "Wisdom", 18),
    ("PSA", "Psalms", "OT", "David", "Wisdom", 19),
    ("PRO", "Proverbs", "OT", "Solomon", "Wisdom", 20),
    ("ECC", "Ecclesiastes", "OT", "Solomon", "Wisdom", 21),
    ("SNG", "Song of Songs", "OT", "Solomon", "Wisdom", 22),
    ("ISA", "Isaiah", "OT", "Isaiah", "Prophecy", 23),
    ("JER", "Jeremiah", "OT", "Jeremiah", "Prophecy", 24),
    ("LAM", "Lamentations", "OT", "Jeremiah", "Prophecy", 25),
    ("EZK", "Ezekiel", "OT", "Ezekiel", "Prophecy", 26),
    ("DAN", "Daniel", "OT", "Daniel", "Prophecy", 27),
    ("HOS", "Hosea", "OT", "Hosea", "Prophecy", 28),
    ("JOL", "Joel", "OT", "Joel", "Prophecy", 29),
    ("AMO", "Amos", "OT", "Amos", "Prophecy", 30),
    ("OBA", "Obadiah", "OT", "Obadiah", "Prophecy", 31),
    ("JON", "Jonah", "OT", "Jonah", "Prophecy", 32),
    ("MIC", "Micah", "OT", "Micah", "Prophecy", 33),
    ("NAM", "Nahum", "OT", "Nahum", "Prophecy", 34),
    ("HAB", "Habakkuk", "OT", "Habakkuk", "Prophecy", 35),
    ("ZEP", "Zephaniah", "OT", "Zephaniah", "Prophecy", 36),
    ("HAG", "Haggai", "OT", "Haggai", "Prophecy", 37),
    ("ZEC", "Zechariah", "OT", "Zechariah", "Prophecy", 38),
    ("MAL", "Malachi", "OT", "Malachi", "Prophecy", 39),
    
    # New Testament
    ("MAT", "Matthew", "NT", "Matthew", "Gospel", 40),
    ("MRK", "Mark", "NT", "Mark", "Gospel", 41),
    ("LUK", "Luke", "NT", "Luke", "Gospel", 42),
    ("JHN", "John", "NT", "John", "Gospel", 43),
    ("ACT", "Acts", "NT", "Luke", "History", 44),
    ("ROM", "Romans", "NT", "Paul", "Epistle", 45),
    ("1CO", "1 Corinthians", "NT", "Paul", "Epistle", 46),
    ("2CO", "2 Corinthians", "NT", "Paul", "Epistle", 47),
    ("GAL", "Galatians", "NT", "Paul", "Epistle", 48),
    ("EPH", "Ephesians", "NT", "Paul", "Epistle", 49),
    ("PHP", "Philippians", "NT", "Paul", "Epistle", 50),
    ("COL", "Colossians", "NT", "Paul", "Epistle", 51),
    ("1TH", "1 Thessalonians", "NT", "Paul", "Epistle", 52),
    ("2TH", "2 Thessalonians", "NT", "Paul", "Epistle", 53),
    ("1TI", "1 Timothy", "NT", "Paul", "Epistle", 54),
    ("2TI", "2 Timothy", "NT", "Paul", "Epistle", 55),
    ("TIT", "Titus", "NT", "Paul", "Epistle", 56),
    ("PHM", "Philemon", "NT", "Paul", "Epistle", 57),
    ("HEB", "Hebrews", "NT", "Paul", "Epistle", 58),
    ("JAS", "James", "NT", "James", "Epistle", 59),
    ("1PE", "1 Peter", "NT", "Peter", "Epistle", 60),
    ("2PE", "2 Peter", "NT", "Peter", "Epistle", 61),
    ("1JN", "1 John", "NT", "John", "Epistle", 62),
    ("2JN", "2 John", "NT", "John", "Epistle", 63),
    ("3JN", "3 John", "NT", "John", "Epistle", 64),
    ("JUD", "Jude", "NT", "Jude", "Epistle", 65),
    ("REV", "Revelation", "NT", "John", "Prophecy", 66),
]


def create_schema(db_path: Path) -> None:
    """
    Create the complete database schema including all tables and indexes.
    
    Args:
        db_path: Path to the SQLite database file
    """
    logger.info(f"Creating database schema at {db_path}")
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Execute schema creation
        conn.executescript(SCHEMA_SQL)
        
        # Insert initial translations
        conn.executemany(
            "INSERT OR IGNORE INTO translations (id, name, language, type) VALUES (?, ?, ?, ?)",
            INITIAL_TRANSLATIONS
        )
        
        # Insert initial books
        conn.executemany(
            "INSERT OR IGNORE INTO books (id, name, testament, author, genre, canonical_order) VALUES (?, ?, ?, ?, ?, ?)",
            INITIAL_BOOKS
        )
        
        conn.commit()
        
    logger.info("Database schema created successfully")


def validate_schema(db_path: Path) -> bool:
    """
    Validate that the database schema is complete and correct.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        True if schema is valid, False otherwise
    """
    if not db_path.exists():
        logger.error(f"Database file does not exist: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check that all required tables exist
            required_tables = [
                "translations", "books", "verses", "verses_fts",
                "words", "strongs_dictionary", "cross_references"
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            missing_tables = set(required_tables) - existing_tables
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                return False
            
            # Check that initial data is present
            cursor.execute("SELECT COUNT(*) FROM translations")
            translation_count = cursor.fetchone()[0]
            if translation_count < 7:  # Should have 7 initial translations
                logger.error(f"Expected 7 translations, found {translation_count}")
                return False
            
            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]
            if book_count < 66:  # Should have 66 canonical books
                logger.error(f"Expected 66 books, found {book_count}")
                return False
            
            logger.info("Database schema validation successful")
            return True
            
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False


def get_database_info(db_path: Path) -> dict:
    """
    Get information about the database contents.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        Dictionary with database statistics
    """
    if not db_path.exists():
        return {"error": "Database file does not exist"}
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get table counts
            info = {}
            tables = ["translations", "books", "verses", "words", "strongs_dictionary", "cross_references"]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                info[f"{table}_count"] = cursor.fetchone()[0]
            
            # Get available translations
            cursor.execute("SELECT id, name FROM translations ORDER BY id")
            info["available_translations"] = dict(cursor.fetchall())
            
            # Get testament distribution
            cursor.execute("SELECT testament, COUNT(*) FROM books GROUP BY testament")
            info["testament_distribution"] = dict(cursor.fetchall())
            
            return info
            
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # For testing schema creation
    test_db = Path("test_schema.db")
    create_schema(test_db)
    
    if validate_schema(test_db):
        print("✅ Schema validation passed")
        info = get_database_info(test_db)
        print(f"📊 Database info: {info}")
    else:
        print("❌ Schema validation failed")
    
    # Cleanup test database
    test_db.unlink(missing_ok=True)