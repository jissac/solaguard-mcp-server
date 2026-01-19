#!/usr/bin/env python3
"""
Ingest Bible translations with Strong's references.

This script parses Bible markdown files and populates the database
with verses and Strong's word alignments for multiple translations.

Supported translations:
- Berean Study Bible (BSB)
- King James Version (KJV)

Data filtering:
- Automatically filters out KJV subscription notes (verse 255)
- These are editorial postscripts, not actual biblical text

Note: Lexicon files are kept as raw markdown in data/lexicon/ and accessed on-demand.
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from solaguard.database.schema import INITIAL_BOOKS, SCHEMA_SQL

# Paths to Bible repos
BEREAN_REPO = Path("/Users/ji/Documents/Github/berean-study-bible-with-strongs")
KJV_REPO = Path("/Users/ji/Documents/Github/kingdom-study-tools-for-obsidian")

# Database path
DB_PATH = Path("data/bible.db")

# Source Data Configuration
# We prioritize the local 'data/bible' directory if the user has placed files there.
DATA_DIR = Path("data/bible")
BSB_PATH = DATA_DIR if DATA_DIR.exists() else Path("/Users/ji/Documents/Github/berean-study-bible-with-strongs/bible")
KJV_PATH = Path("/Users/ji/Documents/Github/kingdom-study-tools-for-obsidian/bible") # Keep fallback

# Translation configurations
TRANSLATIONS = [
    {
        "id": "BSB",
        "name": "Berean Study Bible",
        "path": BSB_PATH,
        # Pattern handles ###### 1 (BSB style)
        "verse_pattern": r'^######\s+(\d+)', 
    },
    {
        "id": "KJV",
        "name": "King James Version",
        "path": KJV_PATH,
        # Pattern handles ### 1 (KJV style)
        "verse_pattern": r'^###\s+(\d+)',  
    },
]


def parse_chapter_file(file_path: Path, verse_pattern: str) -> List[Dict]:
    """
    Parse a chapter markdown file using a robust line-by-line state machine.
    
    Args:
        file_path: Path to chapter markdown file
        verse_pattern: Regex pattern to match verse numbers (e.g., r'^###### (\d+)')
    
    Returns:
        List of verse dictionaries
    """
    verses = []
    current_verse_num = None
    current_lines = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line_stripped = line.strip()
        
        # Check for verse header
        match = re.match(verse_pattern, line_stripped)
        if match:
            # Save previous verse if exists
            if current_verse_num is not None:
                verse_text, words = process_verse_text(" ".join(current_lines))
                if verse_text or words:  # Only add if there's content
                    verses.append({
                        'verse': current_verse_num,
                        'text': verse_text,
                        'words': words
                    })
            
            # Start new verse
            verse_num = int(match.group(1))
            
            # Skip KJV subscription notes (verse 255)
            # These are editorial postscripts, not actual biblical text
            if verse_num == 255:
                current_verse_num = None
                current_lines = []
                continue
                
            current_verse_num = verse_num
            current_lines = []
            
            # If there's text on the same line after the header (rare in this format but possible)
            # Remove the header from the line and keep the rest
            # Regex match gives us the header part.
            # We need to be careful with strict replacement.
            # match.group(0) is the header.
            # But line might have trailing chars.
            # Let's assume the header is the start.
            
            # Check if there is content after the header on the same line
            header_end = match.end()
            if header_end < len(line_stripped):
                 rest = line_stripped[header_end:].strip()
                 if rest:
                     current_lines.append(rest)
            
        else:
            # It's content line (or empty, or metadata)
            # Skip metadata headers/separators if they don't look like text
            if line_stripped == "---" or line_stripped.startswith("cssClasses:") or line_stripped.startswith("# "):
                continue
                
            # Skip navigation links like [[Micah 1|←]]
            if "[[" in line_stripped and "←" in line_stripped:
                continue
                
            if current_verse_num is not None and line_stripped:
                current_lines.append(line_stripped)

    # Save the last verse
    if current_verse_num is not None:
        verse_text, words = process_verse_text(" ".join(current_lines))
        if verse_text or words:
            verses.append({
                'verse': current_verse_num,
                'text': verse_text,
                'words': words
            })
    
    return verses


def process_verse_text(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Process raw verse text to extract Strong's numbers and clean text.
    """
    # Extract words with Strong's numbers
    words_with_strongs = []
    
    # Pattern to match: word [[H1234]] or [[H1234]]
    # Improved regex to handle punctuation attached to words
    pattern = r'(\w+(?:[\',-]\w+)?(?:[^\s\[\]]+)?)\s*\[\[([HG]\d+)\]\]|\[\[([HG]\d+)\]\]'
    
    for match in re.finditer(pattern, text):
        word = match.group(1) if match.group(1) else ""
        strongs = match.group(2) if match.group(2) else match.group(3)
        
        # Clean up the word (remove punctuation for the word list if desired, 
        # but for interlinear, keeping some might be okay. 
        # Let's strip purely punctuation if it's not part of the word.)
        word = word.strip(".,;:!?\"() ")
        
        if strongs:
            words_with_strongs.append((word, strongs))
    
    # Create clean text without Strong's tags
    clean_text = re.sub(r'\[\[[HG]\d+\]\]', '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text, words_with_strongs


def get_book_id_from_folder(folder_name: str) -> str:
    """
    Convert folder name to book ID.
    
    Example: "01 - Genesis" -> "GEN"
    """
    # Extract book name
    book_name = folder_name.split(' - ')[1] if ' - ' in folder_name else folder_name
    
    # Handle special cases where folder name differs from schema
    name_mappings = {
        "Song of Solomon": "Song of Songs",
    }
    
    book_name = name_mappings.get(book_name, book_name)
    
    # Map to book ID (INITIAL_BOOKS format: (id, name, testament, author, genre, order))
    book_map = {book[1]: book[0] for book in INITIAL_BOOKS}
    
    return book_map.get(book_name, book_name[:3].upper())


def create_database():
    """Create the database with schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript(SCHEMA_SQL)
    
    # Add translations
    for trans in TRANSLATIONS:
        cursor.execute("""
            INSERT OR IGNORE INTO translations (id, name, language, type)
            VALUES (?, ?, 'en', 'translation')
        """, (trans["id"], trans["name"]))
    
    # Add books (INITIAL_BOOKS format: (id, name, testament, author, genre, order))
    for book in INITIAL_BOOKS:
        cursor.execute("""
            INSERT OR IGNORE INTO books (id, name, testament, author, genre, canonical_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, book)
    
    conn.commit()
    conn.close()
    
    print("✅ Database created")


def get_expected_chapters(book_folder: Path, book_name: str) -> List[int]:
    """
    Get expected chapter numbers from the book.md file.
    
    Args:
        book_folder: Path to book folder
        book_name: Name of the book (e.g., "Micah")
    
    Returns:
        List of expected chapter numbers
    """
    book_file = book_folder / f"{book_name}.md"
    if not book_file.exists():
        return []
    
    try:
        with open(book_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find chapter links like [[Micah 1]], [[Micah 2]], etc.
        pattern = rf'\[\[{re.escape(book_name)} (\d+)\]\]'
        matches = re.findall(pattern, content)
        
        return sorted([int(match) for match in matches])
    except Exception as e:
        print(f"   ⚠️ Error reading {book_file}: {e}")
        return []


def ingest_bible_text():
    """Ingest all Bible translations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for trans_config in TRANSLATIONS:
        trans_id = trans_config["id"]
        trans_name = trans_config["name"]
        bible_path = trans_config["path"]
        verse_pattern = trans_config["verse_pattern"]
        
        if not bible_path.exists():
            print(f"⚠️  Skipping {trans_name} - path not found: {bible_path}")
            continue
        
        print(f"\n📖 Processing {trans_name} ({trans_id})...")
        
        total_verses = 0
        total_words = 0
        
        # Iterate through book folders
        for book_folder in sorted(bible_path.iterdir()):
            if not book_folder.is_dir():
                continue
            
            book_id = get_book_id_from_folder(book_folder.name)
            book_name = book_folder.name.split(' - ')[1] if ' - ' in book_folder.name else book_folder.name
            
            print(f"   {book_name}...", end=" ", flush=True)
            
            book_verses = 0
            
            # Process each chapter file
            for chapter_file in sorted(book_folder.glob("*.md")):
                # Skip the book summary file
                if chapter_file.stem == book_name:
                    continue
                
                # Extract chapter number
                # Filenames are like "Genesis 1.md", "1 Kings 1.md"
                # We need the last number in the filename
                chapter_match = re.findall(r'(\d+)', chapter_file.stem)
                if not chapter_match:
                    print(f"      ⚠️  Skipping {chapter_file.name} - no chapter number found")
                    continue
                
                # The last number is always the chapter number
                chapter_num = int(chapter_match[-1])
                
                # Parse verses
                verses = parse_chapter_file(chapter_file, verse_pattern)
                
                for verse_data in verses:
                    
                    # Insert verse
                    cursor.execute("""
                        INSERT OR REPLACE INTO verses 
                        (book_id, chapter, verse, text, translation_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (book_id, chapter_num, verse_data['verse'], verse_data['text'], trans_id))
                    
                    verse_id = cursor.lastrowid
                    total_verses += 1
                    book_verses += 1
                    
                    # Insert word alignments
                    for position, (word, strongs_num) in enumerate(verse_data['words'], 1):
                        if word and strongs_num:
                            cursor.execute("""
                                INSERT INTO words 
                                (verse_id, sequence, text, strongs, english_equiv, normalized)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (verse_id, position, word, strongs_num, word, word.lower()))
                            total_words += 1
            
            print(f"{book_verses} verses")
            conn.commit()
        
        print(f"   ✅ {trans_name}: {total_verses:,} verses, {total_words:,} Strong's references")
    
    conn.close()


def ingest_lexicon():
    """
    Lexicon files are kept as raw markdown in data/lexicon/ directory.
    They will be accessed on-demand when Strong's definitions are needed.
    This function is a no-op but kept for backwards compatibility.
    """
    print("\n📚 Lexicon files available in data/lexicon/ (accessed on-demand)")
    print("   ✅ No parsing needed - files used as LLM context")


def build_fts_index():
    """Build FTS5 search index."""
    print("\n🔍 Building FTS5 search index...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Populate FTS5 table
    cursor.execute("""
        INSERT INTO verses_fts (rowid, text, book_id)
        SELECT id, text, book_id FROM verses
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ FTS5 index built")


def main():
    """Main ingestion process."""
    print("🚀 Starting Bible Ingestion")
    print("=" * 60)
    
    # Create database
    print("\n1️⃣ Creating database...")
    create_database()
    
    # Ingest Bible text
    print("\n2️⃣ Ingesting Bible translations...")
    ingest_bible_text()
    
    # Build FTS index
    print("\n3️⃣ Building search index...")
    build_fts_index()
    
    # Note about lexicon
    print("\n4️⃣ Lexicon files...")
    ingest_lexicon()
    
    print("\n" + "=" * 60)
    print("🎉 Bible ingestion complete!")
    print(f"📁 Database created at: {DB_PATH}")
    print(f"📚 Lexicon files available at: data/lexicon/")
    print("\n📋 Next steps:")
    print("   1. Test the database:")
    print("      uv run python -c \"import sqlite3; conn = sqlite3.connect('data/bible.db'); print('Verses:', conn.execute('SELECT COUNT(*) FROM verses').fetchone()[0]); print('Words:', conn.execute('SELECT COUNT(*) FROM words').fetchone()[0])\"")
    print("   2. Update server to use data/bible.db")
    print("   3. Run tests: uv run python run_tests.py quick")


if __name__ == "__main__":
    main()
