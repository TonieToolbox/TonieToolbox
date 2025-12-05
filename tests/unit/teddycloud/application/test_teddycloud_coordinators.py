#!/usr/bin/python3
"""
Unit tests for TeddyCloud Upload Coordinator.

Tests the TeddyCloudUploadCoordinator class, focusing on:
- File upload with artwork
- Custom JSON creation (v1 and v2 formats)
- Upload error handling
- Folder content uploads
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

from TonieToolbox.core.teddycloud.application.coordinators import (
    TeddyCloudUploadCoordinator,
    TeddyCloudTagCoordinator
)
from TonieToolbox.core.teddycloud.domain.entities import UploadResult, SpecialFolder
from TonieToolbox.core.teddycloud.infrastructure.http_repository import HttpTeddyCloudRepository


class TestTeddyCloudUploadCoordinator:
    """Test suite for TeddyCloudUploadCoordinator."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock TeddyCloud service."""
        service = Mock()
        # Create a mock that will pass isinstance check for HttpTeddyCloudRepository
        mock_repo = Mock(spec=HttpTeddyCloudRepository)
        service.repository = mock_repo
        return service
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()
    
    @pytest.fixture
    def coordinator(self, mock_service, mock_logger):
        """Create coordinator instance."""
        return TeddyCloudUploadCoordinator(mock_service, mock_logger)
    
    @pytest.fixture
    def successful_upload_result(self):
        """Create a successful upload result."""
        return UploadResult(
            success=True,
            file_path="/path/to/file.taf",
            destination_path="/content/file.taf"
        )
    
    @pytest.fixture
    def failed_upload_result(self):
        """Create a failed upload result."""
        return UploadResult(
            success=False,
            file_path="/path/to/file.taf",
            error="Upload failed"
        )
    
    def test_coordinator_initialization(self, coordinator, mock_service, mock_logger):
        """Test coordinator initializes correctly."""
        assert coordinator.teddycloud_service == mock_service
        assert coordinator.logger == mock_logger
        assert coordinator.event_bus is not None
    
    def test_upload_with_artwork_success(self, coordinator, mock_service, successful_upload_result):
        """Test successful upload with artwork."""
        # Setup
        taf_file = "/path/to/audio.taf"
        artwork_files = ["/path/to/audio.jpg"]
        
        mock_service.upload_file.return_value = successful_upload_result
        
        # Execute
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file, artwork_files
        )
        
        # Verify
        assert taf_result.success is True
        assert len(artwork_results) == 1
        assert mock_service.upload_file.call_count == 2  # TAF + 1 artwork
    
    def test_upload_with_artwork_taf_failure(self, coordinator, mock_service, failed_upload_result):
        """Test that artwork upload is skipped when TAF upload fails."""
        taf_file = "/path/to/audio.taf"
        artwork_files = ["/path/to/audio.jpg"]
        
        mock_service.upload_file.return_value = failed_upload_result
        
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file, artwork_files
        )
        
        assert taf_result.success is False
        assert len(artwork_results) == 0
        # Only TAF upload attempted, artwork skipped
        assert mock_service.upload_file.call_count == 1
    
    def test_upload_with_multiple_artwork_files(self, coordinator, mock_service, successful_upload_result):
        """Test upload with multiple artwork files."""
        taf_file = "/path/to/audio.taf"
        artwork_files = [
            "/path/to/audio.jpg",
            "/path/to/audio.png",
            "/path/to/audio.webp"
        ]
        
        mock_service.upload_file.return_value = successful_upload_result
        
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file, artwork_files
        )
        
        assert taf_result.success is True
        assert len(artwork_results) == 3
        # 1 TAF + 3 artwork = 4 uploads
        assert mock_service.upload_file.call_count == 4
    
    def test_upload_with_template_path(self, coordinator, mock_service, successful_upload_result):
        """Test upload with custom template path."""
        taf_file = "/path/to/audio.taf"
        artwork_files = ["/path/to/audio.jpg"]
        template_path = "/custom/path/audio"
        
        mock_service.upload_file.return_value = successful_upload_result
        
        coordinator.upload_with_artwork(taf_file, artwork_files, template_path)
        
        # Verify template path is used
        calls = mock_service.upload_file.call_args_list
        assert calls[0][0][1] == template_path  # TAF upload
    
    def test_upload_with_special_folder(self, coordinator, mock_service, successful_upload_result):
        """Test upload to special folder."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        special = SpecialFolder.LIBRARY
        
        mock_service.upload_file.return_value = successful_upload_result
        
        coordinator.upload_with_artwork(
            taf_file, artwork_files, special=special
        )
        
        # Verify special folder is passed
        calls = mock_service.upload_file.call_args_list
        assert calls[0][0][2] == special
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_upload_with_custom_json_v1(self, mock_fetch_v1, coordinator, mock_service, successful_upload_result):
        """Test upload with custom JSON creation (v1 format)."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        
        mock_service.upload_file.return_value = successful_upload_result
        mock_fetch_v1.return_value = True
        
        coordinator.upload_with_artwork(
            taf_file,
            artwork_files,
            create_custom_json=True,
            use_version_2=False
        )
        
        # Verify v1 function was called
        mock_fetch_v1.assert_called_once()
        call_kwargs = mock_fetch_v1.call_args[1]
        assert call_kwargs['taf_file'] == taf_file
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v2')
    def test_upload_with_custom_json_v2(self, mock_fetch_v2, coordinator, mock_service, successful_upload_result):
        """Test upload with custom JSON creation (v2 format)."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        
        mock_service.upload_file.return_value = successful_upload_result
        mock_service.repository = Mock(spec=HttpTeddyCloudRepository)  # Ensure repository exists with correct type
        mock_fetch_v2.return_value = True
        
        coordinator.upload_with_artwork(
            taf_file,
            artwork_files,
            create_custom_json=True,
            use_version_2=True
        )
        
        # Verify v2 function was called
        mock_fetch_v2.assert_called_once()
        call_kwargs = mock_fetch_v2.call_args[1]
        assert call_kwargs['taf_file'] == taf_file
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_custom_json_not_created_on_upload_failure(self, mock_fetch_v1, coordinator, mock_service, failed_upload_result):
        """Test that custom JSON is not created when upload fails."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        
        mock_service.upload_file.return_value = failed_upload_result
        
        coordinator.upload_with_artwork(
            taf_file,
            artwork_files,
            create_custom_json=True
        )
        
        # JSON creation should be skipped due to failed upload
        mock_fetch_v1.assert_not_called()
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_custom_json_with_input_files(self, mock_fetch_v1, coordinator, mock_service, successful_upload_result):
        """Test custom JSON creation includes input files."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        input_files = ["/input/track1.mp3", "/input/track2.mp3"]
        
        mock_service.upload_file.return_value = successful_upload_result
        mock_service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_fetch_v1.return_value = True
        
        coordinator.upload_with_artwork(
            taf_file,
            artwork_files,
            create_custom_json=True,
            input_files=input_files
        )
        
        call_kwargs = mock_fetch_v1.call_args[1]
        assert call_kwargs['input_files'] == input_files
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_custom_json_with_artwork_url(self, mock_fetch_v1, coordinator, mock_service, successful_upload_result):
        """Test custom JSON creation includes artwork URL."""
        taf_file = "/path/to/audio.taf"
        artwork_files = ["/path/to/audio.jpg"]
        
        # Create result with server_path for artwork
        taf_result = UploadResult(
            success=True,
            file_path=taf_file,
            destination_path="/content/audio.taf"
        )
        artwork_result = UploadResult(
            success=True,
            file_path=artwork_files[0],
            destination_path="/content/audio.jpg"
        )
        
        mock_service.upload_file.side_effect = [taf_result, artwork_result]
        mock_service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_fetch_v1.return_value = True
        
        coordinator.upload_with_artwork(
            taf_file,
            artwork_files,
            create_custom_json=True
        )
        
        call_kwargs = mock_fetch_v1.call_args[1]
        assert call_kwargs['artwork_url'] == "/content/audio.jpg"
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_custom_json_with_output_dir(self, mock_fetch_v1, coordinator, mock_service, successful_upload_result):
        """Test custom JSON creation with custom output directory."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        output_dir = "/custom/output"
        
        mock_service.upload_file.return_value = successful_upload_result
        mock_service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_fetch_v1.return_value = True
        
        coordinator.upload_with_artwork(
            taf_file,
            artwork_files,
            create_custom_json=True,
            output_dir=output_dir
        )
        
        call_kwargs = mock_fetch_v1.call_args[1]
        assert call_kwargs['output_dir'] == output_dir
    
    def test_update_custom_json_handles_errors(self, coordinator, mock_service):
        """Test _update_custom_json handles errors gracefully."""
        # Test without repository
        mock_service.repository = None
        
        # Should not raise exception
        coordinator._update_custom_json(
            taf_file="/path/to/file.taf",
            input_files=None,
            artwork_url=None,
            output_dir=None,
            use_version_2=False
        )
        
        # Logger should have warning about missing client
        coordinator.logger.warning.assert_called()
    
    def test_get_artwork_template_without_base(self, coordinator):
        """Test artwork template generation without base template."""
        artwork_file = "/path/to/audio.jpg"
        
        template = coordinator._get_artwork_template(None, artwork_file)
        
        assert template == "audio"
    
    def test_get_artwork_template_with_base(self, coordinator):
        """Test artwork template generation with base template."""
        base_template = "/custom/path/audio"
        artwork_file = "/path/to/cover.jpg"
        
        template = coordinator._get_artwork_template(base_template, artwork_file)
        
        assert "custom/path" in template
        assert "cover" in template
    
    def test_upload_exception_handling(self, coordinator, mock_service):
        """Test that exceptions during upload are handled gracefully."""
        taf_file = "/path/to/audio.taf"
        artwork_files = []
        
        mock_service.upload_file.side_effect = Exception("Network error")
        
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file, artwork_files
        )
        
        assert taf_result.success is False
        assert "Network error" in taf_result.error
        assert len(artwork_results) == 0


