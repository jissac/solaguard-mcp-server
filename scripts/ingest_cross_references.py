#!/usr/bin/env python3
"""
Cross-Reference Ingestion Script

Ingests verse cross-reference data from JSON files into the SolaGuard database.
Handles verse ID mapping, validation, and batch insertion with progress reporting.
"""

import argparse
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class CrossReferenceStats:
    """Statistics for cross-reference ingestion."""
    files_processed: int = 0
    verses_processed: int = 0
    cross_references_found: int = 0
    cross_references_created: int = 0
    cross_references_skipped: int = 0
    verse_mapping_errors: int = 0
    processing_time_seconds: float = 0.0
    
    def get_summary(self) -> str:
        """Get formatted summary of ingestion statistics."""
        success_rate = (self.cross_references_created / max(self.cross_references_found, 1)) * 100
        
        return f"""
Files processed: {self.files_processed:,}
Verses processed: {self.verses_processed:,}
Cross-references found: {self.cross_references_found:,}
Cross-references created: {self.cross_references_created:,}
Cross-references skipped: {self.cross_references_skipped:,}
Verse mapping errors: {self.verse_mapping_errors:,}
Success rate: {success_rate:.1f}%
Processing time: {self.processing_time_seconds:.2f} seconds
        """.strip()


class VerseMapper:
    """Maps verse references to database verse IDs."""
    
    def __init__(self, db_path: Path):
        """
        Initialize verse mapper with database connection.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.verse_cache: Dict[str, int] = {}
        self.book_mapping = self._create_book_mapping()
        self._load_verse_cache()
    
    def _create_book_mapping(self) -> Dict[str, str]:
        """Create mapping from various book abbreviations to database book IDs."""
        return {
            # Old Testament
            "GEN": "GEN", "EXO": "EXO", "LEV": "LEV", "NUM": "NUM", "DEU": "DEU",
            "JOS": "JOS", "JDG": "JDG", "RUT": "RUT", "1SA": "1SA", "2SA": "2SA",
            "1KI": "1KI", "2KI": "2KI", "1CH": "1CH", "2CH": "2CH", "EZR": "EZR",
            "NEH": "NEH", "EST": "EST", "JOB": "JOB", "PSA": "PSA", "PRO": "PRO",
            "ECC": "ECC", "SNG": "SNG", "ISA": "ISA", "JER": "JER", "LAM": "LAM",
            "EZK": "EZK", "DAN": "DAN", "HOS": "HOS", "JOL": "JOL", "AMO": "AMO",
            "OBA": "OBA", "JON": "JON", "MIC": "MIC", "NAM": "NAM", "HAB": "HAB",
            "ZEP": "ZEP", "HAG": "HAG", "ZEC": "ZEC", "MAL": "MAL",
            
            # New Testament
            "MAT": "MAT", "MRK": "MRK", "LUK": "LUK", "JHN": "JHN", "ACT": "ACT",
            "ROM": "ROM", "1CO": "1CO", "2CO": "2CO", "GAL": "GAL", "EPH": "EPH",
            "PHP": "PHP", "COL": "COL", "1TH": "1TH", "2TH": "2TH", "1TI": "1TI",
            "2TI": "2TI", "TIT": "TIT", "PHM": "PHM", "HEB": "HEB", "JAS": "JAS",
            "1PE": "1PE", "2PE": "2PE", "1JN": "1JN", "2JN": "2JN", "3JN": "3JN",
            "JUD": "JUD", "REV": "REV"
        }
    
    def _load_verse_cache(self) -> None:
        """Load all verses into cache for fast lookup."""
        logger = logging.getLogger(__name__)
        logger.info("Loading verse cache from database...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load all verses with their references
            cursor.execute("""
                SELECT v.id, b.id as book_id, v.chapter, v.verse, v.translation_id
                FROM verses v
                JOIN books b ON v.book_id = b.id
                ORDER BY b.canonical_order, v.chapter, v.verse
            """)
            
            for verse_id, book_id, chapter, verse, translation_id in cursor.fetchall():
                # Create cache key: "BOOK CHAPTER VERSE TRANSLATION"
                cache_key = f"{book_id} {chapter} {verse} {translation_id}"
                self.verse_cache[cache_key] = verse_id
        
        logger.info(f"Loaded {len(self.verse_cache):,} verses into cache")
    
    def parse_verse_reference(self, ref: str) -> Optional[Tuple[str, int, int]]:
        """
        Parse verse reference string into components.
        
        Args:
            ref: Verse reference like "GEN 1 1" or "JHN 3 16"
            
        Returns:
            Tuple of (book_id, chapter, verse) or None if invalid
        """
        try:
            parts = ref.strip().split()
            if len(parts) != 3:
                return None
            
            book_abbrev, chapter_str, verse_str = parts
            
            # Map book abbreviation
            book_id = self.book_mapping.get(book_abbrev.upper())
            if not book_id:
                return None
            
            chapter = int(chapter_str)
            verse = int(verse_str)
            
            return book_id, chapter, verse
            
        except (ValueError, AttributeError):
            return None
    
    def get_verse_id(self, ref: str, translation: str = "KJV") -> Optional[int]:
        """
        Get database verse ID for a verse reference.
        
        Args:
            ref: Verse reference like "GEN 1 1"
            translation: Translation code (default: KJV)
            
        Returns:
            Database verse ID or None if not found
        """
        parsed = self.parse_verse_reference(ref)
        if not parsed:
            return None
        
        book_id, chapter, verse = parsed
        cache_key = f"{book_id} {chapter} {verse} {translation}"
        
        return self.verse_cache.get(cache_key)


class CrossReferenceIngester:
    """Handles cross-reference data ingestion."""
    
    def __init__(self, db_path: Path, batch_size: int = 1000):
        """
        Initialize cross-reference ingester.
        
        Args:
            db_path: Path to SQLite database
            batch_size: Batch size for database operations
        """
        self.db_path = db_path
        self.batch_size = batch_size
        self.verse_mapper = VerseMapper(db_path)
        self.stats = CrossReferenceStats()
    
    def parse_json_file(self, file_path: Path) -> List[Dict]:
        """
        Parse a single JSON file containing cross-reference data.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List of verse data dictionaries
        """
        logger = logging.getLogger(__name__)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to list format for processing
            verses = []
            for verse_id, verse_data in data.items():
                if isinstance(verse_data, dict) and 'v' in verse_data and 'r' in verse_data:
                    verses.append({
                        'id': verse_id,
                        'reference': verse_data['v'],
                        'cross_refs': verse_data['r']
                    })
            
            logger.debug(f"Parsed {len(verses)} verses from {file_path}")
            return verses
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []
    
    def process_cross_references(self, verse_data: Dict) -> List[Tuple[int, int]]:
        """
        Process cross-references for a single verse.
        
        Args:
            verse_data: Dictionary with verse data
            
        Returns:
            List of (from_verse_id, to_verse_id) tuples
        """
        logger = logging.getLogger(__name__)
        cross_refs = []
        
        # Get source verse ID
        from_verse_id = self.verse_mapper.get_verse_id(verse_data['reference'])
        if not from_verse_id:
            logger.debug(f"Could not map source verse: {verse_data['reference']}")
            self.stats.verse_mapping_errors += 1
            return cross_refs
        
        # Process each cross-reference
        for ref_id, ref_text in verse_data['cross_refs'].items():
            to_verse_id = self.verse_mapper.get_verse_id(ref_text)
            if to_verse_id:
                cross_refs.append((from_verse_id, to_verse_id))
                self.stats.cross_references_found += 1
            else:
                logger.debug(f"Could not map target verse: {ref_text}")
                self.stats.verse_mapping_errors += 1
        
        return cross_refs
    
    def insert_cross_references(self, cross_refs: List[Tuple[int, int]], dry_run: bool = False) -> None:
        """
        Insert cross-references into database.
        
        Args:
            cross_refs: List of (from_verse_id, to_verse_id) tuples
            dry_run: If True, don't actually insert into database
        """
        if dry_run:
            self.stats.cross_references_created += len(cross_refs)
            return
        
        logger = logging.getLogger(__name__)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Process in batches
            for i in range(0, len(cross_refs), self.batch_size):
                batch = cross_refs[i:i + self.batch_size]
                
                try:
                    # Prepare batch data with relationship type and relevance score
                    batch_data = [
                        (from_id, to_id, 'traditional', 1.0)
                        for from_id, to_id in batch
                    ]
                    
                    # Use INSERT OR IGNORE to avoid duplicates
                    cursor.executemany("""
                        INSERT OR IGNORE INTO cross_references 
                        (from_verse_id, to_verse_id, relationship_type, relevance_score)
                        VALUES (?, ?, ?, ?)
                    """, batch_data)
                    
                    self.stats.cross_references_created += cursor.rowcount
                    conn.commit()
                    
                    logger.debug(f"Inserted batch {i//self.batch_size + 1}: {cursor.rowcount} cross-references")
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to insert batch {i//self.batch_size + 1}: {e}")
                    self.stats.cross_references_skipped += len(batch)
    
    def ingest_from_directory(self, json_dir: Path, dry_run: bool = False) -> None:
        """
        Ingest cross-references from all JSON files in a directory.
        
        Args:
            json_dir: Directory containing JSON files
            dry_run: If True, don't actually insert into database
        """
        logger = logging.getLogger(__name__)
        
        # Find all JSON files
        json_files = list(json_dir.glob("*.json"))
        if not json_files:
            logger.error(f"No JSON files found in {json_dir}")
            return
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        self.stats.files_processed = len(json_files)
        
        all_cross_refs = []
        
        # Process each file
        for i, json_file in enumerate(json_files):
            self.display_progress(i + 1, len(json_files), "Processing files")
            
            verses = self.parse_json_file(json_file)
            
            for verse_data in verses:
                self.stats.verses_processed += 1
                cross_refs = self.process_cross_references(verse_data)
                all_cross_refs.extend(cross_refs)
        
        print()  # New line after progress bar
        
        # Insert all cross-references
        if all_cross_refs:
            logger.info(f"Inserting {len(all_cross_refs):,} cross-references...")
            self.insert_cross_references(all_cross_refs, dry_run)
        
        # Calculate skipped references
        self.stats.cross_references_skipped = (
            self.stats.cross_references_found - self.stats.cross_references_created
        )
    
    def display_progress(self, current: int, total: int, prefix: str = "Progress") -> None:
        """Display progress bar."""
        if total == 0:
            return
        
        percent = (current / total) * 100
        bar_length = 50
        filled_length = int(bar_length * current // total)
        bar = "█" * filled_length + "-" * (bar_length - filled_length)
        
        print(f"\r{prefix}: |{bar}| {current}/{total} ({percent:.1f}%)", end="", flush=True)
    
    def get_stats(self) -> CrossReferenceStats:
        """Get ingestion statistics."""
        return self.stats


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """Setup logging configuration."""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest cross-reference data into SolaGuard database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic ingestion
  python scripts/ingest_cross_references.py
  
  # Dry run to test without database changes
  python scripts/ingest_cross_references.py --dry-run
  
  # Custom paths and batch size
  python scripts/ingest_cross_references.py --json-dir /path/to/json --batch-size 500
  
  # Verbose logging with log file
  python scripts/ingest_cross_references.py --log-level DEBUG --log-file cross_ref_ingestion.log
        """
    )
    
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=Path("data/cross_references"),
        help="Path to directory containing JSON files (default: data/cross_references)"
    )
    
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/bible.db"),
        help="Path to database file (default: data/bible.db)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for database operations (default: 1000)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate without database changes"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Optional log file path"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting SolaGuard Cross-Reference Ingestion")
    logger.info("🔗 Verse Cross-Reference Population for MCP Server")
    
    start_time = time.time()
    
    try:
        # Validate inputs
        if not args.database.exists():
            logger.error(f"Database file not found: {args.database}")
            sys.exit(1)
        
        if not args.json_dir.exists():
            logger.error(f"JSON directory not found: {args.json_dir}")
            sys.exit(1)
        
        # Initialize ingester
        ingester = CrossReferenceIngester(args.database, args.batch_size)
        
        # Run ingestion
        ingester.ingest_from_directory(args.json_dir, args.dry_run)
        
        # Get final statistics
        stats = ingester.get_stats()
        stats.processing_time_seconds = time.time() - start_time
        
        # Display results
        print("\n" + "=" * 60)
        print("CROSS-REFERENCE INGESTION COMPLETE")
        print("=" * 60)
        print(stats.get_summary())
        
        success_rate = (stats.cross_references_created / max(stats.cross_references_found, 1)) * 100
        
        if success_rate > 90:
            print("🎉 Ingestion completed successfully!")
        elif success_rate > 70:
            print("⚠️ Ingestion completed with some issues")
        else:
            print("❌ Ingestion completed with significant issues")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()