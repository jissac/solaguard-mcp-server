#!/usr/bin/env python3
"""
Naves Topical Dictionary Ingestion Script

Ingests Naves Topical Dictionary CSV data into the database with proper verse linking.
Handles various verse reference formats and validates against existing verse data.
"""

import csv
import re
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.tools.reference_parser import parse_reference, ReferenceParseError, VerseRange

# Database path
DB_PATH = Path("data/bible.db")
CSV_PATH = Path("data/NavesTopicalDictionary.csv")


class VerseReferenceExtractor:
    """Extracts and parses verse references from Nave's entry text."""
    
    # Pattern to match verse references in various formats
    # Examples: "EXO 6:16-20", "JOS 21:4,10", "1CH 6:2,3", "LEV 9", "PSA 77:20"
    REFERENCE_PATTERN = re.compile(
        r'\b([123]?[A-Z]{2,3})\s+(\d+)(?::(\d+(?:[-,]\d+)*))?',
        re.IGNORECASE
    )
    
    def extract_references(self, entry_text: str) -> List[str]:
        """
        Extract all verse references from entry text.
        
        Args:
            entry_text: The entry text containing verse references
            
        Returns:
            List of reference strings (e.g., ["EXO 6:16-20", "JOS 21:4"])
        """
        references = []
        
        for match in self.REFERENCE_PATTERN.finditer(entry_text):
            book = match.group(1)
            chapter = match.group(2)
            verses = match.group(3) if match.group(3) else None
            
            if verses:
                # Handle comma-separated verses: "21:4,10" -> ["21:4", "21:10"]
                if ',' in verses:
                    verse_parts = verses.split(',')
                    for verse_part in verse_parts:
                        verse_part = verse_part.strip()
                        if '-' in verse_part:
                            # Range like "4-10"
                            references.append(f"{book} {chapter}:{verse_part}")
                        else:
                            # Single verse
                            references.append(f"{book} {chapter}:{verse_part}")
                else:
                    # Single verse or range
                    references.append(f"{book} {chapter}:{verses}")
            else:
                # Chapter only reference (e.g., "LEV 9")
                references.append(f"{book} {chapter}")
        
        return references
    
    def parse_and_validate(self, reference: str, cursor: sqlite3.Cursor) -> List[int]:
        """
        Parse a reference and get verse IDs from database.
        
        Args:
            reference: Reference string (e.g., "EXO 6:16-20")
            cursor: Database cursor
            
        Returns:
            List of verse IDs from database
        """
        try:
            parsed = parse_reference(reference)
            verse_ids = []
            
            if isinstance(parsed, VerseRange):
                # Get all verses in range
                for verse_ref in parsed.to_verse_list():
                    verse_id = self._get_verse_id(
                        cursor, 
                        verse_ref.book_id, 
                        verse_ref.chapter, 
                        verse_ref.verse
                    )
                    if verse_id:
                        verse_ids.append(verse_id)
            else:
                # Single verse
                verse_id = self._get_verse_id(
                    cursor,
                    parsed.book_id,
                    parsed.chapter,
                    parsed.verse
                )
                if verse_id:
                    verse_ids.append(verse_id)
            
            return verse_ids
            
        except ReferenceParseError as e:
            # Log but don't fail
            return []
    
    def _get_verse_id(self, cursor: sqlite3.Cursor, book_id: str, chapter: int, verse: int) -> Optional[int]:
        """Get verse ID from database."""
        cursor.execute("""
            SELECT id FROM verses 
            WHERE book_id = ? AND chapter = ? AND verse = ?
            LIMIT 1
        """, (book_id, chapter, verse))
        
        result = cursor.fetchone()
        return result[0] if result else None