class TestTeddyCloudTagCoordinator:
    """Test suite for TeddyCloudTagCoordinator."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        service = Mock()
        return service
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return Mock()
    
    @pytest.fixture
    def coordinator(self, mock_service, mock_logger):
        """Create coordinator instance."""
        return TeddyCloudTagCoordinator(mock_service, mock_logger)
    
    def test_tag_coordinator_initialization(self, coordinator, mock_service, mock_logger):
        """Test tag coordinator initializes correctly."""
        assert coordinator.teddycloud_service == mock_service
        assert coordinator.logger == mock_logger


class TestUploadCoordinatorIntegration:
    """Integration tests for upload coordinator workflows."""
    
    @pytest.fixture
    def coordinator(self):
        """Create coordinator with mocked dependencies."""
        service = Mock()
        logger = Mock()
        return TeddyCloudUploadCoordinator(service, logger)
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v2')
    def test_complete_upload_workflow_with_json_v1(self, mock_v2, mock_v1, coordinator):
        """Test complete upload workflow with JSON v1 creation."""
        # Setup
        coordinator.teddycloud_service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/path/to/file.taf",
            destination_path="/content/file.taf"
        )
        coordinator.teddycloud_service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_v1.return_value = True
        
        # Execute
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file="/path/to/file.taf",
            artwork_files=["/path/to/cover.jpg"],
            create_custom_json=True,
            use_version_2=False,
            input_files=["/input/track.mp3"],
            output_dir="/output"
        )
        
        # Verify
        assert taf_result.success is True
        assert len(artwork_results) == 1
        mock_v1.assert_called_once()
        mock_v2.assert_not_called()
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v2')
    def test_complete_upload_workflow_with_json_v2(self, mock_v2, mock_v1, coordinator):
        """Test complete upload workflow with JSON v2 creation."""
        # Setup
        coordinator.teddycloud_service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/path/to/file.taf",
            destination_path="/content/file.taf"
        )
        coordinator.teddycloud_service.repository = Mock(spec=HttpTeddyCloudRepository)
        mock_v2.return_value = True
        
        # Execute
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file="/path/to/file.taf",
            artwork_files=["/path/to/cover.jpg"],
            create_custom_json=True,
            use_version_2=True,
            input_files=["/input/track.mp3"],
            output_dir="/output"
        )
        
        # Verify
        assert taf_result.success is True
        assert len(artwork_results) == 1
        mock_v2.assert_called_once()
        mock_v1.assert_not_called()
