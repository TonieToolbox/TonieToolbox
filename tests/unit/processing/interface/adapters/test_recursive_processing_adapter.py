#!/usr/bin/env python3
"""
Unit tests for RecursiveProcessingAdapter.

Tests cover both modes of operation:
- Combine mode: Combines all audio files in each folder into one TAF per folder
- Individual mode: Processes each audio file individually (--files-to-taf)

Tests include:
- Folder discovery with max_depth support
- Metadata extraction from audio files
- Template-based path resolution
- File combination logic
- Individual file processing
- Error handling and edge cases
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from TonieToolbox.core.processing.interface.adapters.files_to_taf_adapter import RecursiveProcessingAdapter


@pytest.fixture
def mock_processing_service():
    """Create mock processing service."""
    service = Mock()
    service.process_file = Mock(return_value=0)
    return service


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock()


@pytest.fixture
def mock_path_resolver():
    """Create mock path resolver."""
    resolver = Mock()
    resolver.resolve_output_path = Mock(return_value=Path("/output/result.taf"))
    resolver.resolve_metadata_from_input = Mock(return_value={'artist': 'Test Artist', 'album': 'Test Album'})
    return resolver


@pytest.fixture
def adapter(mock_processing_service, mock_logger, mock_path_resolver):
    """Create RecursiveProcessingAdapter instance with mocked dependencies."""
    adapter = RecursiveProcessingAdapter(mock_processing_service, mock_logger)
    adapter.path_resolver = mock_path_resolver
    adapter._update_progress = Mock()
    return adapter


class TestRecursiveAdapterInitialization:
    """Test RecursiveProcessingAdapter initialization."""
    
    def test_initialization_with_processing_service(self, mock_processing_service, mock_logger):
        """Test adapter initializes correctly with processing service."""
        adapter = RecursiveProcessingAdapter(mock_processing_service, mock_logger)
        
        assert adapter.processing_service == mock_processing_service
        assert adapter.logger == mock_logger
        assert adapter.path_resolver is not None
    
    def test_initialization_creates_path_resolver(self, mock_processing_service, mock_logger):
        """Test adapter creates OutputPathResolver during initialization."""
        adapter = RecursiveProcessingAdapter(mock_processing_service, mock_logger)
        
        assert hasattr(adapter, 'path_resolver')
        assert adapter.path_resolver is not None


class TestFolderDiscovery:
    """Test folder discovery with audio file grouping."""
    
    def test_discover_folders_with_audio(self, adapter, mock_audio_directory):
        """Test discovering folders containing audio files."""
        request = {'file_extensions': ['.mp3']}
        
        base_path = mock_audio_directory
        folders = adapter._discover_folders_with_audio(base_path, request)
        
        # Should find multiple folders with audio: Album 1, Album 2, Bonus, single file in root
        assert len(folders) >= 3
        
        # Check Album 1
        album1_files = folders.get(base_path / "Album 1", [])
        assert len(album1_files) == 3  # track1.mp3, track2.mp3, track3.mp3
        assert all(f.suffix == '.mp3' for f in album1_files)
        
        # Check Album 2
        album2_files = folders.get(base_path / "Album 2", [])
        assert len(album2_files) == 2  # track1.mp3, track2.mp3
        
        # Check Bonus subfolder
        bonus_files = folders.get(base_path / "Album 2" / "Bonus", [])
        assert len(bonus_files) == 2  # bonus_track.mp3, hidden.mp3
    
    def test_discover_folders_respects_max_depth(self, adapter, mock_audio_directory):
        """Test folder discovery respects max_depth parameter."""
        request = {
            'file_extensions': ['.mp3'],
            'max_depth': 1  # Only go 1 level deep
        }
        
        base_path = mock_audio_directory
        folders = adapter._discover_folders_with_audio(base_path, request)
        
        # Should find Album 1 and Album 2, but NOT Bonus (depth 2)
        assert base_path / "Album 1" in folders
        assert base_path / "Album 2" in folders
        assert base_path / "Album 2" / "Bonus" not in folders
    
    def test_discover_folders_filters_by_extension(self, adapter, mock_audio_directory):
        """Test folder discovery filters files by extension."""
        base_path = mock_audio_directory
        # Add non-audio file
        (base_path / "Album 1" / "readme.txt").write_text("This is a readme file")
        
        request = {'file_extensions': ['.mp3']}
        
        folders = adapter._discover_folders_with_audio(base_path, request)
        
        album1_files = folders.get(base_path / "Album 1", [])
        # Should only find .mp3 files, not .txt
        assert all(f.suffix == '.mp3' for f in album1_files)
        assert len(album1_files) == 3  # track1, track2, track3 (not readme.txt)
    
    def test_discover_folders_sorts_files(self, adapter, mock_audio_directory):
        """Test folder discovery returns sorted file lists."""
        request = {'file_extensions': ['.mp3']}
        
        base_path = mock_audio_directory
        folders = adapter._discover_folders_with_audio(base_path, request)
        
        for folder_path, files in folders.items():
            # Check that files are sorted
            sorted_files = sorted(files)
            assert files == sorted_files


class TestMetadataExtraction:
    """Test metadata extraction from audio files for template substitution."""
    
    @patch('TonieToolbox.core.media.tags.get_media_tag_service')
    def test_extract_folder_metadata_uses_first_file(self, mock_get_service, adapter, tmp_path, sample_audio_files):
        """Test metadata extraction uses first audio file as representative."""
        import shutil
        
        # Get source test audio file from fixtures
        test_audio_file = sample_audio_files['mp3_stereo']
        
        # Create test files
        files = [tmp_path / "track1.mp3", tmp_path / "track2.mp3"]
        for f in files:
            shutil.copy(test_audio_file, f)
        
        # Mock tag service
        mock_tag_service = Mock()
        mock_get_service.return_value = mock_tag_service
        
        adapter.path_resolver.resolve_metadata_from_input = Mock(
            return_value={'artist': 'Artist', 'album': 'Album'}
        )
        
        request = {'use_media_tags': True}
        
        metadata = adapter._extract_folder_metadata(files, request)
        
        # Should extract from first file
        adapter.path_resolver.resolve_metadata_from_input.assert_called_once()
        call_args = adapter.path_resolver.resolve_metadata_from_input.call_args
        assert call_args[0][0] == files[0]  # First file
        
        assert metadata == {'artist': 'Artist', 'album': 'Album'}
    
    def test_extract_folder_metadata_returns_empty_when_disabled(self, adapter, tmp_path, sample_audio_files):
        """Test metadata extraction returns empty dict when use_media_tags is False."""
        import shutil
        
        test_audio_file = sample_audio_files['mp3_stereo']
        files = [tmp_path / "track1.mp3"]
        shutil.copy(test_audio_file, files[0])
        
        request = {'use_media_tags': False}
        
        metadata = adapter._extract_folder_metadata(files, request)
        
        assert metadata == {}
    
    def test_extract_folder_metadata_handles_errors(self, adapter, tmp_path, sample_audio_files):
        """Test metadata extraction handles errors gracefully."""
        import shutil
        
        test_audio_file = sample_audio_files['mp3_stereo']
        files = [tmp_path / "track1.mp3"]
        shutil.copy(test_audio_file, files[0])
        
        # Mock resolver to raise exception
        adapter.path_resolver.resolve_metadata_from_input = Mock(
            side_effect=Exception("Metadata extraction failed")
        )
        
        request = {'use_media_tags': True}
        
        metadata = adapter._extract_folder_metadata(files, request)
        
        # Should return empty dict and log warning
        assert metadata == {}
        adapter.logger.warning.assert_called()


class TestOutputPathResolution:
    """Test output path resolution for folder-based TAF files."""
    
    def test_resolve_folder_output_path_with_templates(self, adapter, tmp_path):
        """Test output path resolution using templates."""
        folder = tmp_path / "MyAlbum"
        folder.mkdir()
        
        metadata = {'artist': 'Test Artist', 'album': 'Test Album'}
        
        adapter.path_resolver.resolve_output_path = Mock(
            return_value=tmp_path / "output" / "Test Artist" / "Test Album.taf"
        )
        
        request = {
            'use_media_tags': True,
            'name_template': '{album}',
            'output_to_template': '{artist}',
            'preserve_structure': False
        }
        
        output_path = adapter._resolve_folder_output_path(
            folder_path=folder,
            input_dir=tmp_path,
            output_dir=tmp_path / "output",
            metadata=metadata,
            request=request
        )
        
        # Should use path resolver with templates
        adapter.path_resolver.resolve_output_path.assert_called_once()
        call_kwargs = adapter.path_resolver.resolve_output_path.call_args[1]
        assert call_kwargs['metadata'] == metadata
        assert call_kwargs['use_templates'] == True
    
    def test_resolve_folder_output_path_preserves_structure(self, adapter, tmp_path):
        """Test output path resolution preserves directory structure."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        folder = input_dir / "subfolder" / "album"
        folder.mkdir(parents=True)
        
        output_dir = tmp_path / "output"
        
        request = {
            'use_media_tags': False,
            'preserve_structure': True
        }
        
        output_path = adapter._resolve_folder_output_path(
            folder_path=folder,
            input_dir=input_dir,
            output_dir=output_dir,
            metadata={},
            request=request
        )
        
        # Should preserve structure: output/subfolder/album/album.taf
        assert output_path.parent.name == "album"
        assert output_path.parent.parent.name == "subfolder"
    
    def test_resolve_folder_output_path_flattens_without_preserve(self, adapter, tmp_path):
        """Test output path resolution flattens to output dir when preserve_structure=False."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        folder = input_dir / "deep" / "nested" / "album"
        folder.mkdir(parents=True)
        
        output_dir = tmp_path / "output"
        
        adapter.path_resolver.resolve_output_path = Mock(
            return_value=output_dir / "album.taf"
        )
        
        request = {
            'use_media_tags': False,
            'preserve_structure': False
        }
        
        output_path = adapter._resolve_folder_output_path(
            folder_path=folder,
            input_dir=input_dir,
            output_dir=output_dir,
            metadata={},
            request=request
        )
        
        # Should be directly in output dir
        assert output_path.parent == output_dir


class TestCombineModeBehavior:
    """Test combine mode (default --recursive behavior)."""
    
    def test_execute_combine_mode_discovers_folders(self, adapter, mock_audio_directory):
        """Test combine mode discovers folders with audio files."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': False,  # Combine mode
            'file_extensions': ['.mp3']
        }
        
        with patch.object(adapter, '_discover_folders_with_audio', return_value={}) as mock_discover:
            with patch.object(adapter, '_process_folders_to_taf', return_value=0) as mock_process:
                adapter.execute(request)
        
        # _process_folders_to_taf should have been called
        assert mock_process.called
    
    @patch('TonieToolbox.core.processing.interface.adapters.files_to_taf_adapter.FilesToTafAdapter')
    def test_combine_mode_calls_files_to_taf_adapter(self, mock_adapter_class, adapter, tmp_path, sample_audio_files):
        """Test combine mode uses FilesToTafAdapter to combine files."""
        import shutil
        
        # Get source test audio file from fixtures
        test_audio_file = sample_audio_files['mp3_stereo']
        
        # Setup
        folder = tmp_path / "album"
        folder.mkdir()
        files = [folder / f"track{i}.mp3" for i in range(3)]
        for f in files:
            shutil.copy(test_audio_file, f)
        
        mock_adapter_instance = Mock()
        mock_adapter_instance.execute = Mock(return_value=0)
        mock_adapter_class.return_value = mock_adapter_instance
        
        request = {
            'quality': 'HIGH',
            'normalize_audio': True
        }
        
        output_path = tmp_path / "output.taf"
        
        # Execute
        result = adapter._combine_files_to_taf(files, output_path, request)
        
        # Verify FilesToTafAdapter was used
        mock_adapter_class.assert_called_once()
        mock_adapter_instance.execute.assert_called_once()
        
        # Verify request was properly constructed
        execute_call_args = mock_adapter_instance.execute.call_args[0][0]
        assert execute_call_args['quality'] == 'HIGH'
        assert execute_call_args['normalize_audio'] == True


