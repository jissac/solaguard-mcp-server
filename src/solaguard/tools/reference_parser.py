"""
Biblical Reference Parser

Parses biblical references in various formats and converts them to standardized format.
Supports formats like "John 3:16", "Gen 1:1", "Romans 8:28-30", etc.
"""

import re
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class VerseReference:
    """Represents a parsed biblical verse reference."""
    book_id: str
    chapter: int
    verse: int
    
    def __str__(self) -> str:
        return f"{self.book_id} {self.chapter}:{self.verse}"


@dataclass
class VerseRange:
    """Represents a range of biblical verses."""
    book_id: str
    chapter: int
    start_verse: int
    end_verse: int
    
    def __str__(self) -> str:
        if self.start_verse == self.end_verse:
            return f"{self.book_id} {self.chapter}:{self.start_verse}"
        return f"{self.book_id} {self.chapter}:{self.start_verse}-{self.end_verse}"
    
    def to_verse_list(self) -> List[VerseReference]:
        """Convert range to list of individual verse references."""
        return [
            VerseReference(self.book_id, self.chapter, verse)
            for verse in range(self.start_verse, self.end_verse + 1)
        ]


# Book name mappings - supports multiple formats
BOOK_MAPPINGS = {
    # Old Testament
    "genesis": "GEN", "gen": "GEN", "ge": "GEN", "gn": "GEN",
    "exodus": "EXO", "exo": "EXO", "ex": "EXO", "exod": "EXO",
    "leviticus": "LEV", "lev": "LEV", "le": "LEV", "lv": "LEV",
    "numbers": "NUM", "num": "NUM", "nu": "NUM", "nm": "NUM", "nb": "NUM",
    "deuteronomy": "DEU", "deut": "DEU", "deu": "DEU", "dt": "DEU", "de": "DEU",
    "joshua": "JOS", "josh": "JOS", "jos": "JOS", "jsh": "JOS",
    "judges": "JDG", "judg": "JDG", "jdg": "JDG", "jg": "JDG", "jgs": "JDG",
    "ruth": "RUT", "rut": "RUT", "ru": "RUT", "rth": "RUT",
    "1samuel": "1SA", "1sam": "1SA", "1sa": "1SA", "1s": "1SA", "1 samuel": "1SA", "1 sam": "1SA",
    "2samuel": "2SA", "2sam": "2SA", "2sa": "2SA", "2s": "2SA", "2 samuel": "2SA", "2 sam": "2SA",
    "1kings": "1KI", "1king": "1KI", "1ki": "1KI", "1k": "1KI", "1 kings": "1KI", "1 king": "1KI",
    "2kings": "2KI", "2king": "2KI", "2ki": "2KI", "2k": "2KI", "2 kings": "2KI", "2 king": "2KI",
    "1chronicles": "1CH", "1chron": "1CH", "1chr": "1CH", "1ch": "1CH", "1 chronicles": "1CH", "1 chron": "1CH",
    "2chronicles": "2CH", "2chron": "2CH", "2chr": "2CH", "2ch": "2CH", "2 chronicles": "2CH", "2 chron": "2CH",
    "ezra": "EZR", "ezr": "EZR", "ez": "EZR",
    "nehemiah": "NEH", "neh": "NEH", "ne": "NEH",
    "esther": "EST", "est": "EST", "es": "EST",
    "job": "JOB", "jb": "JOB",
    "psalms": "PSA", "psalm": "PSA", "psa": "PSA", "ps": "PSA", "pss": "PSA",
    "proverbs": "PRO", "prov": "PRO", "pro": "PRO", "pr": "PRO", "prv": "PRO",
    "ecclesiastes": "ECC", "eccl": "ECC", "ecc": "ECC", "ec": "ECC", "qoh": "ECC",
    "songofsolomon": "SNG", "song": "SNG", "sng": "SNG", "so": "SNG", "sos": "SNG", "canticles": "SNG",
    "isaiah": "ISA", "isa": "ISA", "is": "ISA",
    "jeremiah": "JER", "jer": "JER", "je": "JER", "jr": "JER",
    "lamentations": "LAM", "lam": "LAM", "la": "LAM",
    "ezekiel": "EZK", "ezek": "EZK", "eze": "EZK", "ezk": "EZK",
    "daniel": "DAN", "dan": "DAN", "da": "DAN", "dn": "DAN",
    "hosea": "HOS", "hos": "HOS", "ho": "HOS",
    "joel": "JOL", "joel": "JOL", "jl": "JOL",
    "amos": "AMO", "amo": "AMO", "am": "AMO",
    "obadiah": "OBA", "obad": "OBA", "oba": "OBA", "ob": "OBA",
    "jonah": "JON", "jon": "JON", "jnh": "JON",
    "micah": "MIC", "mic": "MIC", "mi": "MIC",
    "nahum": "NAM", "nah": "NAM", "na": "NAM",
    "habakkuk": "HAB", "hab": "HAB", "hb": "HAB",
    "zephaniah": "ZEP", "zeph": "ZEP", "zep": "ZEP", "zp": "ZEP",
    "haggai": "HAG", "hag": "HAG", "hg": "HAG",
    "zechariah": "ZEC", "zech": "ZEC", "zec": "ZEC", "zc": "ZEC",
    "malachi": "MAL", "mal": "MAL", "ml": "MAL",
    
    # New Testament
    "matthew": "MAT", "matt": "MAT", "mat": "MAT", "mt": "MAT",
    "mark": "MRK", "mrk": "MRK", "mk": "MRK", "mar": "MRK",
    "luke": "LUK", "luk": "LUK", "lk": "LUK", "lu": "LUK",
    "john": "JHN", "jhn": "JHN", "jn": "JHN", "joh": "JHN",
    "acts": "ACT", "act": "ACT", "ac": "ACT",
    "romans": "ROM", "rom": "ROM", "ro": "ROM", "rm": "ROM",
    "1corinthians": "1CO", "1cor": "1CO", "1co": "1CO", "1c": "1CO", "1 corinthians": "1CO", "1 cor": "1CO",
    "2corinthians": "2CO", "2cor": "2CO", "2co": "2CO", "2c": "2CO", "2 corinthians": "2CO", "2 cor": "2CO",
    "galatians": "GAL", "gal": "GAL", "ga": "GAL",
    "ephesians": "EPH", "eph": "EPH", "ep": "EPH",
    "philippians": "PHP", "phil": "PHP", "php": "PHP", "pp": "PHP",
    "colossians": "COL", "col": "COL", "co": "COL",
    "1thessalonians": "1TH", "1thess": "1TH", "1th": "1TH", "1t": "1TH", "1 thessalonians": "1TH", "1 thess": "1TH",
    "2thessalonians": "2TH", "2thess": "2TH", "2th": "2TH", "2t": "2TH", "2 thessalonians": "2TH", "2 thess": "2TH",
    "1timothy": "1TI", "1tim": "1TI", "1ti": "1TI", "1 timothy": "1TI", "1 tim": "1TI",
    "2timothy": "2TI", "2tim": "2TI", "2ti": "2TI", "2 timothy": "2TI", "2 tim": "2TI",
    "titus": "TIT", "tit": "TIT", "ti": "TIT",
    "philemon": "PHM", "phlm": "PHM", "phm": "PHM", "pm": "PHM",
    "hebrews": "HEB", "heb": "HEB", "he": "HEB",
    "james": "JAS", "jas": "JAS", "jm": "JAS", "ja": "JAS",
    "1peter": "1PE", "1pet": "1PE", "1pe": "1PE", "1p": "1PE", "1 peter": "1PE", "1 pet": "1PE",
    "2peter": "2PE", "2pet": "2PE", "2pe": "2PE", "2p": "2PE", "2 peter": "2PE", "2 pet": "2PE",
    "1john": "1JN", "1jn": "1JN", "1j": "1JN", "1 john": "1JN",
    "2john": "2JN", "2jn": "2JN", "2j": "2JN", "2 john": "2JN",
    "3john": "3JN", "3jn": "3JN", "3j": "3JN", "3 john": "3JN",
    "jude": "JUD", "jud": "JUD", "jd": "JUD",
    "revelation": "REV", "rev": "REV", "re": "REV", "rv": "REV",
}

