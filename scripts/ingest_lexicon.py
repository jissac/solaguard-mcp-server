#!/usr/bin/env python3
"""
Lexicon Ingestion Script

Main script to ingest Strong's lexicon data from markdown files into the database.
Orchestrates parsing, validation, and database insertion with progress reporting.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.lexicon.parser import LexiconParser, find_lexicon_files
from solaguard.lexicon.validator import DataValidator, create_validator_from_files
from solaguard.lexicon.database import DatabaseWriter, create_cross_references_from_entries
from solaguard.lexicon.models import LexiconEntry, IngestionStats


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
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
        description="Ingest Strong's lexicon data into SolaGuard database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic ingestion
  python scripts/ingest_lexicon.py
  
  # Dry run to test without database changes
  python scripts/ingest_lexicon.py --dry-run
  
  # Custom paths and batch size
  python scripts/ingest_lexicon.py --lexicon-dir /path/to/lexicon --batch-size 500
  
  # Verbose logging with log file
  python scripts/ingest_lexicon.py --log-level DEBUG --log-file lexicon_ingestion.log
        """
    )
    
    parser.add_argument(
        "--lexicon-dir",
        type=Path,
        default=Path("data/lexicon"),
        help="Path to lexicon directory (default: data/lexicon)"
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
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation step (faster but less safe)"
    )
    
    parser.add_argument(
        "--create-indexes",
        action="store_true",
        default=True,
        help="Create database indexes after ingestion (default: True)"
    )
    
    parser.add_argument(
        "--create-fts",
        action="store_true",
        help="Create full-text search table after ingestion"
    )
    
    return parser.parse_args()


def display_progress(current: int, total: int, prefix: str = "Progress") -> None:
    """
    Display progress bar.
    
    Args:
        current: Current progress
        total: Total items
        prefix: Progress bar prefix
    """
    if total == 0:
        return
    
    percent = (current / total) * 100
    bar_length = 50
    filled_length = int(bar_length * current // total)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    
    print(f"\r{prefix}: |{bar}| {current}/{total} ({percent:.1f}%)", end="", flush=True)
    
    if current == total:
        print()  # New line when complete


def ingest_lexicon_data(args: argparse.Namespace) -> IngestionStats:
    """
    Main ingestion function.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        IngestionStats with ingestion results
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()
    
    # Initialize components
    parser = LexiconParser()
    stats = IngestionStats()
    
    # Find lexicon files
    logger.info(f"Searching for lexicon files in {args.lexicon_dir}")
    lexicon_files = find_lexicon_files(args.lexicon_dir)
    
    if not lexicon_files:
        logger.error(f"No lexicon files found in {args.lexicon_dir}")
        return stats
    
    logger.info(f"Found {len(lexicon_files)} lexicon files")
    stats.files_processed = len(lexicon_files)
    
    # Parse files
    logger.info("Parsing lexicon files...")
    parsed_entries = []
    parse_errors = 0
    
    for i, file_path in enumerate(lexicon_files):
        display_progress(i + 1, len(lexicon_files), "Parsing")
        
        try:
            entry = parser.parse_file(file_path)
            parsed_entries.append(entry)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            parse_errors += 1
    
    logger.info(f"Parsed {len(parsed_entries)} entries successfully, {parse_errors} errors")
    
    # Validate entries
    valid_entries = parsed_entries
    if not args.skip_validation:
        logger.info("Validating lexicon entries...")
        validator = create_validator_from_files(lexicon_files)
        
        validation_results = validator.validate_batch(parsed_entries)
        valid_entries = []
        
        for i, result in enumerate(validation_results):
            display_progress(i + 1, len(validation_results), "Validating")
            
            if result.is_valid:
                valid_entries.append(result.entry)
            else:
                stats.validation_errors += len(result.errors)
                logger.debug(f"Validation failed for {result.entry.strongs_number}: {result.errors}")
            
            stats.validation_warnings += len(result.warnings)
        
        # Display validation summary
        validation_summary = validator.get_validation_summary()
        logger.info(f"Validation complete: {validation_summary['success_rate']:.1f}% success rate")
        
        if validation_summary['error_rate'] > 0:
            logger.warning(f"Validation errors: {validation_summary['error_rate']:.1f}%")
        
        # Show most common issues
        common_issues = validator.get_most_common_issues()
        if common_issues['top_errors']:
            logger.warning("Most common validation errors:")
            for error, count in common_issues['top_errors']:
                logger.warning(f"  - {error}: {count} occurrences")
    
    logger.info(f"Ready to process {len(valid_entries)} valid entries")
    
    # Database operations
    if not args.dry_run:
        if not args.database.exists():
            logger.error(f"Database file not found: {args.database}")
            return stats
        
        logger.info("Initializing database writer...")
        db_writer = DatabaseWriter(args.database, args.batch_size)
        
        # Update database schema
        logger.info("Updating database schema...")
        db_writer.update_database_schema()
        
        # Insert lexicon entries
        logger.info("Inserting lexicon entries...")
        db_writer.insert_lexicon_entries(valid_entries)
        
        # Create cross-references
        logger.info("Creating cross-references...")
        cross_refs = create_cross_references_from_entries(valid_entries)
        db_writer.insert_cross_references(cross_refs)
        
        # Create indexes
        if args.create_indexes:
            logger.info("Creating database indexes...")
            db_writer.create_indexes()
        
        # Create FTS table
        if args.create_fts:
            logger.info("Creating full-text search table...")
            db_writer.create_fts_table()
        
        # Get final statistics
        db_stats = db_writer.get_database_stats()
        ingestion_stats = db_writer.get_ingestion_stats()
        
        # Update our stats with database results
        stats.entries_created = ingestion_stats.entries_created
        stats.entries_updated = ingestion_stats.entries_updated
        stats.cross_references_created = ingestion_stats.cross_references_created
        
        logger.info("Database operations complete")
        logger.info(f"Database statistics: {db_stats}")
        
        # Verify data integrity
        logger.info("Verifying data integrity...")
        integrity_check = db_writer.verify_data_integrity()
        if integrity_check['is_valid']:
            logger.info("✅ Data integrity verification passed")
        else:
            logger.warning("⚠️ Data integrity issues found:")
            for issue in integrity_check['issues']:
                logger.warning(f"  - {issue}")
    
    else:
        logger.info("Dry run complete - no database changes made")
        stats.entries_created = len(valid_entries)
    
    # Calculate final statistics
    end_time = time.time()
    stats.processing_time_seconds = end_time - start_time
    
    return stats


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting SolaGuard Lexicon Ingestion")
    logger.info("📖 Strong's Dictionary Population for MCP Server")
    
    try:
        # Run ingestion
        stats = ingest_lexicon_data(args)
        
        # Display final results
        print("\n" + "=" * 60)
        print("LEXICON INGESTION COMPLETE")
        print("=" * 60)
        print(stats.get_summary())
        
        if stats.get_success_rate() > 90:
            print("🎉 Ingestion completed successfully!")
        elif stats.get_success_rate() > 70:
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