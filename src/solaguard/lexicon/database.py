"""
Lexicon Database Writer

Handles batch insertion and updates of lexicon data into the database
with optimized performance and transaction safety.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

from .models import LexiconEntry, CrossReference, IngestionStats

logger = logging.getLogger(__name__)


class DatabaseWriteError(Exception):
    """Raised when database write operations fail."""
    pass


class DatabaseWriter:
    """
    Handles database operations for lexicon data with batch processing,
    transaction safety, and performance optimization.
    """
    
    def __init__(self, db_path: Path, batch_size: int = 1000):
        """
        Initialize database writer.
        
        Args:
            db_path: Path to SQLite database file
            batch_size: Number of entries to process per batch
        """
        self.db_path = db_path
        self.batch_size = batch_size
        self.stats = IngestionStats()
        
        # Verify database exists
        if not db_path.exists():
            raise DatabaseWriteError(f"Database file not found: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        Get database connection with proper cleanup.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseWriteError(f"Database connection error: {e}")
        finally:
            if conn:
                conn.close()
    
    def update_database_schema(self) -> None:
        """
        Update database schema to support enhanced lexicon data.
        
        Adds new columns to existing strongs_dictionary table if needed.
        """
        logger.info("Updating database schema for lexicon data")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check current schema
            cursor.execute("PRAGMA table_info(strongs_dictionary)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            
            # Define required columns with simple types for ALTER TABLE
            required_columns = {
                "notes": "TEXT",
                "theological_significance": "TEXT", 
                "language": "TEXT",
                "created_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP"
            }
            
            # Add missing columns one by one
            for column, column_type in required_columns.items():
                if column not in existing_columns:
                    try:
                        if column in ["created_at", "updated_at"]:
                            # Add timestamp columns with default
                            cursor.execute(f"ALTER TABLE strongs_dictionary ADD COLUMN {column} {column_type} DEFAULT CURRENT_TIMESTAMP")
                        else:
                            cursor.execute(f"ALTER TABLE strongs_dictionary ADD COLUMN {column} {column_type}")
                        logger.info(f"Added column: {column}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e).lower():
                            logger.warning(f"Could not add column {column}: {e}")
            
            # Create cross-references table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lexicon_cross_references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_strongs TEXT NOT NULL,
                    to_strongs TEXT NOT NULL,
                    context TEXT DEFAULT 'unknown',
                    FOREIGN KEY (from_strongs) REFERENCES strongs_dictionary(number),
                    FOREIGN KEY (to_strongs) REFERENCES strongs_dictionary(number),
                    UNIQUE(from_strongs, to_strongs)
                )
            """)
            
            conn.commit()
            logger.info("Database schema updated successfully")
    
    def insert_lexicon_entries(self, entries: List[LexiconEntry]) -> None:
        """
        Batch insert lexicon entries with upsert logic.
        
        Args:
            entries: List of LexiconEntry objects to insert
        """
        if not entries:
            return
        
        logger.info(f"Inserting {len(entries)} lexicon entries in batches of {self.batch_size}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Process entries in batches
            for i in range(0, len(entries), self.batch_size):
                batch = entries[i:i + self.batch_size]
                
                try:
                    # Prepare batch data
                    batch_data = []
                    for entry in batch:
                        batch_data.append((
                            entry.strongs_number,
                            entry.word,
                            entry.transliteration,
                            entry.pronunciation,
                            entry.definition,
                            entry.notes,
                            entry.theological_significance,
                            entry.language
                        ))
                    
                    # Use INSERT OR REPLACE for upsert behavior
                    cursor.executemany("""
                        INSERT OR REPLACE INTO strongs_dictionary 
                        (number, word, transliteration, pronunciation, definition, 
                         notes, theological_significance, language, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, batch_data)
                    
                    # Check if entries were created or updated
                    for entry in batch:
                        cursor.execute(
                            "SELECT created_at, updated_at FROM strongs_dictionary WHERE number = ?",
                            (entry.strongs_number,)
                        )
                        row = cursor.fetchone()
                        if row:
                            created_at, updated_at = row
                            if created_at == updated_at:
                                self.stats.entries_created += 1
                            else:
                                self.stats.entries_updated += 1
                    
                    conn.commit()
                    logger.debug(f"Inserted batch {i//self.batch_size + 1}: {len(batch)} entries")
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to insert batch {i//self.batch_size + 1}: {e}")
                    raise DatabaseWriteError(f"Batch insertion failed: {e}")
        
        logger.info(f"Successfully inserted {len(entries)} lexicon entries")
    
    def insert_cross_references(self, references: List[CrossReference]) -> None:
        """
        Insert cross-reference relationships.
        
        Args:
            references: List of CrossReference objects to insert
        """
        if not references:
            return
        
        logger.info(f"Inserting {len(references)} cross-references")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Prepare batch data
                batch_data = [
                    (ref.from_strongs, ref.to_strongs, ref.context)
                    for ref in references
                ]
                
                # Use INSERT OR IGNORE to avoid duplicates
                cursor.executemany("""
                    INSERT OR IGNORE INTO lexicon_cross_references 
                    (from_strongs, to_strongs, context)
                    VALUES (?, ?, ?)
                """, batch_data)
                
                self.stats.cross_references_created += cursor.rowcount
                conn.commit()
                
                logger.info(f"Successfully inserted {cursor.rowcount} cross-references")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to insert cross-references: {e}")
                raise DatabaseWriteError(f"Cross-reference insertion failed: {e}")
    
    def create_indexes(self) -> None:
        """
        Create optimized indexes for lexicon queries.
        """
        logger.info("Creating database indexes for lexicon data")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_strongs_word ON strongs_dictionary(word)",
            "CREATE INDEX IF NOT EXISTS idx_strongs_language ON strongs_dictionary(language)",
            "CREATE INDEX IF NOT EXISTS idx_strongs_transliteration ON strongs_dictionary(transliteration)",
            "CREATE INDEX IF NOT EXISTS idx_cross_ref_from ON lexicon_cross_references(from_strongs)",
            "CREATE INDEX IF NOT EXISTS idx_cross_ref_to ON lexicon_cross_references(to_strongs)",
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.debug(f"Created index: {index_sql.split()[-1]}")
                except Exception as e:
                    logger.warning(f"Could not create index: {e}")
            
            conn.commit()
        
        logger.info("Database indexes created successfully")
    
    def create_fts_table(self) -> None:
        """
        Create full-text search table for lexicon definitions.
        """
        logger.info("Creating full-text search table for lexicon data")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Create FTS5 virtual table
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS strongs_fts USING fts5(
                        number UNINDEXED,
                        word,
                        transliteration,
                        definition,
                        notes,
                        theological_significance,
                        content='strongs_dictionary',
                        content_rowid='rowid'
                    )
                """)
                
                # Populate FTS table
                cursor.execute("""
                    INSERT INTO strongs_fts(strongs_fts) VALUES('rebuild')
                """)
                
                conn.commit()
                logger.info("Full-text search table created successfully")
                
            except Exception as e:
                logger.warning(f"Could not create FTS table: {e}")
    
    def get_database_stats(self) -> Dict:
        """
        Get current database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count entries by language
            cursor.execute("""
                SELECT language, COUNT(*) 
                FROM strongs_dictionary 
                WHERE language IS NOT NULL 
                GROUP BY language
            """)
            stats["entries_by_language"] = dict(cursor.fetchall())
            
            # Count total entries
            cursor.execute("SELECT COUNT(*) FROM strongs_dictionary")
            stats["total_entries"] = cursor.fetchone()[0]
            
            # Count cross-references
            cursor.execute("SELECT COUNT(*) FROM lexicon_cross_references")
            stats["total_cross_references"] = cursor.fetchone()[0]
            
            # Count entries with various fields
            for field in ["notes", "theological_significance", "pronunciation"]:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM strongs_dictionary 
                    WHERE {field} IS NOT NULL AND {field} != ''
                """)
                stats[f"entries_with_{field}"] = cursor.fetchone()[0]
            
            return stats
    
    def verify_data_integrity(self) -> Dict:
        """
        Verify data integrity after ingestion.
        
        Returns:
            Dictionary with integrity check results
        """
        logger.info("Verifying data integrity")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            issues = []
            
            # Check for entries with missing required fields
            cursor.execute("""
                SELECT number FROM strongs_dictionary 
                WHERE word IS NULL OR word = '' OR definition IS NULL OR definition = ''
            """)
            missing_required = cursor.fetchall()
            if missing_required:
                issues.append(f"Entries with missing required fields: {len(missing_required)}")
            
            # Check for invalid Strong's number formats
            cursor.execute("""
                SELECT number FROM strongs_dictionary 
                WHERE number NOT GLOB '[GH][0-9]*'
            """)
            invalid_numbers = cursor.fetchall()
            if invalid_numbers:
                issues.append(f"Entries with invalid Strong's numbers: {len(invalid_numbers)}")
            
            # Check for broken cross-references
            cursor.execute("""
                SELECT DISTINCT lcr.to_strongs 
                FROM lexicon_cross_references lcr
                LEFT JOIN strongs_dictionary sd ON lcr.to_strongs = sd.number
                WHERE sd.number IS NULL
            """)
            broken_refs = cursor.fetchall()
            if broken_refs:
                issues.append(f"Broken cross-references: {len(broken_refs)}")
            
            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "total_entries": self.get_database_stats()["total_entries"]
            }
    
    def get_ingestion_stats(self) -> IngestionStats:
        """
        Get current ingestion statistics.
        
        Returns:
            IngestionStats object with current statistics
        """
        return self.stats


