#!/usr/bin/env python3
"""
Validation result domain model.

This module contains the ValidationResult value object for representing
validation outcomes in the processing domain.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ValidationResult:
    """
    Represents the result of a validation operation.
    
    This is a value object that encapsulates whether validation passed,
    along with any errors or warnings encountered during validation.
    """
    
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        """Initialize warnings list if not provided."""
        if self.warnings is None:
            object.__setattr__(self, 'warnings', [])
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return len(self.warnings) > 0
    
    @property
    def message_count(self) -> int:
        """Get total count of errors and warnings."""
        return len(self.errors) + len(self.warnings)
    
    def get_summary(self) -> str:
        """Get a human-readable summary of validation results."""
        if self.is_valid and not self.has_warnings:
            return "Validation passed"
        elif self.is_valid and self.has_warnings:
            return f"Validation passed with {len(self.warnings)} warnings"
        else:
            return f"Validation failed with {len(self.errors)} errors" + \
                   (f" and {len(self.warnings)} warnings" if self.has_warnings else "")
    
    def get_all_messages(self) -> List[str]:
        """Get all error and warning messages combined."""
        messages = []
        for error in self.errors:
            messages.append(f"ERROR: {error}")
        for warning in self.warnings:
            messages.append(f"WARNING: {warning}")
        return messages