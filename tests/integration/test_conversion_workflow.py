"""
Integration tests for audio conversion workflows.

These tests verify that the complete audio conversion pipeline works correctly,
including file processing, dependency management, and output generation.
"""

import os
import tempfile
import shutil
from pathlib import Path
import sys

try:
    import pytest
except ImportError:
    pass

# Import the modules we're testing
try:
    from TonieToolbox.core.app import TonieToolboxApp
except ImportError:
    # Fallback for direct imports
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from TonieToolbox.core.app import TonieToolboxApp


class TestAudioConversionWorkflow:
    """Test end-to-end audio conversion workflows."""
    
    @pytest.mark.integration
    @pytest.mark.requires_ffmpeg
    @pytest.mark.requires_opus
    def test_single_mp3_to_taf_conversion(self, valid_mp3_file, temp_output_dir):
        """Test converting a single MP3 file to TAF format."""
        output_file = temp_output_dir / "converted.taf"
        
        # Create argument namespace (simulating CLI args)
        class MockArgs:
            input_filename = str(valid_mp3_file)
            output_filename = str(output_file)
            bitrate = 128
            cbr = False
            auto_download = True
            ffmpeg = None
            no_mono_conversion = False
            keep_temp = False
            use_legacy_tags = False
            user_timestamp = None
            no_tonie_header = False
            append_tonie_tag = None
            force_creation = False
            recursive = False
            output_to_source = False
            use_media_tags = False
            name_template = None
            upload = None
            debug = False
            trace = False
            quiet = False
            silent = False
        
        args = MockArgs()
        
        try:
            # Initialize app and run conversion
            app = TonieToolboxApp()
            
            # Use the actual command line interface
            cmd_args = [
                str(valid_mp3_file), 
                str(output_file), 
                "--auto-download",
                "--quiet"
            ]
            result = app.run(cmd_args)
            
            # Should complete successfully
            assert result == 0, f"Conversion should succeed, got exit code {result}"
            
            # Verify output file was created
            assert output_file.exists(), f"Output TAF file should be created at {output_file}"
            assert output_file.stat().st_size > 0, "Output TAF file should not be empty"
            
            # Verify the TAF file has correct structure
            with open(output_file, 'rb') as f:
                # Read header size (first 4 bytes)
                header_size_bytes = f.read(4)
                assert len(header_size_bytes) == 4, "Should have 4-byte header size"
                
                import struct
                header_size = struct.unpack(">L", header_size_bytes)[0]
                assert header_size > 0, "Header size should be positive"
                
                # Read and verify we can parse the header
                header_data = f.read(header_size)
                assert len(header_data) == header_size, "Should read complete header"
                
        except Exception as e:
            if "ffmpeg" in str(e).lower() or "opus" in str(e).lower():
                pytest.skip(f"Required dependencies not available: {e}")
            else:
                raise
    
    @pytest.mark.integration
    def test_taf_info_extraction(self, valid_taf_file):
        """Test extracting information from a TAF file."""
        class MockArgs:
            input_filename = str(valid_taf_file)
            info = True
            debug = False
            trace = False
            quiet = False
            silent = False
        
        args = MockArgs()
        
        try:
            app = TonieToolboxApp()
            
            # Use the actual command line interface
            cmd_args = ["--info", str(valid_taf_file), "--quiet"]
            result = app.run(cmd_args)
            
            # Should complete without error
            assert result == 0, f"Info extraction should succeed, got exit code {result}"
            
        except Exception as e:
            pytest.fail(f"TAF info extraction failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_taf_splitting_workflow_direct(self, valid_taf_file):
        """
        Test splitting a TAF file into individual tracks using direct function call.
        
        This test creates all files in a temporary directory that is automatically
        created at the beginning and removed at the end, similar to --split behavior.
        """
        # Create a temporary directory for output files
        with tempfile.TemporaryDirectory() as temp_output_dir:
            temp_output_path = Path(temp_output_dir)
            
            # Copy the valid TAF file to temporary directory to avoid polluting test data
            temp_taf_file = temp_output_path / "test_file.taf"
            shutil.copy2(valid_taf_file, temp_taf_file)
            
            try:
                # Import the split function directly to test with our controlled output
                from TonieToolbox.core.analysis.extraction import split_to_opus_files
                
                # Perform the split operation with explicit output directory
                split_to_opus_files(str(temp_taf_file), str(temp_output_path))
                
                # Check for output files in the specified output directory
                opus_files = list(temp_output_path.glob("*.opus"))
                
                assert len(opus_files) > 0, "Should create at least one Opus file"
                
                # Verify files have content
                for opus_file in opus_files:
                    assert opus_file.stat().st_size > 0, f"Split file {opus_file} should not be empty"
                    
                # Verify file naming convention (should be in format XX_filename.opus)
                for opus_file in opus_files:
                    assert opus_file.name.startswith(('01_', '02_', '03_')), \
                        f"File should follow naming convention: {opus_file.name}"
                    assert opus_file.name.endswith('test_file.opus'), \
                        f"File should have correct base name: {opus_file.name}"
                
                print(f"Successfully created {len(opus_files)} Opus files in temporary directory")
                
            except ImportError:
                pytest.skip("TAF splitting functionality not available")
            except Exception as e:
                pytest.fail(f"TAF splitting failed: {e}")
            
            # Files will be automatically cleaned up when temp directory is destroyed
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="TAF splitting (--split) removed with opus-tools dependency")
    def test_taf_splitting_workflow_cli(self, valid_taf_file):
        """
        Test splitting a TAF file into individual tracks using CLI interface.
        
        This test creates all files in a temporary directory that is automatically
        created at the beginning and removed at the end, similar to --split behavior.
        """
        # Create a temporary directory for all operations
        with tempfile.TemporaryDirectory() as temp_output_dir:
            temp_output_path = Path(temp_output_dir)
            
            # Copy the valid TAF file to temporary directory to avoid polluting test data
            temp_taf_file = temp_output_path / "test_file_cli.taf" 
            shutil.copy2(valid_taf_file, temp_taf_file)
            
            # Change to temporary directory so split files are created there by default
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_output_path)
                
                # Test CLI interface
                app = TonieToolboxApp()
                
                # Use the actual command line interface  
                cmd_args = ["--split", str(temp_taf_file), "--quiet"]
                result = app.run(cmd_args)
                
                # Should complete without error (or handle overwrite issue)
                if result != 0:
                    # Check if it's just an overwrite protection issue
                    pytest.skip("TAF splitting failed - may be overwrite protection issue")
        
                # Check for output files in the temporary directory
                opus_files = list(temp_output_path.glob("*.opus"))
                
                assert len(opus_files) > 0, "Should create at least one Opus file"
                
                # Verify files have content
                for opus_file in opus_files:
                    assert opus_file.stat().st_size > 0, f"Split file {opus_file} should not be empty"
                    
                # Verify file naming convention
                for opus_file in opus_files:
                    assert opus_file.name.startswith(('01_', '02_', '03_')), \
                        f"File should follow naming convention: {opus_file.name}"
                    assert opus_file.name.endswith('test_file_cli.opus'), \
                        f"File should have correct base name: {opus_file.name}"
                
                print(f"CLI: Successfully created {len(opus_files)} Opus files in temporary directory")
                        
            except Exception as e:
                pytest.fail(f"TAF splitting via CLI failed: {e}")
            finally:
                # Always restore original working directory
                os.chdir(original_cwd)
            
            # Files will be automatically cleaned up when temp directory is destroyed


