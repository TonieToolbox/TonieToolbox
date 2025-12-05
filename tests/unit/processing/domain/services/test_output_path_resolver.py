#!/usr/bin/env python3
"""
Unit tests for OutputPathResolver domain service.

Tests cover all business logic for output path resolution including:
- Explicit output paths
- Template-based path generation
- Default path generation
- Metadata extraction
- Edge cases and error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from TonieToolbox.core.processing.domain.services.output_path_resolver import OutputPathResolver


class TestOutputPathResolverBasics:
    """Test basic initialization and simple path resolution."""
    
    def test_initialization(self):
        """Test service initializes correctly."""
        resolver = OutputPathResolver()
        assert resolver is not None
        assert resolver.logger is not None
    
    def test_initialization_with_logger(self):
        """Test service accepts custom logger."""
        mock_logger = Mock()
        resolver = OutputPathResolver(logger=mock_logger)
        assert resolver.logger == mock_logger


class TestExplicitOutputPath:
    """Test explicit output path handling (highest priority)."""
    
    def test_explicit_path_used_directly(self):
        """Test that explicit output path is used without modification."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        explicit_output = Path("/output/result.taf")
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            explicit_output_path=explicit_output
        )
        
        assert result == explicit_output
    
    def test_explicit_path_gets_taf_extension(self):
        """Test that explicit path without .taf gets extension added."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        explicit_output = Path("/output/result")
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            explicit_output_path=explicit_output
        )
        
        assert result == Path("/output/result.taf")
    
    def test_explicit_path_ignores_templates(self):
        """Test that templates are ignored when explicit path provided."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        explicit_output = Path("/output/result.taf")
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            explicit_output_path=explicit_output,
            output_directory_template="{artist}/{album}",
            filename_template="{title}",
            metadata={"artist": "Test", "album": "Album", "title": "Song"},
            use_templates=True
        )
        
        # Should use explicit path, not templates
        assert result == explicit_output


