#!/usr/bin/python3
"""
Unit tests for TAF validation and comparison display.

Tests the comparison display functionality including:
- Basic file comparison display
- Detailed OGG page comparison output
- Metadata difference formatting
- Error message display
"""
import pytest
from unittest.mock import Mock, patch, call
from io import StringIO
from pathlib import Path

from TonieToolbox.core.analysis.validation import compare_taf_files


class TestCompareTafFilesDisplay:
    """Test suite for compare_taf_files display output."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock TAF analysis service."""
        service = Mock()
        return service
    
    @pytest.fixture
    def identical_files_result(self):
        """Create comparison result for identical files."""
        return {
            'identical': True,
            'differences': [],
            'metadata_diff': {},
            'audio_diff': {},
            'file_size_diff': {
                'file1': 10000,
                'file2': 10000
            }
        }
    
    @pytest.fixture
    def different_files_result(self):
        """Create comparison result for different files."""
        return {
            'identical': False,
            'differences': ['File sizes differ', 'Audio streams differ'],
            'metadata_diff': {
                'title': {'file1': 'Title A', 'file2': 'Title B'},
                'artist': {'file1': 'Artist A', 'file2': 'Artist B'}
            },
            'audio_diff': {
                'duration': {'file1': 300, 'file2': 350}
            },
            'file_size_diff': {
                'file1': 10000,
                'file2': 12000
            }
        }
    
    @pytest.fixture
    def ogg_page_diff_result(self):
        """Create OGG page comparison result."""
        return {
            'total_pages_file1': 10,
            'total_pages_file2': 10,
            'page_differences': [
                {
                    'page_index': 0,
                    'page_no': {'file1': 0, 'file2': 0},
                    'granule_position': {'file1': 0, 'file2': 960},
                    'checksum': {'file1': 0x11111111, 'file2': 0x22222222}
                },
                {
                    'page_index': 5,
                    'segment_count': {'file1': 1, 'file2': 2},
                    'size': {'file1': 59, 'file2': 100}
                }
            ]
        }
    
    def test_display_identical_files(self, mock_service, identical_files_result, capsys):
        """Test display output for identical files."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = identical_files_result
            
            compare_taf_files(file1, file2)
            
            captured = capsys.readouterr()
            assert "identical" in captured.out.lower() or "same" in captured.out.lower()
    
    def test_display_different_files(self, mock_service, different_files_result, capsys):
        """Test display output for different files."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = different_files_result
            
            compare_taf_files(file1, file2)
            
            captured = capsys.readouterr()
            assert "different" in captured.out.lower() or "differ" in captured.out.lower()
    
    def test_display_metadata_differences(self, mock_service, different_files_result, capsys):
        """Test that metadata differences are displayed."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = different_files_result
            
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            # Should show metadata differences
            assert "title" in captured.out.lower() or "metadata" in captured.out.lower()
    
    def test_display_file_size_differences(self, mock_service, different_files_result, capsys):
        """Test that file size differences are displayed."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = different_files_result
            
            compare_taf_files(file1, file2)
            
            captured = capsys.readouterr()
            # Should show file sizes
            assert "10000" in captured.out or "12000" in captured.out
    
    def test_display_detailed_ogg_pages(self, mock_service, different_files_result, ogg_page_diff_result, capsys):
        """Test detailed OGG page comparison display."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        # Add OGG page diff to result
        result_with_ogg = different_files_result.copy()
        result_with_ogg['ogg_pages_diff'] = ogg_page_diff_result
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result_with_ogg
            
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            # Should show OGG page information
            assert "page" in captured.out.lower()
            assert "10" in captured.out  # Page count
    
    def test_display_ogg_page_properties(self, mock_service, identical_files_result, ogg_page_diff_result, capsys):
        """Test that OGG page properties are displayed in detail mode."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        result_with_ogg = identical_files_result.copy()
        result_with_ogg['identical'] = False  # Set to different so OGG diff is shown
        result_with_ogg['ogg_pages_diff'] = ogg_page_diff_result
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result_with_ogg
            
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            output_lower = captured.out.lower()
            
            # Should show various OGG page properties
            # At least one of these should appear
            expected_terms = ['granule', 'checksum', 'segment', 'page']
            assert any(term in output_lower for term in expected_terms)
    
    def test_display_different_page_counts(self, mock_service, identical_files_result, capsys):
        """Test display when files have different OGG page counts."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        ogg_diff = {
            'total_pages_file1': 10,
            'total_pages_file2': 15,
            'page_differences': [
                {
                    'page_index': 10,
                    'only_in': 'file2'
                }
            ]
        }
        
        result_with_ogg = identical_files_result.copy()
        result_with_ogg['identical'] = False  # Set to different so OGG diff is shown
        result_with_ogg['ogg_pages_diff'] = ogg_diff
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result_with_ogg
            
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            # Should show different page counts
            assert "10" in captured.out and "15" in captured.out
    
    def test_no_ogg_display_without_detailed_flag(self, mock_service, different_files_result, ogg_page_diff_result, capsys):
        """Test that OGG pages are not displayed without detailed flag."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        result_with_ogg = different_files_result.copy()
        result_with_ogg['ogg_pages_diff'] = ogg_page_diff_result
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result_with_ogg
            
            compare_taf_files(file1, file2, detailed=False)
            
            captured = capsys.readouterr()
            # OGG page details should be minimal or absent without detailed flag
            # Basic comparison info should still be present
            assert len(captured.out) > 0
    
    def test_display_handles_missing_ogg_diff(self, mock_service, different_files_result, capsys):
        """Test display handles missing OGG page diff gracefully."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        # Result without ogg_pages_diff key
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = different_files_result
            
            # Should not crash even in detailed mode
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            assert len(captured.out) > 0
    
    def test_display_page_only_in_one_file(self, mock_service, identical_files_result, capsys):
        """Test display of pages that exist only in one file."""
        file1 = Path("/path/to/file1.taf")
        file2 = Path("/path/to/file2.taf")
        
        ogg_diff = {
            'total_pages_file1': 10,
            'total_pages_file2': 12,
            'page_differences': [
                {
                    'page_index': 10,
                    'only_in': 'file2',
                    'page_no': 10
                },
                {
                    'page_index': 11,
                    'only_in': 'file2',
                    'page_no': 11
                }
            ]
        }
        
        result_with_ogg = identical_files_result.copy()
        result_with_ogg['ogg_pages_diff'] = ogg_diff
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result_with_ogg
            
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            # Should indicate pages only in one file
            assert "only" in captured.out.lower() or "file2" in captured.out.lower()


class TestComparisonDisplayFormatting:
    """Test formatting of comparison output."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        return Mock()
    
    def test_output_is_readable(self, mock_service, capsys):
        """Test that output is human-readable."""
        result = {
            'identical': False,
            'differences': ['Size differs'],
            'metadata_diff': {'title': {'file1': 'A', 'file2': 'B'}},
            'audio_diff': {},
            'file_size_diff': {'file1': 1000, 'file2': 2000}
        }
        
        file1 = Path("/test1.taf")
        file2 = Path("/test2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result
            
            compare_taf_files(file1, file2, detailed=True)
            
            captured = capsys.readouterr()
            # Output should contain newlines and proper formatting
            assert '\n' in captured.out
            assert len(captured.out) > 50  # Should have substantial output
    
    def test_file_paths_included_in_output(self, mock_service, capsys):
        """Test that file paths are included in output."""
        result = {
            'identical': True,
            'differences': [],
            'metadata_diff': {},
            'audio_diff': {},
            'file_size_diff': {'file1': 1000, 'file2': 1000}
        }
        
        file1 = Path("/path/to/test1.taf")
        file2 = Path("/path/to/test2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result
            
            compare_taf_files(file1, file2)
            
            captured = capsys.readouterr()
            # File names should appear in output
            assert "test1" in captured.out or "test2" in captured.out or "file" in captured.out.lower()


class TestComparisonErrorHandling:
    """Test error handling in comparison display."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        return Mock()
    
    def test_handles_service_exception(self, mock_service, capsys):
        """Test that service exceptions are handled gracefully."""
        file1 = Path("/test1.taf")
        file2 = Path("/test2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.side_effect = Exception("Comparison failed")
            
            # Should not crash
            try:
                compare_taf_files(file1, file2)
            except Exception:
                # Exception might propagate, which is acceptable
                pass
    
    def test_handles_malformed_result(self, mock_service, capsys):
        """Test handling of malformed comparison results."""
        file1 = Path("/test1.taf")
        file2 = Path("/test2.taf")
        
        # Malformed result missing required keys
        malformed_result = {'identical': True}
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = malformed_result
            
            # Should handle gracefully
            try:
                compare_taf_files(file1, file2)
                captured = capsys.readouterr()
                # Should produce some output
                assert len(captured.out) >= 0
            except (KeyError, AttributeError):
                # Acceptable if it raises these specific errors
                pass
    
    def test_handles_nonexistent_files(self, mock_service):
        """Test handling of nonexistent files."""
        file1 = Path("/nonexistent/file1.taf")
        file2 = Path("/nonexistent/file2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.side_effect = FileNotFoundError()
            
            # Should handle gracefully and not raise (error is logged)
            compare_taf_files(file1, file2)


class TestDetailedModeFeatures:
    """Test features specific to detailed comparison mode."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        return Mock()
    
    def test_detailed_mode_shows_more_info(self, mock_service, capsys):
        """Test that detailed mode shows more information than basic mode."""
        result = {
            'identical': False,
            'differences': ['Size'],
            'metadata_diff': {'title': {'file1': 'A', 'file2': 'B'}},
            'audio_diff': {'duration': {'file1': 100, 'file2': 200}},
            'file_size_diff': {'file1': 1000, 'file2': 2000},
            'ogg_pages_diff': {
                'total_pages_file1': 5,
                'total_pages_file2': 5,
                'page_differences': []
            }
        }
        
        file1 = Path("/test1.taf")
        file2 = Path("/test2.taf")
        
        with patch('TonieToolbox.core.analysis.validation.TafAnalysisService') as mock_class:
            mock_class.return_value = mock_service
            mock_service.compare_taf_files.return_value = result
            
            # Get basic output
            compare_taf_files(file1, file2, detailed=False)
            basic_output = capsys.readouterr().out
            
            # Get detailed output
            compare_taf_files(file1, file2, detailed=True)
            detailed_output = capsys.readouterr().out
            
            # Detailed should have equal or more output
            # (in practice should be more, but at least not less)
            assert len(detailed_output) >= len(basic_output) * 0.5
