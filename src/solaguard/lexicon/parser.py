"""
Lexicon Parser

Parses Strong's lexicon markdown files to extract structured data including
definitions, notes, theological significance, and cross-references.
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple, Optional

from .models import LexiconEntry, extract_strongs_from_text, normalize_strongs_number

logger = logging.getLogger(__name__)


class LexiconParseError(Exception):
    """Raised when lexicon file parsing fails."""
    pass


class LexiconParser:
    """
    Parses Strong's lexicon markdown files into structured LexiconEntry objects.
    
    Handles the complete lexicon format including:
    - Strong's number from filename
    - Original script word and transliteration from headers
    - Pronunciation guides
    - Main definition text
    - Theological significance bullets
    - Notes sections
    - Cross-references from all sections
    """
    
    def __init__(self):
        """Initialize the parser with regex patterns."""
        # Pattern for Strong's number in filename (G1.md -> G1)
        self.filename_pattern = r'([GH]\d+)\.md$'
        
        # Pattern for pronunciation guide: _(al'-fah | AL-fa | AL-fa)_
        self.pronunciation_pattern = r'_\(([^)]+)\)_'
        
        # Pattern for cross-references: [[G123]] or [[H456]]
        self.cross_ref_pattern = r'\[\[([GH]\d+)\]\]'
        
        # Section headers
        self.definition_header = r'###\s*Definition'
        self.notes_header = r'###\s*Note'
        self.see_also_header = r'###\s*See also'
    
    def parse_file(self, file_path: Path) -> LexiconEntry:
        """
        Parse a single lexicon markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            LexiconEntry with extracted data
            
        Raises:
            LexiconParseError: If parsing fails
        """
        try:
            # Extract Strong's number from filename
            strongs_number = self.extract_strongs_number(file_path.name)
            
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                content = file_path.read_text(encoding='latin-1')
            
            # Parse all components
            word, transliteration = self.parse_header_info(content)
            pronunciation = self.parse_pronunciation(content)
            definition, theological_significance = self.parse_definition(content)
            notes = self.parse_notes(content)
            cross_references = self.extract_cross_references(content)
            
            # Create entry
            entry = LexiconEntry(
                strongs_number=strongs_number,
                word=word,
                transliteration=transliteration,
                pronunciation=pronunciation,
                definition=definition,
                notes=notes,
                theological_significance=theological_significance,
                cross_references=cross_references
            )
            
            logger.debug(f"Parsed {strongs_number}: {word}")
            return entry
            
        except Exception as e:
            raise LexiconParseError(f"Failed to parse {file_path}: {e}")
    
    def extract_strongs_number(self, filename: str) -> str:
        """
        Extract Strong's number from filename.
        
        Args:
            filename: Filename like "G1.md" or "H123.md"
            
        Returns:
            Strong's number like "G1" or "H123"
            
        Raises:
            LexiconParseError: If filename format is invalid
        """
        match = re.search(self.filename_pattern, filename, re.IGNORECASE)
        if not match:
            raise LexiconParseError(f"Invalid filename format: {filename}")
        
        return normalize_strongs_number(match.group(1))
    
    def parse_header_info(self, content: str) -> Tuple[str, str]:
        """
        Extract original word and transliteration from headers.
        
        For example:
        # G1 Α
        ## A
        
        Args:
            content: File content
            
        Returns:
            Tuple of (original_word, transliteration)
        """
        lines = content.split('\n')
        original_word = ""
        transliteration = ""
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for the main header: # G1 Α
            if line.startswith('# ') and ' ' in line:
                parts = line[2:].split(' ', 1)
                if len(parts) == 2:
                    original_word = parts[1].strip()
            
            # Look for the transliteration header: ## A
            elif line.startswith('## ') and original_word:
                transliteration = line[3:].strip()
                break
        
        return original_word, transliteration
    
    def parse_pronunciation(self, content: str) -> str:
        """
        Extract pronunciation guide from content.
        
        Looks for patterns like: _(al'-fah | AL-fa | AL-fa)_
        
        Args:
            content: File content
            
        Returns:
            Pronunciation guide string
        """
        match = re.search(self.pronunciation_pattern, content)
        if match:
            return match.group(1).strip()
        return ""
    
    def parse_definition(self, content: str) -> Tuple[str, str]:
        """
        Extract main definition and theological significance.
        
        Separates the main definition text from theological bullet points.
        
        Args:
            content: File content
            
        Returns:
            Tuple of (main_definition, theological_significance)
        """
        # Find the Definition section
        definition_match = re.search(self.definition_header, content, re.IGNORECASE)
        if not definition_match:
            return "", ""
        
        # Extract content from Definition section until next ### header
        start_pos = definition_match.end()
        
        # Find the end of the definition section
        next_section = re.search(r'\n###\s+', content[start_pos:])
        if next_section:
            definition_content = content[start_pos:start_pos + next_section.start()]
        else:
            definition_content = content[start_pos:]
        
        # Clean up the content
        definition_content = definition_content.strip()
        
        # Separate main definition from bullet points
        lines = definition_content.split('\n')
        main_def_lines = []
        theological_lines = []
        
        in_bullets = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('- '):
                in_bullets = True
                theological_lines.append(line)
            elif in_bullets and (line.startswith('  ') or line.startswith('-')):
                # Continuation of bullets
                theological_lines.append(line)
            elif not in_bullets:
                main_def_lines.append(line)
        
        main_definition = ' '.join(main_def_lines).strip()
        theological_significance = '\n'.join(theological_lines).strip()
        
        return main_definition, theological_significance
    
    def parse_notes(self, content: str) -> str:
        """
        Extract the Notes section content.
        
        Args:
            content: File content
            
        Returns:
            Notes section text
        """
        # Find the Notes section
        notes_match = re.search(self.notes_header, content, re.IGNORECASE)
        if not notes_match:
            return ""
        
        # Extract content from Notes section until next ### header
        start_pos = notes_match.end()
        
        # Find the end of the notes section
        next_section = re.search(r'\n###\s+', content[start_pos:])
        if next_section:
            notes_content = content[start_pos:start_pos + next_section.start()]
        else:
            notes_content = content[start_pos:]
        
        # Clean up and return
        return notes_content.strip()
    
    def extract_cross_references(self, content: str) -> List[str]:
        """
        Find all Strong's number cross-references in the content.
        
        Searches for [[G123]] and [[H456]] patterns throughout the entire file.
        
        Args:
            content: File content
            
        Returns:
            List of unique Strong's numbers referenced
        """
        return extract_strongs_from_text(content)
    
    def parse_batch(self, file_paths: List[Path]) -> List[Tuple[Path, Optional[LexiconEntry], Optional[str]]]:
        """
        Parse multiple lexicon files in batch.
        
        Args:
            file_paths: List of file paths to parse
            
        Returns:
            List of tuples: (file_path, entry_or_none, error_message_or_none)
        """
        results = []
        
        for file_path in file_paths:
            try:
                entry = self.parse_file(file_path)
                results.append((file_path, entry, None))
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                results.append((file_path, None, str(e)))
        
        return results
    
    def get_parsing_stats(self, results: List[Tuple[Path, Optional[LexiconEntry], Optional[str]]]) -> dict:
        """
        Generate statistics from batch parsing results.
        
        Args:
            results: Results from parse_batch
            
        Returns:
            Dictionary with parsing statistics
        """
        total_files = len(results)
        successful = sum(1 for _, entry, _ in results if entry is not None)
        failed = total_files - successful
        
        # Count languages
        greek_count = sum(1 for _, entry, _ in results 
                         if entry and entry.language == "greek")
        hebrew_count = sum(1 for _, entry, _ in results 
                          if entry and entry.language == "hebrew")
        
        # Count entries with various sections
        with_notes = sum(1 for _, entry, _ in results 
                        if entry and entry.notes)
        with_theological = sum(1 for _, entry, _ in results 
                              if entry and entry.theological_significance)
        with_cross_refs = sum(1 for _, entry, _ in results 
                             if entry and entry.cross_references)
        
        return {
            "total_files": total_files,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total_files * 100) if total_files > 0 else 0,
            "greek_entries": greek_count,
            "hebrew_entries": hebrew_count,
            "entries_with_notes": with_notes,
            "entries_with_theological_significance": with_theological,
            "entries_with_cross_references": with_cross_refs,
        }


def find_lexicon_files(lexicon_dir: Path) -> List[Path]:
    """
    Find all lexicon markdown files in the directory structure.
    
    Args:
        lexicon_dir: Root lexicon directory (e.g., data/lexicon)
        
    Returns:
        List of paths to lexicon files
    """
    lexicon_files = []
    
    # Look for Greek files
    greek_dir = lexicon_dir / "greek"
    if greek_dir.exists():
        lexicon_files.extend(greek_dir.glob("G*.md"))
    
    # Look for Hebrew files
    hebrew_dir = lexicon_dir / "hebrew"
    if hebrew_dir.exists():
        lexicon_files.extend(hebrew_dir.glob("H*.md"))
    
    return sorted(lexicon_files)


if __name__ == "__main__":
    # Test the parser
    parser = LexiconParser()
    
    # Test with the G1 file if it exists
    test_file = Path("data/lexicon/greek/G1.md")
    if test_file.exists():
        try:
            entry = parser.parse_file(test_file)
            print("Parser test successful!")
            print(f"Strong's: {entry.strongs_number}")
            print(f"Word: {entry.word}")
            print(f"Transliteration: {entry.transliteration}")
            print(f"Pronunciation: {entry.pronunciation}")
            print(f"Definition: {entry.definition[:100]}...")
            print(f"Notes: {entry.notes[:100]}...")
            print(f"Theological: {entry.theological_significance}")
            print(f"Cross-refs: {entry.cross_references}")
            print(f"Language: {entry.language}")
            print(f"Valid: {entry.is_valid()}")
        except Exception as e:
            print(f"Parser test failed: {e}")
    else:
        print("Test file not found - parser created successfully")
    
    # Test finding files
    lexicon_dir = Path("data/lexicon")
    if lexicon_dir.exists():
        files = find_lexicon_files(lexicon_dir)
        print(f"Found {len(files)} lexicon files")
        if files:
            print(f"First few: {[f.name for f in files[:5]]}")