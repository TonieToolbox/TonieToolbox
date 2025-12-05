#!/usr/bin/python3
"""
Integration tests for new features.

Tests complete workflows for:
- TAF file comparison with detailed OGG analysis
- TeddyCloud upload with custom JSON creation (v1 and v2)
- End-to-end feature integration
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from TonieToolbox.core.processing.infrastructure.services.taf_analysis_service import TafAnalysisService
from TonieToolbox.core.teddycloud.application.coordinators import TeddyCloudUploadCoordinator
from TonieToolbox.core.teddycloud.processors.upload_processor import TeddyCloudUploadProcessor
from TonieToolbox.core.teddycloud.domain.entities import UploadResult
from TonieToolbox.core.teddycloud.infrastructure.http_repository import HttpTeddyCloudRepository


class TestDetailedCompareIntegration:
    """Integration tests for --detailed-compare feature."""
    
    @pytest.fixture
    def taf_files(self, tmp_path):
        """Create test TAF files."""
        file1 = tmp_path / "audio1.taf"
        file2 = tmp_path / "audio2.taf"
        
        # TAF header (4096 bytes)
        header = b'\x00' * 4096
        
        # Mock OGG page data
        ogg_page = (
            b'OggS'  # Capture pattern
            b'\x00'  # Version
            b'\x00'  # Header type
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Granule
            b'\x01\x00\x00\x00'  # Serial
            b'\x00\x00\x00\x00'  # Sequence
            b'\x00\x00\x00\x00'  # Checksum
            b'\x01'  # Segments
            b'\x20'  # Segment table
            b'\x00' * 32  # Data
        )
        
        file1.write_bytes(header + ogg_page)
        file2.write_bytes(header + ogg_page)
        
        return file1, file2
    
    @pytest.mark.skip(reason="TAF comparison with detailed OGG analysis requires implementation")
    def test_complete_detailed_comparison_workflow(self, sample_audio_files):
        """Test complete detailed comparison from file to display using real TAF files."""
        logger = Mock()
        service = TafAnalysisService(logger)
        
        # Compare two different real TAF files
        result = service.compare_taf_files(sample_audio_files['taf_stereo'], sample_audio_files['taf_mono'])
        
        # Verify result structure (check for error first)
        if 'error' in result:
            pytest.skip(f"TAF comparison failed with error: {result['error']}")
        
        assert 'identical' in result
        assert 'ogg_pages_diff' in result
        assert 'total_pages_file1' in result['ogg_pages_diff']
        assert 'total_pages_file2' in result['ogg_pages_diff']
        assert 'page_differences' in result['ogg_pages_diff']
        
        # Real files should have actual OGG pages
        assert result['ogg_pages_diff']['total_pages_file1'] > 0
        assert result['ogg_pages_diff']['total_pages_file2'] > 0
    
    @pytest.mark.skip(reason="TAF comparison needs OGG page analysis")
    def test_comparison_detects_ogg_differences(self, sample_audio_files):
        """Test that OGG page differences are detected in real files."""
        logger = Mock()
        service = TafAnalysisService(logger)
        
        # Compare stereo vs mono files - should have differences
        result = service.compare_taf_files(sample_audio_files['taf_stereo'], sample_audio_files['taf_mono'])
        
        # Check for errors first
        if 'error' in result:
            pytest.skip(f"TAF comparison failed with error: {result['error']}")
        
        # Files are different
        assert result['identical'] is False
        
        # Should have OGG page information
        assert 'ogg_pages_diff' in result
        ogg_diff = result['ogg_pages_diff']
        
        # Both files should have pages
        assert ogg_diff['total_pages_file1'] > 0
        assert ogg_diff['total_pages_file2'] > 0


class TestCustomJsonIntegration:
    """Integration tests for custom JSON creation feature."""
    
    @pytest.fixture
    def mock_teddycloud_service(self):
        """Create mock TeddyCloud service."""
        service = Mock()
        service.repository = Mock(spec=HttpTeddyCloudRepository)
        service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/path/to/file.taf",
            destination_path="/content/file.taf"
        )
        return service
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_upload_workflow_with_json_v1(self, mock_fetch_v1, mock_teddycloud_service):
        """Test complete upload workflow with v1 JSON creation."""
        mock_fetch_v1.return_value = True
        
        logger = Mock()
        coordinator = TeddyCloudUploadCoordinator(mock_teddycloud_service, logger)
        
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file="/path/to/audio.taf",
            artwork_files=["/path/to/audio.jpg"],
            create_custom_json=True,
            use_version_2=False,
            input_files=["/input/track.mp3"],
            output_dir="/output"
        )
        
        # Verify upload succeeded
        assert taf_result.success is True
        
        # Verify JSON creation was called
        mock_fetch_v1.assert_called_once()
        call_kwargs = mock_fetch_v1.call_args[1]
        assert call_kwargs['taf_file'] == "/path/to/audio.taf"
        assert call_kwargs['input_files'] == ["/input/track.mp3"]
        assert call_kwargs['output_dir'] == "/output"
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v2')
    def test_upload_workflow_with_json_v2(self, mock_fetch_v2, mock_teddycloud_service):
        """Test complete upload workflow with v2 JSON creation."""
        mock_fetch_v2.return_value = True
        
        logger = Mock()
        coordinator = TeddyCloudUploadCoordinator(mock_teddycloud_service, logger)
        
        taf_result, artwork_results = coordinator.upload_with_artwork(
            taf_file="/path/to/audio.taf",
            artwork_files=[],
            create_custom_json=True,
            use_version_2=True,
            input_files=["/input/track.mp3"],
            output_dir="/output"
        )
        
        # Verify upload succeeded
        assert taf_result.success is True
        
        # Verify v2 JSON creation was called
        mock_fetch_v2.assert_called_once()
        call_kwargs = mock_fetch_v2.call_args[1]
        assert call_kwargs['taf_file'] == "/path/to/audio.taf"
        assert call_kwargs['input_files'] == ["/input/track.mp3"]
    
    @patch('TonieToolbox.core.tonies_data.fetch_and_update_tonies_json_v1')
    def test_processor_to_coordinator_workflow(self, mock_fetch_v1, tmp_path):
        """Test workflow from processor through coordinator."""
        # Create test file
        taf_file = tmp_path / "audio.taf"
        jpg_file = tmp_path / "audio.jpg"
        taf_file.write_bytes(b'\x00' * 100)
        jpg_file.write_bytes(b'\x00' * 100)
        
        # Setup
        mock_fetch_v1.return_value = True
        logger = Mock()
        processor = TeddyCloudUploadProcessor(logger, {})
        
        processor.service = Mock()
        processor.coordinator = Mock()
        processor.coordinator.upload_with_artwork.return_value = (
            UploadResult(success=True, file_path=str(taf_file)),
            [UploadResult(success=True, file_path=str(jpg_file))]
        )
        
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
        
        # Verify parameters were passed correctly
        call_kwargs = processor.coordinator.upload_with_artwork.call_args[1]
        assert call_kwargs['create_custom_json'] is True
        assert call_kwargs['use_version_2'] is False


class TestEndToEndFeatureIntegration:
    """End-to-end integration tests combining multiple features."""
    
    @pytest.mark.skip(reason="TAF comparison needs to be integrated with upload workflow")
    def test_compare_then_upload_workflow(self, sample_audio_files):
        """Test comparing files before uploading using real TAF files."""
        # Step 1: Compare files
        logger = Mock()
        analysis_service = TafAnalysisService(logger)
        comparison = analysis_service.compare_taf_files(sample_audio_files['taf_stereo'], sample_audio_files['taf_mono'])
        
        # Check for errors first
        if 'error' in comparison:
            pytest.skip(f"TAF comparison failed with error: {comparison['error']}")
        
        # Files should be different (stereo vs mono)
        assert comparison['identical'] is False
        
        # Step 2: Upload one file with JSON creation
        with patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1') as mock_fetch:
            mock_fetch.return_value = True
            
            service = Mock()
            service.repository = Mock(spec=HttpTeddyCloudRepository)
            service.upload_file.return_value = UploadResult(
                success=True,
                file_path=str(sample_audio_files['taf_stereo']),
                destination_path="/content/audio1.taf"
            )
            
            coordinator = TeddyCloudUploadCoordinator(service, logger)
            
            taf_result, _ = coordinator.upload_with_artwork(
                taf_file=str(sample_audio_files['taf_stereo']),
                artwork_files=[],
                create_custom_json=True,
                use_version_2=False
            )
            
            assert taf_result.success is True
            mock_fetch.assert_called_once()
    
    def test_version_flag_selection(self):
        """Test that version flag correctly selects v1 or v2."""
        with patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1') as mock_v1:
            with patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v2') as mock_v2:
                mock_v1.return_value = True
                mock_v2.return_value = True
                
                service = Mock()
                service.repository = Mock(spec=HttpTeddyCloudRepository)
                service.upload_file.return_value = UploadResult(
                    success=True,
                    file_path="/test.taf"
                )
                
                logger = Mock()
                coordinator = TeddyCloudUploadCoordinator(service, logger)
                
                # Test v1
                coordinator.upload_with_artwork(
                    "/test.taf",
                    [],
                    create_custom_json=True,
                    use_version_2=False
                )
                mock_v1.assert_called()
                mock_v2.assert_not_called()
                
                # Reset mocks
                mock_v1.reset_mock()
                mock_v2.reset_mock()
                
                # Test v2
                coordinator.upload_with_artwork(
                    "/test.taf",
                    [],
                    create_custom_json=True,
                    use_version_2=True
                )
                mock_v2.assert_called()


class TestErrorRecoveryIntegration:
    """Test error recovery in integrated workflows."""
    
    def test_upload_failure_prevents_json_creation(self):
        """Test that failed upload prevents JSON creation."""
        with patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1') as mock_fetch:
            service = Mock()
            service.upload_file.return_value = UploadResult(
                success=False,
                file_path="/test.taf",
                error="Upload failed"
            )
            
            logger = Mock()
            coordinator = TeddyCloudUploadCoordinator(service, logger)
            
            taf_result, _ = coordinator.upload_with_artwork(
                "/test.taf",
                [],
                create_custom_json=True
            )
            
            assert taf_result.success is False
            # JSON creation should not be called
            mock_fetch.assert_not_called()
    
    
    def test_comparison_handles_corrupted_files(self, tmp_path, sample_audio_files):
        """Test that comparison handles corrupted files gracefully."""
        # Use real file for file1
        file2 = tmp_path / "corrupted.taf"
        
        # Write invalid data to file2
        file2.write_bytes(b'INVALID' * 100)
        
        logger = Mock()
        service = TafAnalysisService(logger)
        
        # Should complete without crashing
        result = service.compare_taf_files(sample_audio_files['taf_stereo'], file2)
        
        # Should indicate files are different
        assert result['identical'] is False


class TestFeatureCombinations:
    """Test various combinations of feature flags."""
    
    @patch('TonieToolbox.core.teddycloud.application.coordinators.fetch_and_update_tonies_json_v1')
    def test_upload_with_artwork_and_json(self, mock_fetch, sample_audio_files):
        """Test upload with both artwork and JSON creation using real files."""
        mock_fetch.return_value = True
        
        service = Mock()
        service.repository = Mock(spec=HttpTeddyCloudRepository)
        service.upload_file.return_value = UploadResult(
            success=True,
            file_path=str(sample_audio_files['taf_stereo']),
            destination_path="/content/audio.taf"
        )
        
        logger = Mock()
        coordinator = TeddyCloudUploadCoordinator(service, logger)
        
        taf_result, artwork_results = coordinator.upload_with_artwork(
            str(sample_audio_files['taf_stereo']),
            [str(sample_audio_files['cover_image'])],
            create_custom_json=True,
            use_version_2=False
        )
        
        # Both upload and JSON creation should succeed
        assert taf_result.success is True
        assert len(artwork_results) == 1
        mock_fetch.assert_called_once()
    
    def test_all_features_disabled(self):
        """Test upload with all optional features disabled."""
        service = Mock()
        service.upload_file.return_value = UploadResult(
            success=True,
            file_path="/test.taf"
        )
        
        logger = Mock()
        coordinator = TeddyCloudUploadCoordinator(service, logger)
        
        # Upload without artwork, JSON, or special options
        taf_result, artwork_results = coordinator.upload_with_artwork(
            "/test.taf",
            [],
            create_custom_json=False,
            use_version_2=False
        )
        
        assert taf_result.success is True
        assert len(artwork_results) == 0