def create_topical_schema(cursor: sqlite3.Cursor):
    """Create topical tables if they don't exist."""
    
    # Create topical_index table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topical_index (
            id INTEGER PRIMARY KEY,
            topic TEXT NOT NULL,
            parent_topic TEXT,
            description TEXT,
            source TEXT DEFAULT 'nave',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(topic, source)
        )
    """)
    
    # Create topic_verses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_verses (
            id INTEGER PRIMARY KEY,
            topic_id INTEGER NOT NULL,
            verse_id INTEGER NOT NULL,
            relevance_score REAL DEFAULT 1.0,
            source TEXT DEFAULT 'nave',
            FOREIGN KEY (topic_id) REFERENCES topical_index(id),
            FOREIGN KEY (verse_id) REFERENCES verses(id),
            UNIQUE(topic_id, verse_id)
        )
    """)
    
    # Create topic_keywords table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_keywords (
            id INTEGER PRIMARY KEY,
            topic_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            FOREIGN KEY (topic_id) REFERENCES topical_index(id),
            UNIQUE(topic_id, keyword)
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_topical_topic ON topical_index(topic)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_verses_topic ON topic_verses(topic_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_verses_verse ON topic_verses(verse_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_keywords_topic ON topic_keywords(topic_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_keywords_keyword ON topic_keywords(keyword)")
    
    print("✅ Topical schema created/verified")


def ingest_csv_data(dry_run: bool = False):
    """
    Ingest Naves Topical Dictionary CSV data.
    
    Args:
        dry_run: If True, parse and validate but don't write to database
    """
    if not CSV_PATH.exists():
        print(f"❌ CSV file not found: {CSV_PATH}")
        return
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create schema
    if not dry_run:
        create_topical_schema(cursor)
        conn.commit()
    
    extractor = VerseReferenceExtractor()
    
    # Statistics
    stats = {
        'rows_processed': 0,
        'topics_created': 0,
        'topics_updated': 0,
        'verses_linked': 0,
        'references_found': 0,
        'references_parsed': 0,
        'references_failed': 0,
        'topics_no_verses': 0,
    }
    
    # Track topics with no verses
    topics_no_verses = []
    
    print(f"\n📖 Processing {CSV_PATH}")
    print(f"{'DRY RUN - ' if dry_run else ''}Ingesting Naves Topical Dictionary...")
    
    # Read CSV with UTF-8-sig to handle BOM
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            stats['rows_processed'] += 1
            
            section = row['section'].strip()
            subject = row['subject'].strip()
            entry = row['entry'].strip()
            
            if not subject:
                continue
            
            # Get or create topic
            if not dry_run:
                cursor.execute("""
                    INSERT OR IGNORE INTO topical_index (topic, description, source)
                    VALUES (?, ?, 'nave')
                """, (subject, f"Nave's Topical Bible entry for {subject}"))
                
                if cursor.rowcount > 0:
                    stats['topics_created'] += 1
                else:
                    stats['topics_updated'] += 1
                
                # Get topic ID
                cursor.execute("""
                    SELECT id FROM topical_index WHERE topic = ? AND source = 'nave'
                """, (subject,))
                topic_id = cursor.fetchone()[0]
            else:
                topic_id = stats['rows_processed']  # Fake ID for dry run
            
            # Extract verse references from entry
            references = extractor.extract_references(entry)
            stats['references_found'] += len(references)
            
            verse_ids_for_topic = set()
            
            # Parse and validate each reference
            for ref in references:
                verse_ids = extractor.parse_and_validate(ref, cursor)
                
                if verse_ids:
                    stats['references_parsed'] += 1
                    verse_ids_for_topic.update(verse_ids)
                else:
                    stats['references_failed'] += 1
            
            # Link verses to topic
            if not dry_run:
                for verse_id in verse_ids_for_topic:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO topic_verses (topic_id, verse_id, source)
                            VALUES (?, ?, 'nave')
                        """, (topic_id, verse_id))
                        
                        if cursor.rowcount > 0:
                            stats['verses_linked'] += 1
                    except sqlite3.IntegrityError:
                        # Duplicate, skip
                        pass
            else:
                stats['verses_linked'] += len(verse_ids_for_topic)
            
            # Track topics with no verses
            if not verse_ids_for_topic:
                stats['topics_no_verses'] += 1
                topics_no_verses.append(subject)
            
            # Progress reporting
            if stats['rows_processed'] % 1000 == 0:
                print(f"   Processed {stats['rows_processed']:,} rows...")
                if not dry_run:
                    conn.commit()
    
    if not dry_run:
        conn.commit()
    
    # Final statistics
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Rows processed:       {stats['rows_processed']:,}")
    print(f"Topics created:       {stats['topics_created']:,}")
    print(f"Topics updated:       {stats['topics_updated']:,}")
    print(f"References found:     {stats['references_found']:,}")
    print(f"References parsed:    {stats['references_parsed']:,}")
    print(f"References failed:    {stats['references_failed']:,}")
    print(f"Verses linked:        {stats['verses_linked']:,}")
    print(f"Topics with no verses: {stats['topics_no_verses']:,}")
    
    if stats['topics_no_verses'] > 0:
        print(f"\n⚠️  {stats['topics_no_verses']} topics have no verse associations")
        print(f"First 20 topics with no verses:")
        for topic in topics_no_verses[:20]:
            print(f"   - {topic}")
    
    # Verification queries
    if not dry_run:
        print("\n📊 Database Verification:")
        
        cursor.execute("SELECT COUNT(*) FROM topical_index")
        print(f"   Total topics: {cursor.fetchone()[0]:,}")
        
        cursor.execute("SELECT COUNT(*) FROM topic_verses")
        print(f"   Total verse links: {cursor.fetchone()[0]:,}")
        
        cursor.execute("""
            SELECT COUNT(DISTINCT ti.id)
            FROM topical_index ti
            LEFT JOIN topic_verses tv ON ti.id = tv.topic_id
            WHERE tv.verse_id IS NULL
        """)
        orphaned = cursor.fetchone()[0]
        print(f"   Topics with no verses: {orphaned:,}")
    
    conn.close()
    
    print("\n✅ Ingestion complete!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest Naves Topical Dictionary CSV data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without database changes"
    )
    
    args = parser.parse_args()
    
    print("🚀 Naves Topical Dictionary Ingestion")
    print("=" * 60)
    
    try:
        ingest_csv_data(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
