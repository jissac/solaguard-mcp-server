#!/usr/bin/env python3
"""
Cross-Reference Verification Script

Verifies that cross-reference data was ingested correctly by showing
actual verse references instead of just database IDs.
"""

import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple


def get_verse_reference(cursor, verse_id: int) -> str:
    """
    Get human-readable verse reference from verse ID.
    
    Args:
        cursor: Database cursor
        verse_id: Database verse ID
        
    Returns:
        Verse reference like "GEN 1:1" or "Unknown"
    """
    cursor.execute("""
        SELECT b.id, v.chapter, v.verse, v.translation_id
        FROM verses v
        JOIN books b ON v.book_id = b.id
        WHERE v.id = ?
    """, (verse_id,))
    
    result = cursor.fetchone()
    if result:
        book_id, chapter, verse, translation = result
        return f"{book_id} {chapter}:{verse} ({translation})"
    else:
        return f"Unknown (ID: {verse_id})"


def verify_cross_references(db_path: Path, sample_size: int = 10) -> None:
    """
    Verify cross-reference data by showing sample entries.
    
    Args:
        db_path: Path to database file
        sample_size: Number of sample cross-references to show
    """
    print(f"🔍 Verifying Cross-Reference Data")
    print(f"Database: {db_path}")
    print("=" * 60)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM cross_references")
        total_count = cursor.fetchone()[0]
        print(f"📊 Total cross-references: {total_count:,}")
        
        # Get sample cross-references
        cursor.execute("""
            SELECT id, from_verse_id, to_verse_id, relationship_type, relevance_score
            FROM cross_references
            ORDER BY id
            LIMIT ?
        """, (sample_size,))
        
        print(f"\n🔍 Sample Cross-References (first {sample_size}):")
        print("-" * 60)
        
        for i, (cr_id, from_id, to_id, rel_type, score) in enumerate(cursor.fetchall(), 1):
            from_ref = get_verse_reference(cursor, from_id)
            to_ref = get_verse_reference(cursor, to_id)
            
            print(f"{i:2d}. {from_ref}")
            print(f"    → {to_ref}")
            print(f"    Type: {rel_type}, Score: {score}")
            print()
        
        # Get some statistics
        print("📈 Cross-Reference Statistics:")
        print("-" * 30)
        
        # Count by relationship type
        cursor.execute("""
            SELECT relationship_type, COUNT(*) 
            FROM cross_references 
            GROUP BY relationship_type
        """)
        for rel_type, count in cursor.fetchall():
            print(f"  {rel_type}: {count:,}")
        
        # Average cross-references per verse
        cursor.execute("""
            SELECT COUNT(DISTINCT from_verse_id) as unique_verses
            FROM cross_references
        """)
        unique_verses = cursor.fetchone()[0]
        avg_refs = total_count / unique_verses if unique_verses > 0 else 0
        print(f"  Unique source verses: {unique_verses:,}")
        print(f"  Average refs per verse: {avg_refs:.1f}")
        
        # Test a specific well-known verse
        print(f"\n🎯 Testing Well-Known Verses:")
        print("-" * 30)
        
        test_verses = [
            ("GEN", 1, 1),  # Genesis 1:1
            ("JHN", 3, 16), # John 3:16
            ("PSA", 23, 1), # Psalm 23:1
        ]
        
        for book_id, chapter, verse in test_verses:
            cursor.execute("""
                SELECT v.id FROM verses v
                WHERE v.book_id = ? AND v.chapter = ? AND v.verse = ? AND v.translation_id = 'KJV'
                LIMIT 1
            """, (book_id, chapter, verse))
            
            result = cursor.fetchone()
            if result:
                verse_id = result[0]
                
                # Count cross-references for this verse
                cursor.execute("""
                    SELECT COUNT(*) FROM cross_references
                    WHERE from_verse_id = ?
                """, (verse_id,))
                
                ref_count = cursor.fetchone()[0]
                print(f"  {book_id} {chapter}:{verse} has {ref_count} cross-references")
                
                # Show first few cross-references
                if ref_count > 0:
                    cursor.execute("""
                        SELECT to_verse_id FROM cross_references
                        WHERE from_verse_id = ?
                        LIMIT 3
                    """, (verse_id,))
                    
                    print(f"    Sample references:")
                    for (to_id,) in cursor.fetchall():
                        to_ref = get_verse_reference(cursor, to_id)
                        print(f"      → {to_ref}")
            else:
                print(f"  {book_id} {chapter}:{verse} not found in database")


def main():
    """Main verification function."""
    db_path = Path("data/bible.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    try:
        verify_cross_references(db_path, sample_size=5)
        print(f"\n✅ Cross-reference verification complete!")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()