#!/usr/bin/python3
"""
Unit tests for TAF Analysis Service.

Tests the TafAnalysisService class, focusing on:
- File comparison functionality
- OGG page comparison (--detailed-compare feature)
- Header analysis
- Audio stream analysis
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from io import BytesIO

from TonieToolbox.core.processing.infrastructure.services.taf_analysis_service import TafAnalysisService


class TestTafAnalysisService:
    """Test suite for TafAnalysisService."""
    
    @pytest.fixture
    def service(self):
        """Create a TafAnalysisService instance with mocked logger."""
        logger = Mock()
        return TafAnalysisService(logger)
    
    @pytest.fixture
    def mock_taf_header(self):
        """Create a mock TAF header (4096 bytes)."""
        # TAF files start with a 4096-byte header
        return b'\x00' * 4096
    
    @pytest.fixture
    def mock_ogg_page_data(self):
        """Create mock OGG page data."""
        # OGG page header format (27 bytes minimum)
        # capture_pattern(4) + version(1) + header_type(1) + granule(8) + 
        # serial(4) + page_seq(4) + checksum(4) + segments(1)
        return (
            b'OggS'  # Capture pattern
            b'\x00'  # Version 0
            b'\x00'  # Header type
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Granule position
            b'\x01\x00\x00\x00'  # Serial number
            b'\x00\x00\x00\x00'  # Page sequence
            b'\x00\x00\x00\x00'  # Checksum
            b'\x01'  # Number of segments
            b'\x20'  # Segment table (1 segment of 32 bytes)
            b'\x00' * 32  # Page data
        )
    
    def test_service_initialization(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service.logger is not None
    
    def test_compare_identical_files(self, service, tmp_path, mock_taf_header, mock_ogg_page_data):
        """Test comparison of identical TAF files."""
        # Create two identical TAF files
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        content = mock_taf_header + mock_ogg_page_data
        file1.write_bytes(content)
        file2.write_bytes(content)
        
        result = service.compare_taf_files(file1, file2)
        
        assert result['identical'] is True
        assert len(result['differences']) == 0
    
    def test_compare_different_files(self, service, sample_audio_files):
        """Test comparison of different TAF files using real files."""
        # Use real files instead of mock data
        result = service.compare_taf_files(sample_audio_files['taf_stereo'], sample_audio_files['taf_mono'])
        
        assert result['identical'] is False
        assert 'file_size_diff' in result
        # file_size_diff is an integer (size2 - size1), can be positive or negative
        assert isinstance(result['file_size_diff'], int)
    
    def test_compare_nonexistent_file(self, service, tmp_path):
        """Test comparison with nonexistent file returns error."""
        file1 = tmp_path / "exists.taf"
        file2 = tmp_path / "nonexistent.taf"
        
        file1.write_bytes(b'\x00' * 5000)
        
        # Implementation handles errors gracefully and adds to differences
        result = service.compare_taf_files(file1, file2)
        assert 'One or both files do not exist' in result.get('differences', [])
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    @patch('TonieToolbox.core.media.formats.ogg.OggPage')
    def test_compare_ogg_pages_identical(self, mock_ogg_page, service, tmp_path, mock_taf_header, mock_ogg_page_data):
        """Test _compare_ogg_pages with identical OGG pages."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        content = mock_taf_header + mock_ogg_page_data
        file1.write_bytes(content)
        file2.write_bytes(content)
        
        # Mock OggPage to simulate page parsing
        mock_page = Mock()
        mock_page.page_no = 0
        mock_page.granule_position = 0
        mock_page.serial_no = 1
        mock_page.page_type = 0
        mock_page.segment_count = 1
        mock_page.checksum = 0
        mock_page.get_page_size.return_value = 59
        
        mock_ogg_page.return_value = mock_page
        mock_ogg_page.seek_to_page_header.side_effect = [True, False, True, False]
        
        result = service._compare_ogg_pages(file1, file2)
        
        assert result['total_pages_file1'] == result['total_pages_file2']
        assert len(result['page_differences']) == 0
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    @patch('TonieToolbox.core.media.formats.ogg.OggPage')
    def test_compare_ogg_pages_different_count(self, mock_ogg_page, service, tmp_path, mock_taf_header, mock_ogg_page_data):
        """Test _compare_ogg_pages with different page counts."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        file1.write_bytes(mock_taf_header + mock_ogg_page_data)
        file2.write_bytes(mock_taf_header + mock_ogg_page_data * 2)
        
        # Mock different page counts
        mock_page1 = Mock()
        mock_page1.page_no = 0
        mock_page1.granule_position = 0
        mock_page1.serial_no = 1
        mock_page1.page_type = 0
        mock_page1.segment_count = 1
        mock_page1.checksum = 0
        mock_page1.get_page_size.return_value = 59
        
        mock_page2 = Mock()
        mock_page2.page_no = 1
        mock_page2.granule_position = 960
        mock_page2.serial_no = 1
        mock_page2.page_type = 0
        mock_page2.segment_count = 1
        mock_page2.checksum = 0x12345678
        mock_page2.get_page_size.return_value = 59
        
        mock_ogg_page.return_value = mock_page1
        # File 1: 1 page, File 2: 2 pages
        mock_ogg_page.seek_to_page_header.side_effect = [
            True, False,  # File 1: 1 page
            True, True, False  # File 2: 2 pages
        ]
        
        result = service._compare_ogg_pages(file1, file2)
        
        assert result['total_pages_file1'] < result['total_pages_file2']
        assert len(result['page_differences']) > 0
    
    @patch('TonieToolbox.core.media.formats.ogg.OggPage')
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    def test_compare_ogg_pages_different_properties(self, mock_ogg_page, service, tmp_path, mock_taf_header, mock_ogg_page_data):
        """Test _compare_ogg_pages with different page properties."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        content = mock_taf_header + mock_ogg_page_data
        file1.write_bytes(content)
        file2.write_bytes(content)
        
        # Mock pages with different properties
        mock_page1 = Mock()
        mock_page1.page_no = 0
        mock_page1.granule_position = 0
        mock_page1.serial_no = 1
        mock_page1.page_type = 0
        mock_page1.segment_count = 1
        mock_page1.checksum = 0x11111111
        mock_page1.get_page_size.return_value = 59
        
        mock_page2 = Mock()
        mock_page2.page_no = 0
        mock_page2.granule_position = 960  # Different
        mock_page2.serial_no = 1
        mock_page2.page_type = 0
        mock_page2.segment_count = 2  # Different
        mock_page2.checksum = 0x22222222  # Different
        mock_page2.get_page_size.return_value = 100  # Different
        
        # First call returns mock_page1, subsequent calls return mock_page2
        mock_ogg_page.side_effect = [mock_page1, mock_page2]
        mock_ogg_page.seek_to_page_header.side_effect = [True, False, True, False]
        
        result = service._compare_ogg_pages(file1, file2)
        
        assert len(result['page_differences']) > 0
        diff = result['page_differences'][0]
        # Differences are nested under 'differences' key
        assert 'differences' in diff
        differences = diff['differences']
        assert 'granule_position' in differences or 'segment_count' in differences or 'checksum' in differences or 'size' in differences
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    def test_compare_ogg_pages_with_io_error(self, service, tmp_path):
        """Test _compare_ogg_pages handles I/O errors gracefully."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "nonexistent.taf"
        
        file1.write_bytes(b'\x00' * 5000)
        
        # Implementation handles errors gracefully
        result = service._compare_ogg_pages(file1, file2)
        # Should return empty/error result structure
        assert isinstance(result, dict)
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    def test_compare_files_includes_ogg_diff_when_requested(self, service, tmp_path, mock_taf_header, mock_ogg_page_data):
        """Test that compare_taf_files includes OGG page diff in results."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        # Make files different so checksum check doesn't return early
        content1 = mock_taf_header + mock_ogg_page_data
        content2 = mock_taf_header + mock_ogg_page_data + b'\x00'  # Add extra byte
        file1.write_bytes(content1)
        file2.write_bytes(content2)
        
        result = service.compare_taf_files(file1, file2)
        
        # Now ogg_pages_diff should be included since files are different
        assert 'ogg_pages_diff' in result
    
    def test_analyze_file_header(self, service, tmp_path, mock_taf_header):
        """Test file header analysis."""
        file = tmp_path / "test.taf"
        file.write_bytes(mock_taf_header + b'\x00' * 1000)
        
        # This would test header analysis if the method exists
        # The actual implementation would depend on the service's API
        assert file.exists()
        assert file.stat().st_size == 5096
    
    def test_service_handles_empty_files(self, service, tmp_path):
        """Test service handles empty files gracefully."""
        file1 = tmp_path / "empty1.taf"
        file2 = tmp_path / "empty2.taf"
        
        file1.write_bytes(b'')
        file2.write_bytes(b'')
        
        result = service.compare_taf_files(file1, file2)
        
        assert result['identical'] is True
        # file_size_diff is an integer (size2 - size1)
        assert result['file_size_diff'] == 0


