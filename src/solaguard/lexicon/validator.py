"""
Lexicon Data Validator

Validates lexicon entries for data quality, integrity, and completeness
before database insertion.
"""

import logging
from typing import Set, List, Dict
from .models import LexiconEntry, ValidationResult, is_valid_strongs_format

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validates lexicon entries to ensure data quality and integrity.
    
    Performs validation on:
    - Strong's number format
    - Required field presence
    - Cross-reference integrity
    - Data consistency
    """
    
    def __init__(self, all_strongs_numbers: Set[str] = None):
        """
        Initialize validator.
        
        Args:
            all_strongs_numbers: Set of all valid Strong's numbers for cross-reference validation
        """
        self.all_strongs_numbers = all_strongs_numbers or set()
        self.validation_stats = {
            "total_validated": 0,
            "valid_entries": 0,
            "entries_with_errors": 0,
            "entries_with_warnings": 0,
            "common_errors": {},
            "common_warnings": {}
        }
    
    def validate_entry(self, entry: LexiconEntry) -> ValidationResult:
        """
        Validate a complete lexicon entry.
        
        Args:
            entry: LexiconEntry to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(entry=entry)
        
        # Update stats
        self.validation_stats["total_validated"] += 1
        
        # Validate Strong's number format
        if not self.validate_strongs_number(entry.strongs_number):
            error_msg = f"Invalid Strong's number format: {entry.strongs_number}"
            result.add_error(error_msg)
            self._track_error(error_msg)
        
        # Validate required fields
        missing_fields = self.check_required_fields(entry)
        for field in missing_fields:
            error_msg = f"Missing required field: {field}"
            result.add_error(error_msg)
            self._track_error(error_msg)
        
        # Validate cross-references
        invalid_refs = self.validate_cross_references(entry.cross_references)
        for ref in invalid_refs:
            warning_msg = f"Cross-reference not found in dataset: {ref}"
            result.add_warning(warning_msg)
            self._track_warning(warning_msg)
        
        # Validate data consistency
        consistency_issues = self.check_data_consistency(entry)
        for issue in consistency_issues:
            result.add_warning(issue)
            self._track_warning(issue)
        
        # Update final stats
        if result.is_valid:
            self.validation_stats["valid_entries"] += 1
        else:
            self.validation_stats["entries_with_errors"] += 1
        
        if result.warnings:
            self.validation_stats["entries_with_warnings"] += 1
        
        return result
    
    def validate_strongs_number(self, number: str) -> bool:
        """
        Verify Strong's number format.
        
        Args:
            number: Strong's number to validate
            
        Returns:
            True if format is valid (G/H + digits)
        """
        return is_valid_strongs_format(number)
    
    def check_required_fields(self, entry: LexiconEntry) -> List[str]:
        """
        Check that all required fields are present and non-empty.
        
        Args:
            entry: LexiconEntry to check
            
        Returns:
            List of missing required field names
        """
        missing_fields = []
        
        # Required fields
        required_fields = {
            "strongs_number": entry.strongs_number,
            "word": entry.word,
            "definition": entry.definition,
            "language": entry.language
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value or not str(field_value).strip():
                missing_fields.append(field_name)
        
        # Language must be valid
        if entry.language and entry.language not in ["greek", "hebrew"]:
            missing_fields.append("language (must be 'greek' or 'hebrew')")
        
        return missing_fields
    
    def validate_cross_references(self, refs: List[str]) -> List[str]:
        """
        Check that cross-references point to valid entries.
        
        Args:
            refs: List of Strong's numbers to validate
            
        Returns:
            List of invalid Strong's numbers
        """
        if not self.all_strongs_numbers:
            # If we don't have the complete dataset, skip validation
            return []
        
        invalid_refs = []
        for ref in refs:
            if not self.validate_strongs_number(ref):
                invalid_refs.append(f"{ref} (invalid format)")
            elif ref not in self.all_strongs_numbers:
                invalid_refs.append(f"{ref} (not found)")
        
        return invalid_refs
    
    def check_data_consistency(self, entry: LexiconEntry) -> List[str]:
        """
        Check for data consistency issues.
        
        Args:
            entry: LexiconEntry to check
            
        Returns:
            List of consistency warning messages
        """
        warnings = []
        
        # Check language consistency with Strong's number
        expected_language = "greek" if entry.strongs_number.startswith('G') else "hebrew"
        if entry.language and entry.language != expected_language:
            warnings.append(f"Language '{entry.language}' doesn't match Strong's number '{entry.strongs_number}'")
        
        # Check for empty optional fields that might be expected
        if not entry.pronunciation:
            warnings.append("Missing pronunciation guide")
        
        if not entry.transliteration:
            warnings.append("Missing transliteration")
        
        # Check for very short definitions (might indicate parsing issues)
        if entry.definition and len(entry.definition.strip()) < 10:
            warnings.append("Definition seems unusually short")
        
        # Check for self-references in cross-references
        if entry.strongs_number in entry.cross_references:
            warnings.append("Entry contains self-reference in cross-references")
        
        # Check for duplicate cross-references
        if len(entry.cross_references) != len(set(entry.cross_references)):
            warnings.append("Duplicate cross-references found")
        
        return warnings
    
    def validate_batch(self, entries: List[LexiconEntry]) -> List[ValidationResult]:
        """
        Validate multiple entries in batch.
        
        Args:
            entries: List of LexiconEntry objects to validate
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        # First pass: collect all Strong's numbers for cross-reference validation
        if not self.all_strongs_numbers:
            self.all_strongs_numbers = {entry.strongs_number for entry in entries if entry.strongs_number}
        
        # Second pass: validate each entry
        for entry in entries:
            result = self.validate_entry(entry)
            results.append(result)
        
        return results
    
    def get_validation_summary(self) -> Dict:
        """
        Get summary of validation statistics.
        
        Returns:
            Dictionary with validation statistics
        """
        stats = self.validation_stats.copy()
        
        if stats["total_validated"] > 0:
            stats["success_rate"] = (stats["valid_entries"] / stats["total_validated"]) * 100
            stats["error_rate"] = (stats["entries_with_errors"] / stats["total_validated"]) * 100
            stats["warning_rate"] = (stats["entries_with_warnings"] / stats["total_validated"]) * 100
        else:
            stats["success_rate"] = 0
            stats["error_rate"] = 0
            stats["warning_rate"] = 0
        
        return stats
    
    def get_most_common_issues(self, top_n: int = 5) -> Dict:
        """
        Get the most common validation issues.
        
        Args:
            top_n: Number of top issues to return
            
        Returns:
            Dictionary with top errors and warnings
        """
        # Sort errors and warnings by frequency
        top_errors = sorted(
            self.validation_stats["common_errors"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        top_warnings = sorted(
            self.validation_stats["common_warnings"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return {
            "top_errors": top_errors,
            "top_warnings": top_warnings
        }
    
    def _track_error(self, error_msg: str) -> None:
        """Track error frequency for statistics."""
        # Normalize error message for tracking
        normalized = error_msg.split(':')[0] if ':' in error_msg else error_msg
        self.validation_stats["common_errors"][normalized] = (
            self.validation_stats["common_errors"].get(normalized, 0) + 1
        )
    
    def _track_warning(self, warning_msg: str) -> None:
        """Track warning frequency for statistics."""
        # Normalize warning message for tracking
        normalized = warning_msg.split(':')[0] if ':' in warning_msg else warning_msg
        self.validation_stats["common_warnings"][normalized] = (
            self.validation_stats["common_warnings"].get(normalized, 0) + 1
        )


def create_validator_from_files(lexicon_files: List) -> DataValidator:
    """
    Create a validator with Strong's numbers extracted from filenames.
    
    Args:
        lexicon_files: List of file paths
        
    Returns:
        DataValidator with pre-populated Strong's numbers
    """
    strongs_numbers = set()
    
    for file_path in lexicon_files:
        filename = str(file_path.name) if hasattr(file_path, 'name') else str(file_path)
        
        # Extract Strong's number from filename
        import re
        match = re.search(r'([GH]\d+)\.md$', filename, re.IGNORECASE)
        if match:
            strongs_numbers.add(match.group(1).upper())
    
    return DataValidator(strongs_numbers)


if __name__ == "__main__":
    # Test the validator
    from .models import LexiconEntry
    
    # Create test entries
    valid_entry = LexiconEntry(
        strongs_number="G1",
        word="Α",
        transliteration="A",
        pronunciation="al'-fah",
        definition="the first letter of the alphabet",
        language="greek",
        cross_references=["G260", "G427"]
    )
    
    invalid_entry = LexiconEntry(
        strongs_number="X1",  # Invalid format
        word="",  # Missing required field
        definition="test",
        language="invalid",  # Invalid language
        cross_references=["G999999"]  # Invalid reference
    )
    
    # Test validation
    validator = DataValidator({"G1", "G260", "G427"})
    
    print("Testing valid entry:")
    result1 = validator.validate_entry(valid_entry)
    print(f"Valid: {result1.is_valid}")
    print(f"Errors: {result1.errors}")
    print(f"Warnings: {result1.warnings}")
    print()
    
    print("Testing invalid entry:")
    result2 = validator.validate_entry(invalid_entry)
    print(f"Valid: {result2.is_valid}")
    print(f"Errors: {result2.errors}")
    print(f"Warnings: {result2.warnings}")
    print()
    
    print("Validation summary:")
    summary = validator.get_validation_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")