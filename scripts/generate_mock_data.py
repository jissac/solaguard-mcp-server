#!/usr/bin/env python3
"""
SolaGuard Mock Data Generator

Generates a valid database structure with sample verses for immediate development.
This unblocks server development while real biblical text ingestion is built.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.database.schema import create_schema
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample verses for testing (well-known biblical passages)
MOCK_VERSES = [
    # John 3:16-17 (Most famous verse)
    ("KJV", "JHN", 3, 16, "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."),
    ("KJV", "JHN", 3, 17, "For God sent not his Son into the world to condemn the world; but that the world through him might be saved."),
    ("WEB", "JHN", 3, 16, "For God so loved the world, that he gave his one and only Son, that whoever believes in him should not perish, but have eternal life."),
    ("WEB", "JHN", 3, 17, "For God didn't send his Son into the world to judge the world, but that the world should be saved through him."),
    
    # Genesis 1:1 (Creation)
    ("KJV", "GEN", 1, 1, "In the beginning God created the heaven and the earth."),
    ("WEB", "GEN", 1, 1, "In the beginning, God created the heavens and the earth."),
    
    # Psalm 23:1-4 (Shepherd's Psalm)
    ("KJV", "PSA", 23, 1, "The LORD is my shepherd; I shall not want."),
    ("KJV", "PSA", 23, 2, "He maketh me to lie down in green pastures: he leadeth me beside the still waters."),
    ("KJV", "PSA", 23, 3, "He restoreth my soul: he leadeth me in the paths of righteousness for his name's sake."),
    ("KJV", "PSA", 23, 4, "Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art with me; thy rod and thy staff they comfort me."),
    
    # Romans 8:28 (All things work together)
    ("KJV", "ROM", 8, 28, "And we know that all things work together for good to them that love God, to them who are the called according to his purpose."),
    ("WEB", "ROM", 8, 28, "We know that all things work together for good for those who love God, to those who are called according to his purpose."),
    
    # Philippians 4:13 (I can do all things)
    ("KJV", "PHP", 4, 13, "I can do all things through Christ which strengtheneth me."),
    ("WEB", "PHP", 4, 13, "I can do all things through Christ, who strengthens me."),
    
    # 1 Corinthians 13:4-7 (Love chapter)
    ("KJV", "1CO", 13, 4, "Charity suffereth long, and is kind; charity envieth not; charity vaunteth not itself, is not puffed up,"),
    ("KJV", "1CO", 13, 5, "Doth not behave itself unseemly, seeketh not her own, is not easily provoked, thinketh no evil;"),
    ("KJV", "1CO", 13, 6, "Rejoiceth not in iniquity, but rejoiceth in the truth;"),
    ("KJV", "1CO", 13, 7, "Beareth all things, believeth all things, hopeth all things, endureth all things."),
    
    # Matthew 5:3-5 (Beatitudes)
    ("KJV", "MAT", 5, 3, "Blessed are the poor in spirit: for theirs is the kingdom of heaven."),
    ("KJV", "MAT", 5, 4, "Blessed are they that mourn: for they shall be comforted."),
    ("KJV", "MAT", 5, 5, "Blessed are the meek: for they shall inherit the earth."),
    
    # Jeremiah 29:11 (Plans to prosper)
    ("KJV", "JER", 29, 11, "For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end."),
    ("WEB", "JER", 29, 11, "For I know the thoughts that I think toward you, says Yahweh, thoughts of peace, and not of evil, to give you hope and a future."),
    
    # Isaiah 40:31 (Mount up with wings)
    ("KJV", "ISA", 40, 31, "But they that wait upon the LORD shall renew their strength; they shall mount up with wings as eagles; they shall run, and not be weary; and they shall walk, and not faint."),
    
    # Proverbs 3:5-6 (Trust in the Lord)
    ("KJV", "PRO", 3, 5, "Trust in the LORD with all thine heart; and lean not unto thine own understanding."),
    ("KJV", "PRO", 3, 6, "In all thy ways acknowledge him, and he shall direct thy paths."),
    
    # 2 Timothy 3:16 (Scripture inspiration)
    ("KJV", "2TI", 3, 16, "All scripture is given by inspiration of God, and is profitable for doctrine, for reproof, for correction, for instruction in righteousness:"),
    ("WEB", "2TI", 3, 16, "Every Scripture is God-breathed and profitable for teaching, for reproof, for correction, and for instruction in righteousness,"),
    
    # Ephesians 2:8-9 (Salvation by grace)
    ("KJV", "EPH", 2, 8, "For by grace are ye saved through faith; and that not of yourselves: it is the gift of God:"),
    ("KJV", "EPH", 2, 9, "Not of works, lest any man should boast."),
    
    # 1 John 4:8 (God is love)
    ("KJV", "1JN", 4, 8, "He that loveth not knoweth not God; for God is love."),
    ("WEB", "1JN", 4, 8, "He who doesn't love doesn't know God, for God is love."),
    
    # Revelation 21:4 (No more tears)
    ("KJV", "REV", 21, 4, "And God shall wipe away all tears from their eyes; and there shall be no more death, neither sorrow, nor crying, neither shall there be any more pain: for the former things are passed away."),
]


def generate_mock_database(db_path: Path) -> None:
    """
    Generate a mock database with sample verses for development.
    
    Args:
        db_path: Path where the mock database should be created
    """
    logger.info(f"Generating mock database at {db_path}")
    
    # Create schema with initial data
    create_schema(db_path)
    
    # Add mock verses
    with sqlite3.connect(db_path) as conn:
        # Insert mock verses
        conn.executemany(
            "INSERT INTO verses (translation_id, book_id, chapter, verse, text) VALUES (?, ?, ?, ?, ?)",
            MOCK_VERSES
        )
        
        # Populate FTS5 index
        conn.execute("INSERT INTO verses_fts(verse_id, book_id, text) SELECT id, book_id, text FROM verses")
        
        conn.commit()
    
    # Verify the mock data
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Count verses by translation
        cursor.execute("SELECT translation_id, COUNT(*) FROM verses GROUP BY translation_id")
        translation_counts = dict(cursor.fetchall())
        
        # Count verses by book
        cursor.execute("SELECT book_id, COUNT(*) FROM verses GROUP BY book_id")
        book_counts = dict(cursor.fetchall())
        
        # Test FTS5 search
        cursor.execute("SELECT COUNT(*) FROM verses_fts WHERE text MATCH 'love'")
        love_verses = cursor.fetchone()[0]
        
        logger.info(f"✅ Mock database created successfully")
        logger.info(f"📊 Verses by translation: {translation_counts}")
        logger.info(f"📚 Verses by book: {book_counts}")
        logger.info(f"🔍 Verses containing 'love': {love_verses}")


def main():
    """Main function to generate mock database."""
    # Default path for mock database
    db_path = Path(__file__).parent.parent / "data" / "bible_mock.db"
    
    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate mock database
    generate_mock_database(db_path)
    
    print(f"✅ Mock database generated at: {db_path}")
    print("🚀 You can now start server development with this test data!")
    print(f"📁 Database size: {db_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()