# Reverse mapping for display names
BOOK_NAMES = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers", "DEU": "Deuteronomy",
    "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth", "1SA": "1 Samuel", "2SA": "2 Samuel",
    "1KI": "1 Kings", "2KI": "2 Kings", "1CH": "1 Chronicles", "2CH": "2 Chronicles",
    "EZR": "Ezra", "NEH": "Nehemiah", "EST": "Esther", "JOB": "Job", "PSA": "Psalms",
    "PRO": "Proverbs", "ECC": "Ecclesiastes", "SNG": "Song of Songs", "ISA": "Isaiah",
    "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel",
    "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah",
    "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah",
    "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts",
    "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians",
    "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians", "1TH": "1 Thessalonians",
    "2TH": "2 Thessalonians", "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus",
    "PHM": "Philemon", "HEB": "Hebrews", "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter",
    "1JN": "1 John", "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}


class ReferenceParseError(Exception):
    """Raised when a biblical reference cannot be parsed."""
    pass


def normalize_book_name(book_name: str) -> str:
    """
    Normalize book name to standard 3-letter code.
    
    Args:
        book_name: Book name in any supported format
        
    Returns:
        Standardized 3-letter book code
        
    Raises:
        ReferenceParseError: If book name is not recognized
    """
    normalized = book_name.lower().strip().replace(" ", "")
    
    if normalized in BOOK_MAPPINGS:
        return BOOK_MAPPINGS[normalized]
    
    # Try with spaces for compound names
    book_with_spaces = book_name.lower().strip()
    if book_with_spaces in BOOK_MAPPINGS:
        return BOOK_MAPPINGS[book_with_spaces]
    
    raise ReferenceParseError(f"Unknown book name: '{book_name}'")


