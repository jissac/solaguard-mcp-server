import sqlite3
from pathlib import Path

DB_PATH = Path("data/bible.db")

def verify_counts():
    if not DB_PATH.exists():
        print("❌ Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n📊 Verification Report")
    print("=" * 40)

    # Total Counts
    for trans in ["BSB", "KJV"]:
        cursor.execute("SELECT COUNT(*) FROM verses WHERE translation_id = ?", (trans,))
        count = cursor.fetchone()[0]
        status = "✅ Perfect" if count == 31102 else f"⚠️ {count - 31102:+d}"
        print(f"{trans}: {count:,} verses ({status})")

    print("\n📖 Detailed Book Counts (Differences only)")
    print("-" * 40)
    
    # Check for discrepancies
    cursor.execute("""
        SELECT book_id, 
               SUM(CASE WHEN translation_id='BSB' THEN 1 ELSE 0 END) as bsb_count,
               SUM(CASE WHEN translation_id='KJV' THEN 1 ELSE 0 END) as kjv_count
        FROM verses 
        GROUP BY book_id
        HAVING bsb_count != kjv_count OR bsb_count = 0
    """)
    
    diffs = cursor.fetchall()
    if not diffs:
        print("No discrepancies found between translations!")
    else:
        print(f"{'Book':<5} | {'BSB':<6} | {'KJV':<6} | {'Diff':<5}")
        for book, bsb, kjv in diffs:
            print(f"{book:<5} | {bsb:<6} | {kjv:<6} | {kjv-bsb:+d}")

    conn.close()

if __name__ == "__main__":
    verify_counts()