class TestIndividualModeBehavior:
    """Test individual mode (--recursive --files-to-taf behavior)."""
    
    @patch('TonieToolbox.core.processing.interface.adapters.single_file_adapter.SingleFileProcessingAdapter')
    def test_execute_individual_mode_processes_each_file(self, mock_adapter_class, adapter, mock_audio_directory):
        """Test individual mode processes each file separately."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': True,  # Individual mode
            'file_extensions': ['.mp3']
        }
        
        # Mock adapter instance
        mock_adapter_instance = Mock()
        mock_adapter_instance.execute = Mock(return_value=0)
        mock_adapter_class.return_value = mock_adapter_instance
        
        with patch.object(adapter, '_discover_recursive_files') as mock_discover:
            # Mock 3 files
            mock_files = [
                (base_path / "file1.mp3", base_path / "output" / "file1.taf"),
                (base_path / "file2.mp3", base_path / "output" / "file2.taf"),
                (base_path / "file3.mp3", base_path / "output" / "file3.taf")
            ]
            mock_discover.return_value = mock_files
            
            result = adapter.execute(request)
        
        # Should process all 3 files through SingleFileProcessingAdapter
        assert mock_adapter_instance.execute.call_count == 3
    
    def test_individual_mode_respects_max_depth(self, adapter, mock_audio_directory):
        """Test individual mode respects max_depth in file discovery."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': True,
            'max_depth': 1,
            'file_extensions': ['.mp3']
        }
        
        # Execute discovery
        files = adapter._discover_recursive_files(base_path, request)
        
        # Should not include files from Bonus subfolder (depth 2) or deeper
        file_paths = [f[0] for f in files]
        assert not any('Bonus' in str(p) for p in file_paths)
        assert not any('Remixes' in str(p) for p in file_paths)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_combine_mode_continues_on_folder_error(self, adapter, mock_audio_directory):
        """Test combine mode continues processing other folders when one fails."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': False,
            'continue_on_error': True,
            'file_extensions': ['.mp3']
        }
        
        # Mock _combine_files_to_taf to fail on first call, succeed on others
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1  # Failure
            return 0  # Success
        
        with patch.object(adapter, '_combine_files_to_taf', side_effect=side_effect) as mock_combine:
            with patch.object(adapter, '_extract_folder_metadata', return_value={}):
                with patch.object(adapter, '_resolve_folder_output_path', return_value=Path("/output.taf")):
                    adapter.execute(request)
        
        # Should have attempted multiple folders despite first failure
        assert mock_combine.call_count > 1
    
    @patch('TonieToolbox.core.processing.interface.adapters.single_file_adapter.SingleFileProcessingAdapter')
    def test_individual_mode_continues_on_file_error(self, mock_adapter_class, adapter, mock_audio_directory):
        """Test individual mode continues processing other files when one fails."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': True,
            'continue_on_error': True,
            'file_extensions': ['.mp3']
        }
        
        # Mock adapter instance to fail on first file
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1  # Failure
            return 0  # Success
        
        mock_adapter_instance = Mock()
        mock_adapter_instance.execute = Mock(side_effect=side_effect)
        mock_adapter_class.return_value = mock_adapter_instance
        
        # Create multiple files
        with patch.object(adapter, '_discover_recursive_files') as mock_discover:
            mock_files = [
                (base_path / f"file{i}.mp3", base_path / f"output{i}.taf")
                for i in range(3)
            ]
            mock_discover.return_value = mock_files
            
            result = adapter.execute(request)
        
        # Should have attempted all 3 files
        assert mock_adapter_instance.execute.call_count == 3
    
    def test_empty_directory_returns_success(self, adapter, tmp_path):
        """Test processing empty directory returns success code."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        request = {
            'input_directory': str(empty_dir),
            'output_directory': str(tmp_path / "output"),
            'files_to_taf': False,
            'file_extensions': ['.mp3']
        }
        
        result = adapter.execute(request)
        
        # No files to process, should still succeed
        assert result == 0
    
    def test_invalid_input_directory_raises_error(self, adapter):
        """Test adapter handles invalid input directory."""
        request = {
            'input_directory': '/nonexistent/path',
            'output_directory': '/output',
            'files_to_taf': False
        }
        
        # Should return non-zero error code
        result = adapter.execute(request)
        assert result != 0


class TestProgressReporting:
    """Test progress reporting during processing."""
    
    def test_combine_mode_reports_progress(self, adapter, mock_audio_directory):
        """Test combine mode reports progress for each folder."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': False,
            'file_extensions': ['.mp3']
        }
        
        with patch.object(adapter, '_combine_files_to_taf', return_value=0):
            with patch.object(adapter, '_extract_folder_metadata', return_value={}):
                with patch.object(adapter, '_resolve_folder_output_path', return_value=Path("/output.taf")):
                    adapter.execute(request)
        
        # Should have called _update_progress multiple times
        assert adapter._update_progress.call_count > 0
    
    def test_individual_mode_reports_progress(self, adapter, mock_audio_directory):
        """Test individual mode reports progress for each file."""
        base_path = mock_audio_directory
        request = {
            'input_directory': str(base_path),
            'output_directory': str(base_path / "output"),
            'files_to_taf': True,
            'file_extensions': ['.mp3']
        }
        
        with patch.object(adapter, '_discover_recursive_files') as mock_discover:
            mock_files = [(base_path / "file.mp3", base_path / "output.taf")]
            mock_discover.return_value = mock_files
            
            with patch.object(adapter.processing_service, 'process_file', return_value=0):
                adapter.execute(request)
        
        # Should report progress
        assert adapter._update_progress.call_count > 0