def parse_reference(reference: str) -> Union[VerseReference, VerseRange]:
    """
    Parse a biblical reference string into structured format.
    
    Supports formats:
    - "John 3:16" -> single verse
    - "Gen 1:1" -> single verse  
    - "Romans 8:28-30" -> verse range
    - "1 Cor 13:4-7" -> verse range
    - "Psalm 23:1" -> single verse
    
    Args:
        reference: Biblical reference string
        
    Returns:
        VerseReference or VerseRange object
        
    Raises:
        ReferenceParseError: If reference format is invalid
    """
    if not reference or not reference.strip():
        raise ReferenceParseError("Empty reference")
    
    reference = reference.strip()
    
    # Pattern for biblical references
    # Supports: "Book Chapter:Verse" or "Book Chapter:StartVerse-EndVerse"
    pattern = r'^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$'
    
    match = re.match(pattern, reference)
    if not match:
        raise ReferenceParseError(
            f"Invalid reference format: '{reference}'. "
            f"Expected format: 'Book Chapter:Verse' (e.g., 'John 3:16', 'Romans 8:28-30')"
        )
    
    book_name, chapter_str, start_verse_str, end_verse_str = match.groups()
    
    try:
        book_id = normalize_book_name(book_name)
        chapter = int(chapter_str)
        start_verse = int(start_verse_str)
        
        if chapter < 1:
            raise ReferenceParseError(f"Invalid chapter number: {chapter}")
        if start_verse < 1:
            raise ReferenceParseError(f"Invalid verse number: {start_verse}")
        
        if end_verse_str:
            # Verse range
            end_verse = int(end_verse_str)
            if end_verse < start_verse:
                raise ReferenceParseError(f"End verse ({end_verse}) cannot be before start verse ({start_verse})")
            return VerseRange(book_id, chapter, start_verse, end_verse)
        else:
            # Single verse
            return VerseReference(book_id, chapter, start_verse)
            
    except ValueError as e:
        raise ReferenceParseError(f"Invalid number in reference: {e}")


def get_book_display_name(book_id: str) -> str:
    """
    Get the display name for a book ID.
    
    Args:
        book_id: 3-letter book code (e.g., 'JHN')
        
    Returns:
        Full book name (e.g., 'John')
    """
    return BOOK_NAMES.get(book_id, book_id)


def format_reference(book_id: str, chapter: int, verse: int) -> str:
    """
    Format a reference for display.
    
    Args:
        book_id: 3-letter book code
        chapter: Chapter number
        verse: Verse number
        
    Returns:
        Formatted reference string
    """
    book_name = get_book_display_name(book_id)
    return f"{book_name} {chapter}:{verse}"


if __name__ == "__main__":
    # Test the parser
    test_references = [
        "John 3:16",
        "Gen 1:1", 
        "Romans 8:28-30",
        "1 Cor 13:4-7",
        "Psalm 23:1",
        "Matt 5:3-12",
        "Rev 21:4"
    ]
    
    for ref in test_references:
        try:
            parsed = parse_reference(ref)
            print(f"'{ref}' -> {parsed}")
        except ReferenceParseError as e:
            print(f"'{ref}' -> ERROR: {e}")