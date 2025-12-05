#!/usr/bin/env python3
"""
Unit tests for sorting utilities.

Tests natural sorting implementation.
"""

import pytest
from TonieToolbox.core.utils.sorting import natural_sort_key, natural_sort


class TestNaturalSortKey:
    """Test natural sort key generation."""
    
    def test_simple_number(self):
        """Test sorting key for simple numbers."""
        key = natural_sort_key("file10")
        assert 10 in key
    
    def test_mixed_string_and_numbers(self):
        """Test sorting key for mixed content."""
        key1 = natural_sort_key("file1.txt")
        key2 = natural_sort_key("file10.txt")
        key3 = natural_sort_key("file2.txt")
        
        # file1 < file2 < file10 (numeric order)
        assert key1 < key3 < key2
    
    def test_no_numbers(self):
        """Test sorting key without numbers."""
        key = natural_sort_key("filename")
        assert all(isinstance(x, str) for x in key)
    
    def test_multiple_numbers(self):
        """Test sorting key with multiple numbers."""
        key = natural_sort_key("chapter1track5")
        # Should split into: 'chapter', 1, 'track', 5
        assert 1 in key
        assert 5 in key
    
    def test_leading_zeros(self):
        """Test handling of leading zeros."""
        key1 = natural_sort_key("file001")
        key2 = natural_sort_key("file01")
        key3 = natural_sort_key("file1")
        
        # All should be treated as number 1
        assert key1 == key2 == key3
    
    def test_case_insensitive(self):
        """Test case-insensitive sorting."""
        key1 = natural_sort_key("FileA")
        key2 = natural_sort_key("filea")
        
        # Should be equal due to case-insensitivity
        assert key1 == key2


class TestNaturalSort:
    """Test natural sorting function."""
    
    def test_simple_numeric_sort(self):
        """Test sorting simple numbered files."""
        files = ["file10.txt", "file1.txt", "file5.txt", "file20.txt"]
        sorted_files = natural_sort(files)
        
        assert sorted_files == ["file1.txt", "file5.txt", "file10.txt", "file20.txt"]
    
    def test_chapter_sorting(self):
        """Test sorting chapter files."""
        chapters = [
            "Chapter 10.mp3",
            "Chapter 1.mp3",
            "Chapter 2.mp3",
            "Chapter 20.mp3"
        ]
        sorted_chapters = natural_sort(chapters)
        
        expected = [
            "Chapter 1.mp3",
            "Chapter 2.mp3",
            "Chapter 10.mp3",
            "Chapter 20.mp3"
        ]
        assert sorted_chapters == expected
    
    def test_mixed_content(self):
        """Test sorting mixed content."""
        items = [
            "track12",
            "track2",
            "track1",
            "track100"
        ]
        sorted_items = natural_sort(items)
        
        assert sorted_items == ["track1", "track2", "track12", "track100"]
    
    def test_no_numbers(self):
        """Test sorting strings without numbers."""
        items = ["zebra", "apple", "banana", "cherry"]
        sorted_items = natural_sort(items)
        
        assert sorted_items == ["apple", "banana", "cherry", "zebra"]
    
    def test_empty_list(self):
        """Test sorting empty list."""
        assert natural_sort([]) == []
    
    def test_single_item(self):
        """Test sorting single item."""
        assert natural_sort(["item"]) == ["item"]
    
    def test_taf_files(self):
        """Test sorting .taf files."""
        files = [
            "500304E0.taf",
            "500304E1.taf",
            "500304EA.taf",
            "500304E2.taf"
        ]
        sorted_files = natural_sort(files)
        
        # Should maintain natural order
        assert sorted_files[0] == "500304E0.taf"
        assert sorted_files[-1] == "500304EA.taf"
    
    def test_preserves_original(self):
        """Test that original list is not modified."""
        original = ["file10", "file1", "file5"]
        copy_of_original = original.copy()
        
        natural_sort(original)
        
        # Original should be unchanged
        assert original == copy_of_original
    
    def test_complex_filenames(self):
        """Test sorting complex real-world filenames."""
        files = [
            "01_Introduction.mp3",
            "02_Chapter_1.mp3",
            "10_Epilogue.mp3",
            "03_Chapter_2.mp3"
        ]
        sorted_files = natural_sort(files)
        
        expected = [
            "01_Introduction.mp3",
            "02_Chapter_1.mp3",
            "03_Chapter_2.mp3",
            "10_Epilogue.mp3"
        ]
        assert sorted_files == expected