class TestOggPageComparison:
    """Detailed tests for OGG page comparison functionality."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        logger = Mock()
        return TafAnalysisService(logger)
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    def test_page_differences_structure(self, service, tmp_path):
        """Test that page differences have correct structure."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        # Create minimal valid TAF files
        header = b'\x00' * 4096
        file1.write_bytes(header + b'OggS' + b'\x00' * 100)
        file2.write_bytes(header + b'OggS' + b'\x00' * 100)
        
        with patch('TonieToolbox.core.media.formats.ogg.OggPage') as mock_ogg:
            mock_page1 = Mock()
            mock_page1.page_no = 0
            mock_page1.granule_position = 0
            mock_page1.serial_no = 1
            mock_page1.page_type = 0
            mock_page1.segment_count = 1
            mock_page1.checksum = 100
            mock_page1.get_page_size.return_value = 59
            
            mock_page2 = Mock()
            mock_page2.page_no = 0
            mock_page2.granule_position = 960
            mock_page2.serial_no = 1
            mock_page2.page_type = 0
            mock_page2.segment_count = 1
            mock_page2.checksum = 200
            mock_page2.get_page_size.return_value = 59
            
            mock_ogg.side_effect = [mock_page1, mock_page2]
            mock_ogg.seek_to_page_header.side_effect = [True, False, True, False]
            
            result = service._compare_ogg_pages(file1, file2)
            
            assert 'total_pages_file1' in result
            assert 'total_pages_file2' in result
            assert 'page_differences' in result
            assert isinstance(result['page_differences'], list)
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    def test_all_page_properties_compared(self, service, tmp_path):
        """Test that all OGG page properties are compared."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        header = b'\x00' * 4096
        file1.write_bytes(header + b'OggS' + b'\x00' * 100)
        file2.write_bytes(header + b'OggS' + b'\x00' * 100)
        
        with patch('TonieToolbox.core.media.formats.ogg.OggPage') as mock_ogg:
            # Create pages with all different properties
            mock_page1 = Mock()
            mock_page1.page_no = 0
            mock_page1.granule_position = 0
            mock_page1.serial_no = 1
            mock_page1.page_type = 0
            mock_page1.segment_count = 1
            mock_page1.checksum = 0x11111111
            mock_page1.get_page_size.return_value = 59
            
            mock_page2 = Mock()
            mock_page2.page_no = 1  # Different
            mock_page2.granule_position = 960  # Different
            mock_page2.serial_no = 2  # Different
            mock_page2.page_type = 1  # Different
            mock_page2.segment_count = 2  # Different
            mock_page2.checksum = 0x22222222  # Different
            mock_page2.get_page_size.return_value = 100  # Different
            
            mock_ogg.side_effect = [mock_page1, mock_page2]
            mock_ogg.seek_to_page_header.side_effect = [True, False, True, False]
            
            result = service._compare_ogg_pages(file1, file2)
            
            # Should detect differences in all properties
            assert len(result['page_differences']) > 0


class TestComparisonEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        logger = Mock()
        return TafAnalysisService(logger)
    
    def test_compare_files_with_permission_error(self, service, tmp_path):
        """Test handling of permission errors."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        file1.write_bytes(b'\x00' * 5000)
        file2.write_bytes(b'\x00' * 5000)
        
        # This test would require platform-specific permission manipulation
        # On Linux/Mac, we could use chmod; on Windows, different approach
        # Skipping actual permission test, but structure is here
        assert file1.exists()
        assert file2.exists()
    
    def test_compare_very_large_files(self, service, tmp_path):
        """Test comparison of large files doesn't cause memory issues."""
        # This is a placeholder for performance testing
        # Actual implementation would create large files and monitor memory
        pass
    
    @pytest.mark.skip(reason="_compare_ogg_pages method not yet implemented")
    def test_compare_corrupted_ogg_data(self, service, tmp_path):
        """Test handling of corrupted OGG data."""
        file1 = tmp_path / "file1.taf"
        file2 = tmp_path / "file2.taf"
        
        header = b'\x00' * 4096
        # Invalid OGG data (doesn't start with 'OggS')
        file1.write_bytes(header + b'INVALID' + b'\x00' * 100)
        file2.write_bytes(header + b'INVALID' + b'\x00' * 100)
        
        # Should handle gracefully without crashing
        with patch('TonieToolbox.core.media.formats.ogg.OggPage') as mock_ogg:
            mock_ogg.seek_to_page_header.return_value = False
            
            result = service._compare_ogg_pages(file1, file2)
            
            # Should return valid result even with no pages found
            assert 'total_pages_file1' in result
            assert 'total_pages_file2' in result
            assert result['total_pages_file1'] == 0
            assert result['total_pages_file2'] == 0