def create_cross_references_from_entries(entries: List[LexiconEntry]) -> List[CrossReference]:
    """
    Create CrossReference objects from lexicon entries.
    
    Args:
        entries: List of LexiconEntry objects
        
    Returns:
        List of CrossReference objects
    """
    cross_refs = []
    
    for entry in entries:
        for ref_number in entry.cross_references:
            cross_ref = CrossReference(
                from_strongs=entry.strongs_number,
                to_strongs=ref_number,
                context="lexicon_entry"
            )
            if cross_ref.is_valid():
                cross_refs.append(cross_ref)
    
    return cross_refs


if __name__ == "__main__":
    # Test the database writer
    from .models import LexiconEntry
    
    # Create test entry
    test_entry = LexiconEntry(
        strongs_number="G1",
        word="Α",
        transliteration="A",
        pronunciation="al'-fah",
        definition="the first letter of the alphabet",
        notes="Often used in composition",
        theological_significance="- Christ is the Alpha",
        language="greek",
        cross_references=["G260", "G427"]
    )
    
    # Test database operations (requires actual database)
    db_path = Path("data/bible.db")
    if db_path.exists():
        try:
            writer = DatabaseWriter(db_path)
            
            # Test schema update
            writer.update_database_schema()
            print("✅ Schema update successful")
            
            # Test stats
            stats = writer.get_database_stats()
            print(f"📊 Database stats: {stats}")
            
            # Test integrity check
            integrity = writer.verify_data_integrity()
            print(f"🔍 Integrity check: {integrity}")
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
    else:
        print("Database not found - writer created successfully")