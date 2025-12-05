#!/usr/bin/env python3
"""
Sorting utilities for TonieToolbox.

Provides natural (human-friendly) sorting functions.
"""

import re
from typing import List, Any


def natural_sort_key(text: str) -> List[Any]:
    """
    Generate a key for natural sorting.
    
    Converts a string to a list of mixed integers and strings for natural sorting.
    This allows sorting like: file1, file2, file10 instead of file1, file10, file2
    
    Args:
        text: String to convert to sort key
        
    Returns:
        List of integers and strings for sorting
        
    Example:
        >>> natural_sort_key("file10.taf")
        ['file', 10, '.taf']
        >>> natural_sort_key("file2.taf")
        ['file', 2, '.taf']
    """
    def atoi(text):
        """Convert text to integer if possible."""
        return int(text) if text.isdigit() else text.lower()
    
    return [atoi(c) for c in re.split(r'(\d+)', str(text))]


def natural_sort(items: List[str]) -> List[str]:
    """
    Sort a list of strings using natural (human-friendly) sorting.
    
    This ensures that numeric parts are sorted numerically rather than
    lexicographically. For example: ['file1', 'file10', 'file2'] becomes
    ['file1', 'file2', 'file10'].
    
    Args:
        items: List of strings to sort
        
    Returns:
        Sorted list of strings
        
    Example:
        >>> natural_sort(['file10.taf', 'file2.taf', 'file1.taf'])
        ['file1.taf', 'file2.taf', 'file10.taf']
    """
    return sorted(items, key=natural_sort_key)