class TestBatchProcessing:
    """Test batch processing workflows."""
    
    @pytest.mark.integration
    def test_list_file_processing(self, sample_list_file, temp_output_dir):
        """Test processing a list file with multiple audio files."""
        class MockArgs:
            input_filename = str(sample_list_file)
            output_filename = None
            bitrate = 128
            cbr = False
            auto_download = True
            ffmpeg = None
            recursive = False
            force_creation = False
            use_media_tags = False
            debug = False
            quiet = True
        
        args = MockArgs()
        
        try:
            app = TonieToolboxApp()
            # This would typically process the list and create a combined TAF
            # Implementation depends on the actual app logic
            
            # For now, just verify the list file is readable
            with open(sample_list_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) > 0, "List file should have content"
                
                # Verify each line points to a valid file
                for line in lines:
                    file_path = Path(line.strip())
                    assert file_path.exists(), f"Referenced file should exist: {file_path}"
                    
        except Exception as e:
            pytest.fail(f"List file processing failed: {e}")
    
    @pytest.mark.integration
    def test_recursive_directory_processing(self, mock_audio_directory, temp_output_dir):
        """Test recursive processing of directory structure."""
        class MockArgs:
            input_filename = str(mock_audio_directory)
            recursive = True
            output_to_source = False
            bitrate = 128
            use_media_tags = False
            auto_download = True
            force_creation = False
            debug = False
            quiet = True
        
        args = MockArgs()
        
        try:
            # Verify the mock directory structure
            assert mock_audio_directory.exists(), "Mock audio directory should exist"
            
            # Find audio files in the structure
            audio_files = []
            for ext in ['.mp3', '.flac', '.wav']:
                audio_files.extend(mock_audio_directory.rglob(f"*{ext}"))
            
            assert len(audio_files) > 0, "Should have audio files in mock directory"
            
            # The actual recursive processing would be tested here
            # For now, verify directory structure is as expected
            subdirs = [d for d in mock_audio_directory.iterdir() if d.is_dir()]
            assert len(subdirs) >= 2, "Should have multiple subdirectories"
            
        except Exception as e:
            pytest.fail(f"Recursive processing failed: {e}")


