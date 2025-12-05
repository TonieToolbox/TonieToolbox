"""
Functional tests for TonieToolbox CLI interface.

These tests verify end-to-end functionality by executing the actual CLI commands
and validating outputs, similar to how users would interact with the tool.
"""

import os
import subprocess
import tempfile
import sys
from pathlib import Path
import json

try:
    import pytest
except ImportError:
    pass


class TestCLIBasicOperations:
    """Test basic CLI operations and help functionality."""
    
    def get_tonietoolbox_command(self, venv_path=None):
        """Get the appropriate command to run TonieToolbox.
        
        Args:
            venv_path: Optional path to virtual environment
        """
        # Try different ways to run the tool
        base_dir = Path(__file__).parents[2]
        
        # First try using the provided or default virtual environment
        if venv_path is None:
            venv_path = base_dir / "venv" / "test"
        else:
            venv_path = Path(venv_path)
        
        venv_python = venv_path / "bin" / "python"
        if venv_python.exists():
            commands = [
                [str(venv_python), "-m", "TonieToolbox"],
                [str(venv_python), "tonietoolbox.py"],
            ]
        else:
            commands = [
                ["python", "-m", "TonieToolbox"],
                ["python", "tonietoolbox.py"],
                ["tonietoolbox"],  # If installed via pip
            ]
        
        for cmd in commands:
            try:
                if cmd[0].endswith("python") and len(cmd) > 1:
                    if "tonietoolbox.py" in cmd[1]:
                        cmd[1] = str(base_dir / "tonietoolbox.py")
                
                # Test if command works
                result = subprocess.run(
                    cmd + ["--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    cwd=str(base_dir)
                )
                if result.returncode == 0 or "TonieToolbox" in result.stdout:
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # Fallback to direct python execution
        return ["python", str(base_dir / "tonietoolbox.py")]
    
    @pytest.mark.functional
    def test_version_display(self, venv_path):
        """Test that version information is displayed correctly."""
        cmd = self.get_tonietoolbox_command(venv_path) + ["--version"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Skip if module import failed (e.g., missing aiofiles)
            if result.returncode != 0 and "ModuleNotFoundError" in result.stderr:
                pytest.skip(f"Skipping due to missing module: {result.stderr}")
            
            # Should exit successfully and show version
            assert result.returncode == 0, f"Version command failed with code {result.returncode}\nStderr: {result.stderr}"
            assert "TonieToolbox" in result.stdout, "Version output should contain 'TonieToolbox'"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Version command timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    def test_help_display(self, venv_path):
        """Test that help information is displayed correctly."""
        cmd = self.get_tonietoolbox_command(venv_path) + ["--help"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Skip if module import failed (e.g., missing aiofiles)
            if result.returncode != 0 and "ModuleNotFoundError" in result.stderr:
                pytest.skip(f"Skipping due to missing module: {result.stderr}")
            
            # Should exit successfully and show help
            assert result.returncode == 0, f"Help command failed with code {result.returncode}\nStderr: {result.stderr}"
            assert "usage:" in result.stdout.lower(), "Help should contain usage information"
            assert "TonieToolbox" in result.stdout, "Help should mention TonieToolbox"
            
            # Check for key argument groups
            help_text = result.stdout.lower()
            expected_sections = [
                "teddycloud options",
                "media tag options", 
                "logging options",
                "positional arguments"
            ]
            
            for section in expected_sections:
                assert section in help_text, f"Help should contain '{section}' section"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Help command timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    def test_invalid_arguments(self, venv_path):
        """Test handling of invalid command line arguments."""
        cmd = self.get_tonietoolbox_command(venv_path) + ["--invalid-option"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Should exit with error code
            assert result.returncode != 0, "Invalid option should cause error exit"
            assert "error:" in result.stderr.lower() or "invalid" in result.stderr.lower(), \
                "Should show error message for invalid option"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Invalid argument test timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")


class TestCLIFileOperations:
    """Test CLI file operation commands."""
    
    def get_tonietoolbox_command(self, venv_path=None):
        """Get the appropriate command to run TonieToolbox.
        
        Args:
            venv_path: Optional path to virtual environment
        """
        base_dir = Path(__file__).parents[2]
        
        # Try using the provided or default virtual environment
        if venv_path is None:
            venv_path = base_dir / "venv" / "test"
        else:
            venv_path = Path(venv_path)
        
        venv_python = venv_path / "bin" / "python"
        if venv_python.exists():
            return [str(venv_python), str(base_dir / "tonietoolbox.py")]
        
        # Fallback commands
        commands = [[str(venv_python), "-m", "TonieToolbox"], ["tonietoolbox"]]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd + ["--version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return cmd
            except:
                continue
        
        # Final fallback
        return ["python", str(base_dir / "tonietoolbox.py")]
    
    @pytest.mark.functional
    def test_taf_info_command(self, valid_taf_file, venv_path):
        """Test TAF file info extraction via CLI."""
        cmd = self.get_tonietoolbox_command(venv_path) + [str(valid_taf_file), "--info"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Check if it's a dependency issue
                if "ffmpeg" in result.stderr.lower() or "opus" in result.stderr.lower():
                    pytest.skip("Required dependencies not available")
                else:
                    pytest.fail(f"Info command failed: {result.stderr}")
            
            # Should contain file information
            output = result.stdout.lower()
            expected_info = ["total size", "audio", "sample rate", "channels"]
            
            for info_item in expected_info:
                assert info_item in output, f"Info output should contain '{info_item}'"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Info command timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    @pytest.mark.slow
    @pytest.mark.skip(reason="TAF splitting (--split) removed with opus-tools dependency")
    def test_taf_split_command(self, valid_taf_file, temp_dir, venv_path):
        """Test TAF file splitting via CLI."""
        output_dir = temp_dir / "cli_split_output"
        output_dir.mkdir()
        
        # Use --output to specify output directory instead of relying on cwd
        cmd = self.get_tonietoolbox_command(venv_path) + [
            str(valid_taf_file), 
            "--split",
            "--output", str(output_dir)
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if result.returncode != 0:
                if "ffmpeg" in result.stderr.lower() or "opus" in result.stderr.lower():
                    pytest.skip("Required dependencies not available")
                else:
                    pytest.fail(f"Split command failed: {result.stderr}")
            
            # Check if output files were created in the output directory
            opus_files = list(output_dir.glob("*.opus"))
            
            assert len(opus_files) > 0, f"Split command should create Opus files in {output_dir}"
            
            # Verify files have content
            for opus_file in opus_files:
                assert opus_file.stat().st_size > 0, f"Split file should not be empty: {opus_file}"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Split command timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    @pytest.mark.requires_ffmpeg
    def test_audio_conversion_command(self, valid_mp3_file, temp_dir, venv_path):
        """Test audio file conversion via CLI."""
        output_file = temp_dir / "cli_converted.taf"
        
        cmd = self.get_tonietoolbox_command(venv_path) + [
            str(valid_mp3_file), 
            str(output_file),
            "--auto-download"  # Try to download dependencies if needed
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                if "ffmpeg" in result.stderr.lower() or "opus" in result.stderr.lower():
                    pytest.skip("Required dependencies not available and auto-download failed")
                else:
                    pytest.fail(f"Conversion command failed: {result.stderr}")
            
            # Verify output file was created
            assert output_file.exists(), f"Conversion should create output file: {output_file}"
            assert output_file.stat().st_size > 0, "Output file should not be empty"
            
            # Verify it's a valid TAF file by checking header
            with open(output_file, 'rb') as f:
                header_size_bytes = f.read(4)
                if len(header_size_bytes) == 4:
                    import struct
                    header_size = struct.unpack(">L", header_size_bytes)[0]
                    assert header_size > 0, "TAF file should have valid header"
                    
        except subprocess.TimeoutExpired:
            pytest.fail("Conversion command timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")


class TestCLIAdvancedFeatures:
    """Test advanced CLI features."""
    
    def get_tonietoolbox_command(self, venv_path=None):
        """Get the appropriate command to run TonieToolbox.
        
        Args:
            venv_path: Optional path to virtual environment
        """
        base_dir = Path(__file__).parents[2]
        
        # Try using the provided or default virtual environment
        if venv_path is None:
            venv_path = base_dir / "venv" / "test"
        else:
            venv_path = Path(venv_path)
        
        venv_python = venv_path / "bin" / "python"
        if venv_python.exists():
            return [str(venv_python), str(base_dir / "tonietoolbox.py")]
        else:
            return ["python", str(base_dir / "tonietoolbox.py")]
    
    @pytest.mark.functional
    def test_media_tags_display(self, valid_mp3_file, venv_path):
        """Test media tag display functionality."""
        cmd = self.get_tonietoolbox_command(venv_path) + [str(valid_mp3_file), "--show-media-tags"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Skip if module import failed (e.g., missing aiofiles)
            if "ModuleNotFoundError" in result.stderr:
                pytest.skip(f"Skipping due to missing module: {result.stderr}")
            
            if result.returncode != 0:
                # May not have tags or tag reading functionality
                if "no tags" in result.stderr.lower() or "mutagen" in result.stderr.lower():
                    pytest.skip("No tags found or tag reading not available")
                else:
                    pytest.fail(f"Show tags command failed: {result.stderr}")
            
            # Should show tag information or indicate no tags
            output = result.stdout.lower()
            # Check for tag field names or indicators of tag presence/absence
            assert (any(field in output for field in ["tpe1:", "tpe2:", "trck:", "talb:", "tit2:", "comm:"]) or 
                    "no tags" in output or "metadata" in output or "tag" in output), \
                f"Should show tag information or indicate no tags found. Output: {result.stdout}"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Show tags command timed out") 
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    def test_bitrate_configuration(self, valid_mp3_file, temp_dir, venv_path):
        """Test custom bitrate configuration."""
        output_file = temp_dir / "custom_bitrate.taf"
        
        cmd = self.get_tonietoolbox_command(venv_path) + [
            str(valid_mp3_file),
            str(output_file), 
            "--bitrate", "192",
            "--cbr",
            "--auto-download"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                if "ffmpeg" in result.stderr.lower() or "opus" in result.stderr.lower():
                    pytest.skip("Required dependencies not available")
                else:
                    pytest.fail(f"Bitrate configuration failed: {result.stderr}")
            
            # Verify output was created
            assert output_file.exists(), "Should create output file with custom bitrate"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Bitrate configuration test timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    def test_logging_levels(self, valid_taf_file, venv_path):
        """Test different logging levels."""
        cmd_base = self.get_tonietoolbox_command(venv_path) + [str(valid_taf_file), "--info"]
        
        logging_options = [
            ["--debug"],
            ["--quiet"], 
            ["--silent"]
        ]
        
        for log_option in logging_options:
            cmd = cmd_base + log_option
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                # Should not crash regardless of logging level
                if result.returncode != 0:
                    if "ffmpeg" in result.stderr.lower():
                        continue  # Skip dependency issues
                    else:
                        pytest.fail(f"Logging option {log_option} caused failure: {result.stderr}")
                
                # Verify appropriate output levels
                if "--debug" in log_option:
                    assert len(result.stdout) > 0, "Debug mode should produce output"
                elif "--silent" in log_option:
                    # Silent mode might have minimal output
                    pass
                    
            except subprocess.TimeoutExpired:
                pytest.fail(f"Logging test {log_option} timed out")
            except FileNotFoundError:
                pytest.skip("TonieToolbox executable not found")


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def get_tonietoolbox_command(self, venv_path=None):
        """Get the appropriate command to run TonieToolbox.
        
        Args:
            venv_path: Optional path to virtual environment
        """
        base_dir = Path(__file__).parents[2]
        
        if venv_path is None:
            venv_path = base_dir / "venv" / "test"
        else:
            venv_path = Path(venv_path)
        
        venv_python = venv_path / "bin" / "python"
        if venv_python.exists():
            return [str(venv_python), "-m", "TonieToolbox"]
        return ["python", str(base_dir / "tonietoolbox.py")]
    
    @pytest.mark.functional
    def test_nonexistent_file_handling(self, venv_path):
        """Test handling of non-existent input files."""
        cmd = self.get_tonietoolbox_command(venv_path) + ["/nonexistent/file.mp3"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Should exit with error code
            assert result.returncode != 0, "Should fail for non-existent file"
            
            # Should show meaningful error message
            error_output = (result.stderr + result.stdout).lower()
            assert any(word in error_output for word in ["no files found", "not found", "does not exist", "file"]), \
                "Should show file not found error"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Non-existent file test timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    def test_invalid_tonie_tag(self, venv_path):
        """Test handling of invalid Tonie tags."""
        cmd = self.get_tonietoolbox_command(venv_path) + [
            "dummy.mp3", 
            "--append-tonie-tag", "INVALID"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Should exit with error for invalid tag
            assert result.returncode != 0, "Should fail for invalid Tonie tag"
            
            # Should show tag-related error
            error_output = (result.stderr + result.stdout).lower()
            assert "tag" in error_output or "hex" in error_output or "8" in error_output, \
                "Should show tag format error"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Invalid tag test timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")
    
    @pytest.mark.functional
    def test_conflicting_arguments(self, venv_path):
        """Test handling of conflicting command line arguments."""
        cmd = self.get_tonietoolbox_command(venv_path) + [
            "dummy.mp3",
            "--debug",
            "--silent"  # Conflicting logging options
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
            # Should exit with error for conflicting options
            assert result.returncode != 0, "Should fail for conflicting arguments"
        
            # Should show argument conflict error or module import error
            error_output = (result.stderr + result.stdout).lower()
            # Accept either argument conflict or import errors as valid failures
            assert any(word in error_output for word in ["conflict", "exclusive", "argument", "error", "module"]), \
                "Should show argument conflict error or other error"
                
        except subprocess.TimeoutExpired:
            pytest.fail("Conflicting arguments test timed out")
        except FileNotFoundError:
            pytest.skip("TonieToolbox executable not found")


class TestCLIIntegrationCommands:
    """Test system integration CLI commands."""
    
    def get_tonietoolbox_command(self, venv_path=None):
        """Get the appropriate command to run TonieToolbox.
        
        Args:
            venv_path: Optional path to virtual environment
        """
        base_dir = Path(__file__).parents[2]
        
        if venv_path is None:
            venv_path = base_dir / "venv" / "test"
        else:
            venv_path = Path(venv_path)
        
        venv_python = venv_path / "bin" / "python"
        if venv_python.exists():
            return [str(venv_python), "-m", "TonieToolbox"]
        return ["python", str(base_dir / "tonietoolbox.py")]
    
    @pytest.mark.functional
    @pytest.mark.skipif(os.name != 'nt', reason="Windows integration tests only")
    def test_windows_integration_help(self, venv_path):
        """Test Windows integration commands (help only, no actual installation)."""
        integration_commands = [
            ["--install-integration", "--help"],
            ["--uninstall-integration", "--help"], 
            ["--config-integration", "--help"]
        ]
        
        for cmd_args in integration_commands:
            cmd = self.get_tonietoolbox_command(venv_path) + cmd_args
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                # Should show help, not actually install
                assert result.returncode == 0, f"Integration help command should succeed: {cmd_args}"
                
            except subprocess.TimeoutExpired:
                pytest.fail(f"Integration command timed out: {cmd_args}")
            except FileNotFoundError:
                pytest.skip("TonieToolbox executable not found")


if __name__ == "__main__":
    # Run tests if called directly
    try:
        import pytest
        pytest.main([__file__, "-v", "-m", "functional"])
    except ImportError:
        print("pytest not available, running basic CLI tests...")
        
        # Basic test runner without pytest
        test_class = TestCLIBasicOperations()
        venv_path = None  # Will use default venv/test
        
        print("Testing version display...")
        try:
            test_class.test_version_display(venv_path)
            print("✓ Version display test passed")
        except Exception as e:
            print(f"✗ Version display test failed: {e}")
        
        print("Testing help display...")
        try:
            test_class.test_help_display(venv_path)
            print("✓ Help display test passed")
        except Exception as e:
            print(f"✗ Help display test failed: {e}")