class TestTemplateBasedPathResolution:
    """Test template-based path generation with metadata."""
    
    @patch('TonieToolbox.core.utils.filename.apply_template_to_path')
    def test_directory_template_only(self, mock_apply_template):
        """Test resolution with only directory template."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        
        # Mock template application
        mock_apply_template.return_value = "/output/Artist/Album"
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            output_directory_template="{artist}/{album}",
            metadata={"artist": "Artist", "album": "Album"},
            use_templates=True
        )
        
        # Should use template directory + default filename
        assert result.parent == Path("/output/Artist/Album")
        assert result.suffix == ".taf"
    
    @patch('TonieToolbox.core.utils.filename.apply_template_to_path')
    @patch('TonieToolbox.core.utils.filename.guess_output_filename')
    def test_filename_template_only(self, mock_guess_filename, mock_apply_template):
        """Test resolution with only filename template."""
        resolver = OutputPathResolver()
        input_path = Path("/input/directory")
        
        # Mock template application
        mock_apply_template.return_value = "Artist - Album"
        mock_guess_filename.return_value = "default"
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            filename_template="{artist} - {album}",
            metadata={"artist": "Artist", "album": "Album"},
            use_templates=True
        )
        
        # Should use template filename
        assert result.name == "Artist - Album.taf"
    
    @patch('TonieToolbox.core.utils.filename.apply_template_to_path')
    def test_both_templates(self, mock_apply_template):
        """Test resolution with both directory and filename templates."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        
        # Mock template application - called twice (directory, then filename)
        mock_apply_template.side_effect = [
            "/output/Artist/Album",  # directory template
            "Artist - Album"          # filename template
        ]
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            output_directory_template="{artist}/{album}",
            filename_template="{artist} - {album}",
            metadata={"artist": "Artist", "album": "Album"},
            use_templates=True
        )
        
        assert result == Path("/output/Artist/Album/Artist - Album.taf")
    
    @patch('TonieToolbox.core.utils.filename.apply_template_to_path')
    def test_directory_template_strips_taf_extension(self, mock_apply_template):
        """Test that .taf extension is stripped from directory template."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        
        # User accidentally included .taf in directory template
        mock_apply_template.return_value = "/output/Artist/Album.taf"
        
        result = resolver.resolve_output_path(
            input_path=input_path,
            output_directory_template="{artist}/{album}.taf",
            metadata={"artist": "Artist", "album": "Album"},
            use_templates=True
        )
        
        # .taf should be stripped from directory
        assert result.parent == Path("/output/Artist/Album")
        assert result.suffix == ".taf"


class TestDefaultPathGeneration:
    """Test default path generation without templates."""
    
    @patch('TonieToolbox.core.utils.filename.guess_output_filename')
    def test_directory_input(self, mock_guess_filename):
        """Test default path for directory input."""
        resolver = OutputPathResolver()
        input_path = Path("/input/my_album")
        
        # Mock directory check
        with patch.object(Path, 'is_dir', return_value=True):
            mock_guess_filename.return_value = "my_album"
            
            result = resolver.resolve_output_path(input_path=input_path)
            
            assert result == Path("/input/my_album/my_album.taf")
    
    @patch('TonieToolbox.core.utils.filename.guess_output_filename')
    def test_file_input(self, mock_guess_filename):
        """Test default path for file input."""
        resolver = OutputPathResolver()
        input_path = Path("/input/song.mp3")
        
        # Mock file check
        with patch.object(Path, 'is_dir', return_value=False):
            mock_guess_filename.return_value = "song"
            
            result = resolver.resolve_output_path(input_path=input_path)
            
            assert result == Path("/input/song.taf")


class TestMetadataExtraction:
    """Test metadata extraction from audio files."""
    
    def test_metadata_extraction_success(self):
        """Test successful metadata extraction."""
        resolver = OutputPathResolver()
        input_path = Path("/input/song.mp3")
        
        # Mock tag service
        mock_tag_service = Mock()
        mock_tag_service.get_file_tags.return_value = {
            "artist": "Test Artist",
            "album": "Test Album"
        }
        mock_tag_service.get_all_file_tags.return_value = {
            "artist": {
                "original": "TPE1",
                "readable": "artist",
                "value": "Test Artist"
            },
            "album": {
                "original": "TALB",
                "readable": "album",
                "value": "Test Album"
            }
        }
        
        metadata = resolver.resolve_metadata_from_input(input_path, mock_tag_service)
        
        assert "artist" in metadata
        assert metadata["artist"] == "Test Artist"
        assert "album" in metadata
        assert metadata["album"] == "Test Album"
        assert "TPE1" in metadata
        assert "TALB" in metadata
    
    def test_metadata_extraction_no_tags(self):
        """Test metadata extraction when no tags found."""
        resolver = OutputPathResolver()
        input_path = Path("/input/song.mp3")
        
        mock_tag_service = Mock()
        mock_tag_service.get_file_tags.return_value = {}
        mock_tag_service.get_all_file_tags.return_value = {}
        
        metadata = resolver.resolve_metadata_from_input(input_path, mock_tag_service)
        
        assert metadata == {}
    
    def test_metadata_extraction_no_service(self):
        """Test metadata extraction without tag service."""
        resolver = OutputPathResolver()
        input_path = Path("/input/song.mp3")
        
        metadata = resolver.resolve_metadata_from_input(input_path, tag_service=None)
        
        assert metadata == {}
    
    def test_metadata_extraction_handles_errors(self):
        """Test that metadata extraction handles errors gracefully."""
        resolver = OutputPathResolver()
        input_path = Path("/input/song.mp3")
        
        mock_tag_service = Mock()
        mock_tag_service.get_file_tags.side_effect = Exception("Tag read error")
        
        # Should not raise, should return empty dict
        metadata = resolver.resolve_metadata_from_input(input_path, mock_tag_service)
        
        assert metadata == {}


class TestRepresentativeAudioFileFinding:
    """Test finding representative audio file in directory."""
    
    def test_find_mp3_file(self):
        """Test finding MP3 file in directory."""
        resolver = OutputPathResolver()
        
        with patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'glob', return_value=[Path("/dir/song.mp3")]):
            
            result = resolver.find_representative_audio_file(Path("/dir"))
            
            assert result == Path("/dir/song.mp3")
    
    def test_find_flac_file(self):
        """Test finding FLAC file when no MP3."""
        resolver = OutputPathResolver()
        
        with patch.object(Path, 'is_dir', return_value=True):
            def mock_glob(pattern):
                if pattern == "*.mp3":
                    return []
                elif pattern == "*.flac":
                    return [Path("/dir/song.flac")]
                return []
            
            with patch.object(Path, 'glob', side_effect=mock_glob):
                result = resolver.find_representative_audio_file(Path("/dir"))
                
                assert result == Path("/dir/song.flac")
    
    def test_no_audio_files_found(self):
        """Test when no audio files found."""
        resolver = OutputPathResolver()
        
        with patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'glob', return_value=[]):
            
            result = resolver.find_representative_audio_file(Path("/dir"))
            
            assert result is None
    
    def test_not_a_directory(self):
        """Test when path is not a directory."""
        resolver = OutputPathResolver()
        
        with patch.object(Path, 'is_dir', return_value=False):
            result = resolver.find_representative_audio_file(Path("/file.mp3"))
            
            assert result is None


class TestTafExtensionHandling:
    """Test .taf extension enforcement."""
    
    def test_ensures_taf_extension(self):
        """Test that .taf extension is added if missing."""
        resolver = OutputPathResolver()
        path = Path("/output/result")
        
        result = resolver._ensure_taf_extension(path)
        
        assert result == Path("/output/result.taf")
    
    def test_preserves_existing_taf_extension(self):
        """Test that existing .taf extension is preserved."""
        resolver = OutputPathResolver()
        path = Path("/output/result.taf")
        
        result = resolver._ensure_taf_extension(path)
        
        assert result == Path("/output/result.taf")
    
    def test_replaces_other_extensions(self):
        """Test that non-.taf extensions are replaced."""
        resolver = OutputPathResolver()
        path = Path("/output/result.mp3")
        
        result = resolver._ensure_taf_extension(path)
        
        assert result == Path("/output/result.taf")


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @patch('TonieToolbox.core.utils.filename.apply_template_to_path')
    def test_template_fails_fallback_to_default(self, mock_apply_template):
        """Test fallback to default when template fails."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        
        # Template returns None (failure)
        mock_apply_template.return_value = None
        
        with patch.object(Path, 'is_dir', return_value=False):
            result = resolver.resolve_output_path(
                input_path=input_path,
                output_directory_template="{missing_tag}",
                metadata={},
                use_templates=True
            )
            
            # Should fall back to current directory
            assert result.name == "file.taf"
    
    def test_use_templates_false_ignores_templates(self):
        """Test that templates are ignored when use_templates=False."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        
        with patch.object(Path, 'is_dir', return_value=False), \
             patch('TonieToolbox.core.utils.filename.guess_output_filename', return_value="file"):
            
            result = resolver.resolve_output_path(
                input_path=input_path,
                output_directory_template="{artist}/{album}",
                filename_template="{title}",
                metadata={"artist": "Artist", "album": "Album", "title": "Title"},
                use_templates=False
            )
            
            # Should use default path, not templates
            assert result == Path("/input/file.taf")
    
    @patch('TonieToolbox.core.utils.filename.apply_template_to_path')
    def test_filename_with_taf_extension_in_template(self, mock_apply_template):
        """Test filename template that includes .taf extension."""
        resolver = OutputPathResolver()
        input_path = Path("/input/file.mp3")
        
        # Template returns filename with .taf already
        mock_apply_template.return_value = "song.taf"
        
        with patch.object(Path, 'is_dir', return_value=False):
            result = resolver.resolve_output_path(
                input_path=input_path,
                filename_template="{title}.taf",
                metadata={"title": "song"},
                use_templates=True
            )
            
            # Should not double .taf
            assert result.name == "song.taf"
            assert str(result).count(".taf") == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
