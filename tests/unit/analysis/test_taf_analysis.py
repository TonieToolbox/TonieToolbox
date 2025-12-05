"""
Unit tests for TAF file analysis functionality.

These tests verify the core TAF file parsing, validation, and information extraction
capabilities that are fundamental to TonieToolbox operation.
"""

import os
import struct
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

# Import the modules we're testing
try:
    from TonieToolbox.core.analysis.header import get_header_info
    from TonieToolbox.core.analysis.validation import check_tonie_file
    from TonieToolbox.core.analysis.extraction import split_to_opus_files
    from TonieToolbox.core.file.taf import tonie_header_pb2
except ImportError:
    # Fallback for direct imports
    import sys
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from TonieToolbox.core.analysis.header import get_header_info
    from TonieToolbox.core.analysis.validation import check_tonie_file  
    from TonieToolbox.core.analysis.extraction import split_to_opus_files
    from TonieToolbox.core.file.taf import tonie_header_pb2


class TestTAFHeaderAnalysis:
    """Test TAF file header parsing and validation."""
    
    def test_header_info_with_valid_taf(self, valid_taf_file):
        """Test header information extraction from valid TAF file."""
        with open(valid_taf_file, 'rb') as f:
            try:
                header_size, tonie_header, file_size, audio_size, sha1sum, \
                opus_head_found, opus_version, channel_count, sample_rate, \
                bitstream_serial_no, opus_comments = get_header_info(f)
                
                # Verify basic header properties
                assert header_size > 0, "Header size should be positive"
                assert file_size > header_size, "File size should be larger than header"
                assert audio_size > 0, "Audio size should be positive"
                
                # Verify Opus properties
                assert opus_head_found is True, "Opus header should be found"
                assert channel_count in [2], f"Channel count should be 2, got {channel_count}"
                assert sample_rate == 48000, f"Sample rate should be 48000 Hz, got {sample_rate}"
                assert bitstream_serial_no is not None, "Bitstream serial should exist"
                
                # Verify protocol buffer header
                assert tonie_header is not None, "Tonie header should be parsed"
                assert hasattr(tonie_header, 'dataLength'), "Header should have dataLength field"
                assert tonie_header.dataLength == audio_size, "Header dataLength should match audio size"
                
            except Exception as e:
                pytest.fail(f"Failed to parse valid TAF file: {e}")
    
    def test_header_info_with_invalid_file(self, temp_dir):
        """Test header parsing with invalid/corrupted file."""
        invalid_file = temp_dir / "invalid.taf"
        
        # Create a file with invalid header
        with open(invalid_file, 'wb') as f:
            f.write(b"INVALID_HEADER_DATA" * 100)
        
        with open(invalid_file, 'rb') as f:
            try:
                result = get_header_info(f)
                # If it doesn't raise an exception with invalid data, that's unexpected
                pytest.fail("Expected exception for invalid TAF file")
            except Exception as e:
                # Expected for invalid files - should be handled gracefully
                error_msg = str(e).lower()
                assert any(word in error_msg for word in ["error", "parsing", "invalid", "corrupt", "decode"]), \
                    f"Should show meaningful error for invalid file, got: {e}"
    
    def test_header_size_validation(self, valid_taf_file):
        """Test that header size is read and validated correctly."""
        with open(valid_taf_file, 'rb') as f:
            # Read the first 4 bytes (header size)
            header_size_bytes = f.read(4)
            header_size = struct.unpack(">L", header_size_bytes)[0]
            
            # Verify it's the expected Tonie header size (4096 bytes minus the 4-byte size field)
            expected_header_size = 4096 - 4
            assert header_size == expected_header_size, \
                f"Header size should be {expected_header_size}, got {header_size}"


class TestTAFValidation:
    """Test TAF file validation functionality."""
    
    def test_check_valid_taf_file(self, valid_taf_file):
        """Test validation of a known good TAF file."""
        result = check_tonie_file(str(valid_taf_file))
        
        # Should not raise exception and return validation info
        assert result is not None, "Validation should return result"
        # The result format may vary, but should indicate success
        assert "error" not in str(result).lower() or "Error" not in str(result)
    
    def test_check_nonexistent_file(self):
        """Test validation with non-existent file."""
        result = check_tonie_file("/nonexistent/file.taf")
        # Should return False for non-existent files instead of raising exception
        assert result is False, "Should return False for non-existent file"
    
    def test_check_invalid_file_format(self, temp_dir):
        """Test validation with invalid file format."""
        invalid_file = temp_dir / "not_a_taf.txt"
        with open(invalid_file, 'w') as f:
            f.write("This is not a TAF file")
        
        try:
            result = check_tonie_file(str(invalid_file))
            # Should handle gracefully or indicate validation failure
            if result is not None:
                assert "invalid" in str(result).lower() or "error" in str(result).lower()
        except Exception as e:
            # Expected for invalid files
            assert any(word in str(e).lower() for word in ["invalid", "corrupt", "format"])


