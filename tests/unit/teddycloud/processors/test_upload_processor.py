#!/usr/bin/python3
"""
Unit tests for TeddyCloud Upload Processor.

Tests the upload processor functionality including:
- File upload processing
- Custom JSON updates during upload
- Artwork file discovery
- Version flag handling
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from argparse import Namespace

from TonieToolbox.core.teddycloud.processors.upload_processor import (
    TeddyCloudUploadProcessor,
)
from TonieToolbox.core.teddycloud.domain.entities import UploadResult, SpecialFolder
from TonieToolbox.core.teddycloud.infrastructure.http_repository import HttpTeddyCloudRepository


class TestTeddyCloudUploadProcessor:
    """Test suite for TeddyCloudUploadProcessor."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock()
    
    @pytest.fixture
    def dependencies(self):
        """Create dependencies dict."""
        return {}
    
    @pytest.fixture
    def processor(self, mock_logger, dependencies):
        """Create processor instance."""
        return TeddyCloudUploadProcessor(mock_logger, dependencies)
    
    @pytest.fixture
    def mock_args(self):
        """Create mock arguments."""
        return Namespace(
            input_filename="test.taf",
            path=None,
            include_artwork=False,
            create_custom_json=False,
            version_2=False,
            output=None,
            special_folder=None
        )
    
    @pytest.fixture
    def successful_upload_result(self):
        """Create successful upload result."""
        return UploadResult(
            success=True,
            file_path="/path/to/file.taf",
            destination_path="/content/file.taf"
        )
    
    def test_processor_initialization(self, processor, mock_logger):
        """Test processor initializes correctly."""
        assert processor.logger == mock_logger
        assert processor.service is None
        assert processor.coordinator is None
    
    def test_find_artwork_files_single_match(self, processor, tmp_path):
        """Test finding artwork files for a TAF file."""
        # Create test files
        taf_file = tmp_path / "audio.taf"
        jpg_file = tmp_path / "audio.jpg"
        
        taf_file.write_bytes(b'\x00' * 100)
        jpg_file.write_bytes(b'\x00' * 100)
        
        artwork_files = processor._find_artwork_files(str(taf_file))
        
        assert len(artwork_files) == 1
        assert str(jpg_file) in artwork_files
    
    def test_find_artwork_files_multiple_formats(self, processor, tmp_path):
        """Test finding multiple artwork file formats."""
        taf_file = tmp_path / "audio.taf"
        jpg_file = tmp_path / "audio.jpg"
        png_file = tmp_path / "audio.png"
        webp_file = tmp_path / "audio.webp"
        
        taf_file.write_bytes(b'\x00' * 100)
        jpg_file.write_bytes(b'\x00' * 100)
        png_file.write_bytes(b'\x00' * 100)
        webp_file.write_bytes(b'\x00' * 100)
        
        artwork_files = processor._find_artwork_files(str(taf_file))
        
        # Should find all matching formats
        assert len(artwork_files) >= 1
    
    def test_find_artwork_files_no_match(self, processor, tmp_path):
        """Test when no artwork files exist."""
        taf_file = tmp_path / "audio.taf"
        taf_file.write_bytes(b'\x00' * 100)
        
        artwork_files = processor._find_artwork_files(str(taf_file))
        
        assert len(artwork_files) == 0
    
    def test_find_artwork_files_different_name(self, processor, tmp_path):
        """Test that artwork with different name is not found."""
        taf_file = tmp_path / "audio.taf"
        jpg_file = tmp_path / "different.jpg"
        
        taf_file.write_bytes(b'\x00' * 100)
        jpg_file.write_bytes(b'\x00' * 100)
        
        artwork_files = processor._find_artwork_files(str(taf_file))
        
        assert len(artwork_files) == 0
    
    def test_find_artwork_files_handles_errors(self, processor):
        """Test artwork file discovery handles errors gracefully."""
        # Non-existent directory
        artwork_files = processor._find_artwork_files("/nonexistent/path/file.taf")
        
        # Should return empty list, not crash
        assert artwork_files == []
    
    @patch('TonieToolbox.core.teddycloud.processors.upload_processor.TeddyCloudUploadCoordinator')
    def test_upload_without_artwork(self, mock_coordinator_class, processor, mock_args, successful_upload_result):
        """Test upload without artwork files."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = successful_upload_result
        processor.coordinator = Mock()
        
        mock_args.include_artwork = False
        file_path = "/path/to/file.taf"
        
        # Execute
        result = processor._upload_single_file(file_path, mock_args)
        
        # Verify
        assert result.success is True
        processor.service.upload_file.assert_called_once()
    
    @patch('TonieToolbox.core.teddycloud.processors.upload_processor.Path')
    def test_upload_with_artwork_enabled(self, mock_path, processor, mock_args, successful_upload_result):
        """Test upload with artwork enabled."""
        # Setup
        processor.service = Mock()
        processor.coordinator = Mock()
        processor.coordinator.upload_with_artwork.return_value = (
            successful_upload_result,
            [successful_upload_result]
        )
        
        mock_args.include_artwork = True
        file_path = "/path/to/file.taf"
        
        # Mock artwork file discovery
        with patch.object(processor, '_find_artwork_files', return_value=["/path/to/file.jpg"]):
            result = processor._upload_single_file(file_path, mock_args)
        
        # Verify coordinator was used
        processor.coordinator.upload_with_artwork.assert_called_once()
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_upload_with_create_custom_json_v1(self, mock_fetch_v1, processor, mock_args, successful_upload_result):
        """Test upload with custom JSON creation (v1)."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = successful_upload_result
        processor.service.repository = Mock(spec=HttpTeddyCloudRepository)
        processor.coordinator = Mock()
        
        mock_args.create_custom_json = True
        mock_args.version_2 = False
        mock_fetch_v1.return_value = True
        
        file_path = "/path/to/file.taf"
        
        # Execute
        with patch.object(processor, '_update_custom_json_after_upload') as mock_update:
            result = processor._upload_single_file(file_path, mock_args)
        
        # Verify
        assert result.success is True
        mock_update.assert_called_once()
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v2')
    def test_upload_with_create_custom_json_v2(self, mock_fetch_v2, processor, mock_args, successful_upload_result):
        """Test upload with custom JSON creation (v2)."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = successful_upload_result
        processor.service.repository = Mock(spec=HttpTeddyCloudRepository)
        processor.coordinator = Mock()
        
        mock_args.create_custom_json = True
        mock_args.version_2 = True
        mock_fetch_v2.return_value = True
        
        file_path = "/path/to/file.taf"
        
        # Execute
        with patch.object(processor, '_update_custom_json_after_upload') as mock_update:
            result = processor._upload_single_file(file_path, mock_args)
        
        # Verify
        assert result.success is True
        mock_update.assert_called_once()
    
    def test_custom_json_not_called_when_disabled(self, processor, mock_args, successful_upload_result):
        """Test that JSON update is not called when disabled."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = successful_upload_result
        processor.coordinator = Mock()
        
        mock_args.create_custom_json = False
        file_path = "/path/to/file.taf"
        
        # Execute
        with patch.object(processor, '_update_custom_json_after_upload') as mock_update:
            result = processor._upload_single_file(file_path, mock_args)
        
        # Verify JSON update was not called
        mock_update.assert_not_called()
    
    def test_custom_json_not_called_on_upload_failure(self, processor, mock_args):
        """Test that JSON update is skipped when upload fails."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = UploadResult(
            success=False,
            file_path="/path/to/file.taf",
            error="Upload failed"
        )
        processor.coordinator = Mock()
        
        mock_args.create_custom_json = True
        file_path = "/path/to/file.taf"
        
        # Execute
        with patch.object(processor, '_update_custom_json_after_upload') as mock_update:
            result = processor._upload_single_file(file_path, mock_args)
        
        # Verify
        assert result.success is False
        mock_update.assert_not_called()
    
    @patch('TonieToolbox.core.tonies_data.fetch_and_update_tonies_json_v1')
    def test_update_custom_json_after_upload_v1(self, mock_fetch_v1, processor):
        """Test _update_custom_json_after_upload with v1 format."""
        # Setup
        processor.service = Mock()
        processor.service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_fetch_v1.return_value = True
        
        upload_result = Mock()
        taf_file = "/path/to/file.taf"
        input_files = ["/input/track.mp3"]
        output_dir = "/output"
        use_version_2 = False
        
        # Execute
        processor._update_custom_json_after_upload(
            upload_result,
            taf_file,
            input_files,
            output_dir,
            use_version_2
        )
        
        # Verify
        mock_fetch_v1.assert_called_once()
        call_kwargs = mock_fetch_v1.call_args[1]
        assert call_kwargs['taf_file'] == taf_file
        assert call_kwargs['input_files'] == input_files
        assert call_kwargs['output_dir'] == output_dir
        assert call_kwargs['artwork_url'] is None
    
    @patch('TonieToolbox.core.tonies_data.fetch_and_update_tonies_json_v2')
    def test_update_custom_json_after_upload_v2(self, mock_fetch_v2, processor):
        """Test _update_custom_json_after_upload with v2 format."""
        # Setup
        processor.service = Mock()
        processor.service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_fetch_v2.return_value = True
        
        upload_result = Mock()
        taf_file = "/path/to/file.taf"
        input_files = ["/input/track.mp3"]
        output_dir = "/output"
        use_version_2 = True
        
        # Execute
        processor._update_custom_json_after_upload(
            upload_result,
            taf_file,
            input_files,
            output_dir,
            use_version_2
        )
        
        # Verify
        mock_fetch_v2.assert_called_once()
        call_kwargs = mock_fetch_v2.call_args[1]
        assert call_kwargs['taf_file'] == taf_file
        assert call_kwargs['input_files'] == input_files
        assert call_kwargs['output_dir'] == output_dir
    
    def test_update_custom_json_without_repository(self, processor):
        """Test JSON update handles missing repository gracefully."""
        # Setup - service without repository
        processor.service = Mock()
        processor.service.repository = None
        
        upload_result = Mock()
        taf_file = "/path/to/file.taf"
        
        # Execute - should not raise exception
        processor._update_custom_json_after_upload(
            upload_result,
            taf_file,
            None,
            None,
            False
        )
        
        # Verify warning was logged
        processor.logger.warning.assert_called()
    
    def test_args_parameter_extraction(self, processor, mock_args):
        """Test that parameters are correctly extracted from args."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/test.taf"
        )
        processor.coordinator = Mock()
        
        mock_args.create_custom_json = True
        mock_args.version_2 = True
        mock_args.input_filename = ["/input/track1.mp3", "/input/track2.mp3"]
        mock_args.output = "/custom/output"
        
        file_path = "/path/to/file.taf"
        
        # Execute
        with patch.object(processor, '_update_custom_json_after_upload') as mock_update:
            processor._upload_single_file(file_path, mock_args)
        
        # Verify parameters were extracted and passed
        assert mock_update.called
        call_args = mock_update.call_args[0]
        assert call_args[2] == ["/input/track1.mp3", "/input/track2.mp3"]  # input_files
        assert call_args[3] == "/custom/output"  # output_dir
        assert call_args[4] is True  # use_version_2
    
    def test_single_input_file_converted_to_list(self, processor, mock_args):
        """Test that single input file is converted to list."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/test.taf"
        )
        processor.coordinator = Mock()
        
        mock_args.create_custom_json = True
        mock_args.input_filename = "/input/single.mp3"  # Not a list
        
        file_path = "/path/to/file.taf"
        
        # Execute
        with patch.object(processor, '_update_custom_json_after_upload') as mock_update:
            processor._upload_single_file(file_path, mock_args)
        
        # Verify single file was converted to list
        call_args = mock_update.call_args[0]
        input_files = call_args[2]
        assert isinstance(input_files, list)
        assert input_files == ["/input/single.mp3"]
    
    def test_upload_handles_exceptions(self, processor, mock_args):
        """Test that upload exceptions are handled gracefully."""
        # Setup
        processor.service = Mock()
        processor.service.upload_file.side_effect = Exception("Network error")
        processor.coordinator = Mock()
        
        file_path = "/path/to/file.taf"
        
        # Execute
        result = processor._upload_single_file(file_path, mock_args)
        
        # Verify error is captured in result
        assert result.success is False
        assert "Network error" in result.error


class TestUploadProcessorIntegration:
    """Integration tests for upload processor workflows."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        logger = Mock()
        return TeddyCloudUploadProcessor(logger, {})
    
    @patch('TonieToolbox.core.tonies_data.fetch_and_update_tonies_json_v1')
    def test_complete_upload_workflow_with_artwork_and_json(self, mock_fetch_v1, processor, tmp_path):
        """Test complete upload workflow with artwork and JSON."""
        # Create test files
        taf_file = tmp_path / "audio.taf"
        jpg_file = tmp_path / "audio.jpg"
        taf_file.write_bytes(b'\x00' * 100)
        jpg_file.write_bytes(b'\x00' * 100)
        
        # Setup
        processor.service = Mock()
        processor.coordinator = Mock()
        processor.coordinator.upload_with_artwork.return_value = (
            UploadResult(success=True, file_path=str(taf_file)),
            [UploadResult(success=True, file_path=str(jpg_file))]
        )
        processor.service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_fetch_v1.return_value = True
        
        # Create args
        args = Namespace(
            include_artwork=True,
            create_custom_json=True,
            version_2=False,
            input_filename=["/input/track.mp3"],
            output="/output",
            path=None,
            special_folder=None
        )
        
        # Execute
        result = processor._upload_single_file(str(taf_file), args)
        
        # Verify
        assert result.success is True
        processor.coordinator.upload_with_artwork.assert_called_once()


class TestUploadProcessorEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        logger = Mock()
        return TeddyCloudUploadProcessor(logger, {})
    
    def test_artwork_discovery_with_special_characters(self, processor, tmp_path):
        """Test artwork discovery with special characters in filename."""
        taf_file = tmp_path / "audio (special) [test].taf"
        jpg_file = tmp_path / "audio (special) [test].jpg"
        
        taf_file.write_bytes(b'\x00' * 100)
        jpg_file.write_bytes(b'\x00' * 100)
        
        artwork_files = processor._find_artwork_files(str(taf_file))
        
        assert len(artwork_files) >= 1
    
    def test_upload_with_missing_args_attributes(self, processor):
        """Test upload handles missing args attributes gracefully."""
        # Create args with minimal attributes
        args = Namespace()
        
        processor.service = Mock()
        processor.service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/test.taf"
        )
        processor.coordinator = Mock()
        
        # Should not crash even with missing attributes
        result = processor._upload_single_file("/path/to/file.taf", args)
        
        # Should complete successfully with defaults
        assert result.success is True
