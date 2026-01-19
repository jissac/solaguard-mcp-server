#!/usr/bin/env python3
"""
Database Table Verification Script

This script verifies that all database tables contain the expected data
and structure for the SolaGuard MCP server.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class TableExpectation:
    """Expected characteristics of a database table."""
    name: str
    min_rows: int
    max_rows: int = None
    required_columns: List[str] = None
    sample_checks: List[Tuple[str, Any]] = None  # (column, expected_type_or_value)


class DatabaseVerifier:
    """Verifies database tables meet expectations."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive information about a table."""
        info = {}
        
        # Get row count
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        info['row_count'] = self.cursor.fetchone()[0]
        
        # Get column info
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        info['columns'] = {col[1]: {'type': col[2], 'not_null': col[3], 'pk': col[5]} 
                          for col in columns}
        
        # Get sample data
        self.cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        info['sample_data'] = self.cursor.fetchall()
        
        return info
    
    def verify_table(self, expectation: TableExpectation) -> Tuple[bool, List[str]]:
        """Verify a single table meets expectations."""
        issues = []
        
        try:
            info = self.get_table_info(expectation.name)
        except sqlite3.OperationalError as e:
            return False, [f"Table {expectation.name} does not exist: {e}"]
        
        # Check row count
        row_count = info['row_count']
        if row_count < expectation.min_rows:
            issues.append(f"Too few rows: {row_count} < {expectation.min_rows}")
        
        if expectation.max_rows and row_count > expectation.max_rows:
            issues.append(f"Too many rows: {row_count} > {expectation.max_rows}")
        
        # Check required columns
        if expectation.required_columns:
            missing_cols = set(expectation.required_columns) - set(info['columns'].keys())
            if missing_cols:
                issues.append(f"Missing columns: {missing_cols}")
        
        # Check sample data
        if expectation.sample_checks and info['sample_data']:
            for col_name, expected in expectation.sample_checks:
                if col_name in info['columns']:
                    # This is a basic check - could be expanded
                    pass
        
        return len(issues) == 0, issues
    
    def print_table_summary(self, table_name: str):
        """Print a detailed summary of a table."""
        try:
            info = self.get_table_info(table_name)
            print(f"\n=== {table_name.upper()} TABLE ===")
            print(f"Rows: {info['row_count']:,}")
            
            print("Columns:")
            for col_name, col_info in info['columns'].items():
                pk_marker = " (PK)" if col_info['pk'] else ""
                null_marker = " NOT NULL" if col_info['not_null'] else ""
                print(f"  - {col_name}: {col_info['type']}{pk_marker}{null_marker}")
            
            if info['sample_data']:
                print("Sample data:")
                for i, row in enumerate(info['sample_data'], 1):
                    print(f"  Row {i}: {row}")
            else:
                print("No sample data available")
                
        except sqlite3.OperationalError as e:
            print(f"\n=== {table_name.upper()} TABLE ===")
            print(f"ERROR: {e}")


def define_expectations() -> List[TableExpectation]:
    """Define what we expect from each table."""
    return [
        TableExpectation(
            name="translations",
            min_rows=1,
            max_rows=10,
            required_columns=["id", "name", "language", "type"],
        ),
        TableExpectation(
            name="books",
            min_rows=66,
            max_rows=66,
            required_columns=["id", "name", "testament", "canonical_order"],
        ),
        TableExpectation(
            name="verses",
            min_rows=31000,  # Bible has ~31,000 verses
            max_rows=100000,  # Allow for multiple translations
            required_columns=["id", "translation_id", "book_id", "chapter", "verse", "text"],
        ),
        TableExpectation(
            name="words",
            min_rows=100000,  # Lots of words in the Bible
            required_columns=["id", "verse_id", "sequence", "text"],
        ),
        TableExpectation(
            name="strongs_dictionary",
            min_rows=0,  # May be empty initially
            required_columns=["number", "word", "definition"],
        ),
        TableExpectation(
            name="cross_references",
            min_rows=0,  # May be empty initially
            required_columns=["id", "from_verse_id", "to_verse_id"],
        ),
    ]


def main():
    """Main verification function."""
    db_path = "data/bible.db"
    
    if not Path(db_path).exists():
        print(f"ERROR: Database file {db_path} does not exist!")
        sys.exit(1)
    
    print("SolaGuard Database Verification")
    print("=" * 50)
    
    expectations = define_expectations()
    all_passed = True
    
    with DatabaseVerifier(db_path) as verifier:
        # Print detailed table summaries
        for expectation in expectations:
            verifier.print_table_summary(expectation.name)
        
        print("\n" + "=" * 50)
        print("VERIFICATION RESULTS")
        print("=" * 50)
        
        # Run verifications
        for expectation in expectations:
            passed, issues = verifier.verify_table(expectation)
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {expectation.name}")
            
            if issues:
                for issue in issues:
                    print(f"  - {issue}")
                all_passed = False
        
        # Additional checks
        print(f"\n{'='*50}")
        print("ADDITIONAL CHECKS")
        print("=" * 50)
        
        # Check for FTS table
        try:
            verifier.cursor.execute("SELECT COUNT(*) FROM verses_fts")
            fts_count = verifier.cursor.fetchone()[0]
            print(f"✅ FTS table exists with {fts_count:,} entries")
        except sqlite3.OperationalError:
            print("❌ FTS table (verses_fts) missing or broken")
            all_passed = False
        
        # Check indexes
        verifier.cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = [row[0] for row in verifier.cursor.fetchall()]
        expected_indexes = ['idx_verses_lookup', 'idx_verses_book', 'idx_verses_translation', 'idx_words_verse', 'idx_words_strongs']
        
        missing_indexes = set(expected_indexes) - set(indexes)
        if missing_indexes:
            print(f"❌ Missing indexes: {missing_indexes}")
            all_passed = False
        else:
            print(f"✅ All expected indexes present: {len(indexes)} total")
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("Database is ready for use.")
    else:
        print("⚠️  SOME VERIFICATIONS FAILED!")
        print("Please check the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()