class TestTAFExtraction:
    """Test TAF file extraction and splitting functionality."""
    
    @pytest.mark.slow
    def test_split_to_opus_files_basic(self, valid_taf_file, temp_dir):
        """Test basic TAF splitting to Opus files."""
        output_dir = temp_dir / "opus_output"
        output_dir.mkdir()
        
        try:
            split_to_opus_files(str(valid_taf_file), str(output_dir))
            
            # Verify output files were created
            opus_files = list(output_dir.glob("*.opus"))
            assert len(opus_files) > 0, "Should create at least one Opus file"
            
            # Verify files have content
            for opus_file in opus_files:
                assert opus_file.stat().st_size > 0, f"Opus file {opus_file} should not be empty"
                
        except Exception as e:
            pytest.fail(f"TAF splitting failed: {e}")
    
    def test_split_invalid_file(self, temp_dir):
        """Test splitting with invalid TAF file."""
        invalid_file = temp_dir / "invalid.taf"
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        # Create invalid TAF file
        with open(invalid_file, 'wb') as f:
            f.write(b"INVALID" * 1000)
        
        with pytest.raises(Exception):
            split_to_opus_files(str(invalid_file), str(output_dir))
    
    def test_split_without_output_directory(self, valid_taf_file):
        """Test splitting without specifying output directory."""
        try:
            # Should use default output location
            split_to_opus_files(str(valid_taf_file))
            # If successful, verify default location has files
            # (Implementation dependent - may need adjustment)
        except Exception as e:
            # Some implementations may require output directory
            assert "output" in str(e).lower() or "directory" in str(e).lower()


class TestProtocolBufferHandling:
    """Test Protocol Buffer header parsing."""
    
    def test_tonie_header_creation(self):
        """Test creating and parsing Tonie header protocol buffer."""
        # Create a test header
        header = tonie_header_pb2.TonieHeader()
        header.dataLength = 12345
        header.timestamp = 1234567890
        header.chapterPages.extend([0, 100, 200])
        
        # Serialize and deserialize
        serialized = header.SerializeToString()
        
        new_header = tonie_header_pb2.TonieHeader()
        new_header.ParseFromString(serialized)
        
        # Verify fields
        assert new_header.dataLength == 12345
        assert new_header.timestamp == 1234567890
        assert list(new_header.chapterPages) == [0, 100, 200]
    
    def test_empty_protocol_buffer(self):
        """Test handling empty protocol buffer."""
        header = tonie_header_pb2.TonieHeader()
        
        # Should have default values
        assert header.dataLength == 0
        assert header.timestamp == 0
        assert len(header.chapterPages) == 0


# Test data validation helpers
class TestFileValidation:
    """Test file validation utilities."""
    
    def test_valid_test_files_exist(self, sample_audio_files):
        """Verify our test data files exist and are readable."""
        for file_type, file_path in sample_audio_files.items():
            assert file_path.exists(), f"Test file {file_type} should exist at {file_path}"
            assert file_path.is_file(), f"Test path {file_path} should be a file"
            assert file_path.stat().st_size > 0, f"Test file {file_path} should not be empty"
    
    def test_taf_file_has_correct_structure(self, valid_taf_file):
        """Test that our sample TAF file has expected structure."""
        with open(valid_taf_file, 'rb') as f:
            # Read header size
            header_size_bytes = f.read(4)
            assert len(header_size_bytes) == 4, "Should be able to read 4-byte header size"
            
            header_size = struct.unpack(">L", header_size_bytes)[0]
            assert header_size > 0, "Header size should be positive"
            assert header_size < 10000, "Header size should be reasonable"  # Sanity check
            
            # Read header data
            header_data = f.read(header_size)
            assert len(header_data) == header_size, "Should be able to read full header"
            
            # Verify we can parse as protocol buffer
            try:
                tonie_header = tonie_header_pb2.TonieHeader()
                tonie_header.ParseFromString(header_data)
                assert tonie_header.dataLength > 0, "Header should have positive data length"
            except Exception as e:
                pytest.fail(f"Failed to parse TAF header as protocol buffer: {e}")


if __name__ == "__main__":
    pytest.main([__file__])