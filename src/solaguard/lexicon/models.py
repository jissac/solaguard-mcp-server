"""
Lexicon Data Models

Data structures for Strong's lexicon entries, validation results, and cross-references.
Supports rich lexicon data including definitions, notes, theological significance, and cross-references.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class LexiconEntry:
    """
    Represents a complete Strong's lexicon entry with all available information.
    
    Attributes:
        strongs_number: Strong's number (e.g., "G1", "H123")
        word: Original script word (e.g., "Α", "אֱלֹהִים")
        transliteration: Romanized form (e.g., "A", "elohim")
        pronunciation: Phonetic guide (e.g., "al'-fah | AL-fa | AL-fa")
        definition: Main definition text
        notes: Additional notes and usage information
        theological_significance: Theological context and meaning (bullet points)
        cross_references: Referenced Strong's numbers from all sections
        language: "greek" or "hebrew"
    """
    strongs_number: str
    word: str
    transliteration: str = ""
    pronunciation: str = ""
    definition: str = ""
    notes: str = ""
    theological_significance: str = ""
    cross_references: List[str] = field(default_factory=list)
    language: str = ""
    
    def is_valid(self) -> bool:
        """
        Check if entry has required fields for database insertion.
        
        Returns:
            True if entry has minimum required data
        """
        return bool(
            self.strongs_number and 
            self.word and 
            self.definition and
            self.language in ["greek", "hebrew"]
        )
    
    def get_language_from_strongs(self) -> str:
        """
        Determine language from Strong's number format.
        
        Returns:
            "greek" for G numbers, "hebrew" for H numbers
        """
        if self.strongs_number.startswith('G'):
            return "greek"
        elif self.strongs_number.startswith('H'):
            return "hebrew"
        else:
            return ""
    
    def extract_theological_bullets(self, definition_text: str) -> tuple[str, str]:
        """
        Separate main definition from theological bullet points.
        
        Args:
            definition_text: Raw definition text with potential bullets
            
        Returns:
            Tuple of (main_definition, theological_bullets)
        """
        lines = definition_text.split('\n')
        main_def_lines = []
        theological_lines = []
        
        in_bullets = False
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                in_bullets = True
                theological_lines.append(line)
            elif in_bullets and line:
                # Continue collecting bullets
                theological_lines.append(line)
            elif not in_bullets and line:
                main_def_lines.append(line)
        
        main_definition = ' '.join(main_def_lines).strip()
        theological_significance = '\n'.join(theological_lines).strip()
        
        return main_definition, theological_significance
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Auto-determine language if not set
        if not self.language:
            self.language = self.get_language_from_strongs()
        
        # Clean up cross-references (remove duplicates, sort)
        if self.cross_references:
            self.cross_references = sorted(list(set(self.cross_references)))


@dataclass
class ValidationResult:
    """
    Results from validating a lexicon entry.
    
    Attributes:
        is_valid: Whether the entry passed validation
        errors: List of validation errors
        warnings: List of validation warnings
        entry: The validated entry (may be modified during validation)
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    entry: Optional[LexiconEntry] = None
    
    def add_error(self, message: str) -> None:
        """
        Add a validation error.
        
        Args:
            message: Error message
        """
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """
        Add a validation warning.
        
        Args:
            message: Warning message
        """
        self.warnings.append(message)
    
    def has_issues(self) -> bool:
        """Check if there are any errors or warnings."""
        return len(self.errors) > 0 or len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Get a summary of validation results."""
        if self.is_valid and not self.warnings:
            return "Valid"
        elif self.is_valid and self.warnings:
            return f"Valid with {len(self.warnings)} warning(s)"
        else:
            return f"Invalid: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"


@dataclass
class CrossReference:
    """
    Represents a cross-reference relationship between Strong's numbers.
    
    Attributes:
        from_strongs: Source Strong's number
        to_strongs: Referenced Strong's number
        context: Context where the reference was found (e.g., "definition", "notes")
    """
    from_strongs: str
    to_strongs: str
    context: str = "unknown"
    
    def is_valid(self) -> bool:
        """Check if cross-reference has required fields."""
        return bool(
            self.from_strongs and 
            self.to_strongs and 
            self.from_strongs != self.to_strongs
        )


@dataclass
class IngestionStats:
    """
    Statistics from the lexicon ingestion process.
    
    Attributes:
        files_processed: Number of files processed
        entries_created: Number of valid entries created
        entries_updated: Number of existing entries updated
        validation_errors: Number of validation errors
        validation_warnings: Number of validation warnings
        cross_references_created: Number of cross-reference relationships created
        processing_time_seconds: Total processing time
    """
    files_processed: int = 0
    entries_created: int = 0
    entries_updated: int = 0
    validation_errors: int = 0
    validation_warnings: int = 0
    cross_references_created: int = 0
    processing_time_seconds: float = 0.0
    
    def get_success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.files_processed == 0:
            return 0.0
        successful = self.entries_created + self.entries_updated
        return (successful / self.files_processed) * 100.0
    
    def get_summary(self) -> str:
        """Get a human-readable summary of ingestion results."""
        return (
            f"Processed {self.files_processed} files in {self.processing_time_seconds:.1f}s\n"
            f"Created: {self.entries_created}, Updated: {self.entries_updated}\n"
            f"Errors: {self.validation_errors}, Warnings: {self.validation_warnings}\n"
            f"Cross-references: {self.cross_references_created}\n"
            f"Success rate: {self.get_success_rate():.1f}%"
        )


# Utility functions for working with Strong's numbers
def is_valid_strongs_format(strongs_number: str) -> bool:
    """
    Validate Strong's number format.
    
    Args:
        strongs_number: Strong's number to validate
        
    Returns:
        True if format is valid (G/H followed by digits)
    """
    if not strongs_number:
        return False
    
    pattern = r'^[GH]\d+$'
    return bool(re.match(pattern, strongs_number))


def extract_strongs_from_text(text: str) -> List[str]:
    """
    Extract all Strong's number references from text.
    
    Args:
        text: Text that may contain [[G123]] or [[H456]] references
        
    Returns:
        List of Strong's numbers found
    """
    if not text:
        return []
    
    pattern = r'\[\[([GH]\d+)\]\]'
    matches = re.findall(pattern, text)
    return list(set(matches))  # Remove duplicates


def get_language_from_strongs(strongs_number: str) -> str:
    """
    Determine language from Strong's number.
    
    Args:
        strongs_number: Strong's number (e.g., "G1", "H123")
        
    Returns:
        "greek", "hebrew", or empty string if invalid
    """
    if not strongs_number:
        return ""
    
    if strongs_number.startswith('G'):
        return "greek"
    elif strongs_number.startswith('H'):
        return "hebrew"
    else:
        return ""


def normalize_strongs_number(strongs_number: str) -> str:
    """
    Normalize Strong's number format.
    
    Args:
        strongs_number: Strong's number in various formats
        
    Returns:
        Normalized Strong's number (e.g., "G1", "H123")
    """
    if not strongs_number:
        return ""
    
    # Remove any whitespace and convert to uppercase
    normalized = strongs_number.strip().upper()
    
    # Ensure it starts with G or H
    if not normalized.startswith(('G', 'H')):
        return ""
    
    # Extract the number part
    number_part = normalized[1:]
    if not number_part.isdigit():
        return ""
    
    # Return normalized format
    return f"{normalized[0]}{int(number_part)}"


if __name__ == "__main__":
    # Test the data models
    
    # Test LexiconEntry
    entry = LexiconEntry(
        strongs_number="G1",
        word="Α",
        transliteration="A",
        pronunciation="al'-fah | AL-fa | AL-fa",
        definition="of Hebrew origin; the first letter of the alphabet; figuratively, only (from its use as a numeral) the first; Alpha.",
        theological_significance="- first letter of Greek alphabet\n- Christ is the Alpha to indicate that he is the beginning and the end",
        notes="Often used (usually ἄν, before a vowel) also in composition (as a contraction from [[G427]]) in the sense of privation; so, in many words, beginning with this letter; occasionally in the sense of union (as a contraction of [[G260]]).",
        cross_references=["G260", "G427"]
    )
    
    print("LexiconEntry test:")
    print(f"Valid: {entry.is_valid()}")
    print(f"Language: {entry.language}")
    print(f"Cross-refs: {entry.cross_references}")
    print()
    
    # Test ValidationResult
    result = ValidationResult()
    result.add_warning("Missing pronunciation guide")
    result.entry = entry
    
    print("ValidationResult test:")
    print(f"Summary: {result.get_summary()}")
    print()
    
    # Test utility functions
    print("Utility function tests:")
    print(f"Valid G1: {is_valid_strongs_format('G1')}")
    print(f"Valid H123: {is_valid_strongs_format('H123')}")
    print(f"Invalid X1: {is_valid_strongs_format('X1')}")
    print(f"Extract from text: {extract_strongs_from_text('See [[G260]] and [[G427]]')}")
    print(f"Language from G1: {get_language_from_strongs('G1')}")
    print(f"Normalize 'g001': {normalize_strongs_number('g001')}")