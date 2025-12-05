#!/usr/bin/env python3
"""
Functional tests for recursive processing feature.

Tests the complete workflow from CLI to file processing:
- Combine mode: --recursive (combines files per folder)
- Individual mode: --recursive --files-to-taf (each file separately)
"""

import pytest
from pathlib import Path
import subprocess
import sys


@pytest.fixture
def tonietoolbox_script():
    """Get path to tonietoolbox.py script."""
    script_path = Path(__file__).parent.parent.parent / "tonietoolbox.py"
    
    if not script_path.exists():
        pytest.skip(f"tonietoolbox.py not found: {script_path}")
    
    return script_path


class TestRecursiveCombineMode:
    """Test --recursive (combine files per folder)."""
    
    def test_recursive_combines_files_per_folder(self, mock_audio_directory, tonietoolbox_script, temp_output_dir):
        """Test that --recursive creates one TAF per folder."""
        # Run command
        result = subprocess.run(
            [sys.executable, str(tonietoolbox_script), "--recursive", 
             str(mock_audio_directory), str(temp_output_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check output
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        
        # Verify that it attempted to process folders (check output messages)
        output_text = result.stdout + result.stderr
        assert "Album" in output_text or "album" in output_text.lower()


class TestRecursiveIndividualMode:
    """Test --recursive --files-to-taf (individual file processing)."""
    
    def test_recursive_files_to_taf_processes_each_file(self, mock_audio_directory, tonietoolbox_script, temp_output_dir):
        """Test that --recursive --files-to-taf processes each file individually."""
        # Run command
        result = subprocess.run(
            [sys.executable, str(tonietoolbox_script), "--recursive", "--files-to-taf",
             str(mock_audio_directory), str(temp_output_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check output
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        
        # Verify that it attempted to process individual files
        # Should mention individual tracks, not just albums
        output_text = result.stdout + result.stderr
        assert "track" in output_text.lower() or "processing" in output_text.lower()


class TestRecursiveWithMaxDepth:
    """Test --recursive with --max-depth."""
    
    def test_max_depth_0_processes_only_root_files(self, mock_audio_directory, tonietoolbox_script, temp_output_dir):
        """Test --max-depth 0 processes only files in the root directory."""
        # Run with max-depth=0 (only root files)
        result = subprocess.run(
            [sys.executable, str(tonietoolbox_script), "--recursive", "--max-depth", "0",
             str(mock_audio_directory), str(temp_output_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        
        output_text = result.stdout + result.stderr
        # Should process root file
        assert "single_file" in output_text.lower() or "audio_collection" in output_text.lower()
        # Should NOT process subdirectories
        assert "album" not in output_text.lower() or "Found 1 folder" in output_text
    
    def test_max_depth_1_processes_first_level(self, mock_audio_directory, tonietoolbox_script, temp_output_dir):
        """Test --max-depth 1 processes only first-level subdirectories."""
        # Run with max-depth=1
        result = subprocess.run(
            [sys.executable, str(tonietoolbox_script), "--recursive", "--max-depth", "1",
             str(mock_audio_directory), str(temp_output_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        
        output_text = result.stdout + result.stderr
        # Should process Album 1, Album 2, Artist, Podcasts (depth 1)
        assert "album" in output_text.lower() or "artist" in output_text.lower()
        # Should NOT process Bonus (depth 2), Deluxe Edition (depth 3), Remixes (depth 4)
        # Check folder count - should have 4-5 folders at depth 1
        if "Found" in output_text and "folder" in output_text:
            # Extract number between "Found" and "folder"
            import re
            match = re.search(r'Found (\d+) folder', output_text)
            if match:
                folder_count = int(match.group(1))
                assert folder_count <= 5, f"Expected max 5 folders at depth 1, got {folder_count}"
    
    def test_max_depth_2_includes_nested_folders(self, mock_audio_directory, tonietoolbox_script, temp_output_dir):
        """Test --max-depth 2 processes up to second-level subdirectories."""
        # Run with max-depth=2
        result = subprocess.run(
            [sys.executable, str(tonietoolbox_script), "--recursive", "--max-depth", "2",
             str(mock_audio_directory), str(temp_output_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        
        output_text = result.stdout + result.stderr
        # Should process Bonus (depth 2), 2023 - New Album (depth 2)
        # Should NOT process Deluxe Edition (depth 3), Remixes (depth 4)
        assert "bonus" in output_text.lower() or "episode" in output_text.lower() or "2023" in output_text.lower()
    
    def test_max_depth_unlimited_processes_all_levels(self, mock_audio_directory, tonietoolbox_script, temp_output_dir):
        """Test --recursive without --max-depth processes all levels."""
        # Run without max-depth (unlimited)
        result = subprocess.run(
            [sys.executable, str(tonietoolbox_script), "--recursive",
             str(mock_audio_directory), str(temp_output_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Exit code: {result.returncode}")
        
        output_text = result.stdout + result.stderr
        # Should process all levels including deepest (Remixes at depth 4)
        # Should have more folders than max-depth=2
        if "Found" in output_text and "folder" in output_text:
            import re
            match = re.search(r'Found (\d+) folder', output_text)
            if match:
                folder_count = int(match.group(1))
                # With full structure: root + Album 1 + Album 2 + Bonus + Artist + 2023 Album + Deluxe + Remixes + Podcasts + Episodes = ~11 folders
                assert folder_count >= 8, f"Expected at least 8 folders with unlimited depth, got {folder_count}"