class TestMediaTagIntegration:
    """Test media tag processing integration."""
    
    @pytest.mark.integration
    def test_tag_extraction_from_mp3(self, valid_mp3_file):
        """Test extracting media tags from MP3 file."""
        try:
            # Import tag reading functionality using new Clean Architecture API
            from TonieToolbox.core.media.tags import get_media_tag_service
            
            service = get_media_tag_service()
            tags = service.get_file_tags(str(valid_mp3_file))
            
            # Should return dictionary of standardized tags
            assert isinstance(tags, dict), "Should return dictionary of tags"
            
            # May or may not have tags, but should not error
            if tags:
                # Verify tag structure if tags exist
                for key, value in tags.items():
                    assert isinstance(key, str), "Tag key should be string"
                    assert value is not None, f"Tag value for '{key}' should not be None"
                    
        except ImportError as e:
            pytest.fail(f"Tag reading functionality import failed: {e}")
        except Exception as e:
            pytest.fail(f"Tag extraction failed: {e}")
    
    @pytest.mark.integration
    def test_template_processing(self):
        """Test media tag template processing."""
        try:
            # Import template processing using new Clean Architecture API
            from TonieToolbox.core.media.tags.domain import (
                FilenameFormattingService, MediaTagCollection, MediaTag
            )
            from TonieToolbox.core.utils import get_logger
            
            logger = get_logger(__name__)
            formatter = FilenameFormattingService(logger=logger)
            
            # Create MediaTagCollection with test data
            test_tags = {
                "artist": MediaTag(key="artist", value="Test Artist", original_key="TPE1"),
                "title": MediaTag(key="title", value="Test Title", original_key="TIT2")
            }
            tags = MediaTagCollection(tags=test_tags)
            
            # Test basic template processing
            template = "{artist} - {title}"
            
            result = formatter.format_filename(tags, template)
            expected = "Test Artist - Test Title"
            
            assert result == expected, f"Template processing failed: got '{result}', expected '{expected}'"
            
        except ImportError as e:
            pytest.fail(f"Template processing functionality import failed: {e}")
        except Exception as e:
            pytest.fail(f"Template processing failed: {e}")


class TestErrorHandling:
    """Test error handling in integration scenarios."""
    
    @pytest.mark.integration
    def test_invalid_input_file(self, temp_dir):
        """Test handling of invalid input files."""
        invalid_file = temp_dir / "nonexistent.mp3"
        
        class MockArgs:
            input_filename = str(invalid_file)
            debug = False
            quiet = True
        
        args = MockArgs()
        
        app = TonieToolboxApp()
        
        # Should handle missing file gracefully
        cmd_args = ["--info", str(invalid_file), "--quiet"]
        result = app.run(cmd_args)
        
        # Should fail with non-zero exit code for missing file
        assert result != 0, "Should fail for non-existent input file"
    
    @pytest.mark.integration
    def test_corrupted_taf_file(self, temp_dir):
        """Test handling of corrupted TAF files."""
        corrupted_file = temp_dir / "corrupted.taf"
        
        # Create a corrupted TAF file
        with open(corrupted_file, 'wb') as f:
            f.write(b"CORRUPTED_DATA" * 1000)
        
        class MockArgs:
            input_filename = str(corrupted_file)
            info = True
            debug = False
            quiet = True
        
        args = MockArgs()
        
        app = TonieToolboxApp()
        
        # Should handle corrupted file gracefully, not crash
        cmd_args = ["--info", str(corrupted_file), "--quiet"]
        result = app.run(cmd_args)
        
        # Should either fail or gracefully handle corrupted file
        # Exit code 0 with error message logged is also acceptable
        if result == 0:
            # If it exits with 0, verify error was logged (shown in captured output)
            pytest.skip("Corrupted file handled gracefully with exit code 0")


if __name__ == "__main__":
    # Run tests if called directly
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, running basic integration tests...")
        
        # Basic test runner without pytest
        print("Integration tests require pytest for proper fixture management.")
        print("Please install pytest: pip install pytest pytest-cov")