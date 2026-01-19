#!/usr/bin/env python3
"""
Quick Database Check Script

A simplified version for quick database table inspection.
"""

import sqlite3
from pathlib import Path


def quick_check():
    """Quick overview of database contents."""
    db_path = "data/bible.db"
    
    if not Path(db_path).exists():
        print(f"ERROR: Database file {db_path} does not exist!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = [
        "translations", "books", "verses", "words", 
        "strongs_dictionary", "cross_references"
    ]
    
    print("SolaGuard Database Quick Check")
    print("=" * 40)
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:20} {count:>10,} rows")
        except sqlite3.OperationalError as e:
            print(f"{table:20} ERROR: {e}")
    
    # Check FTS
    try:
        cursor.execute("SELECT COUNT(*) FROM verses_fts")
        fts_count = cursor.fetchone()[0]
        print(f"{'verses_fts':20} {fts_count:>10,} rows")
    except sqlite3.OperationalError:
        print(f"{'verses_fts':20} ERROR: Missing")
    
    conn.close()


if __name__ == "__main__":
    quick_check()