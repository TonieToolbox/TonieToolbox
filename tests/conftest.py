"""
Pytest configuration and shared fixtures for TonieToolbox tests.

This module provides:
- Test data fixtures
- Common test utilities
- Pytest configuration
- Shared mock objects
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
import pytest


# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_AUDIO_MP3 = TEST_DATA_DIR / "test_audio.mp3"
TEST_AUDIO_TAF = TEST_DATA_DIR / "test_audio.taf"
TEST_AUDIO_MONO_MP3 = TEST_DATA_DIR / "test_audio_mono.mp3"
TEST_AUDIO_MONO_TAF = TEST_DATA_DIR / "test_audio_mono.taf"
TEST_COVER_JPEG = TEST_DATA_DIR / "cover.jpeg"


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Provide path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def sample_audio_files() -> Dict[str, Path]:
    """Provide paths to all sample audio files."""
    return {
        "mp3_stereo": TEST_AUDIO_MP3,
        "taf_stereo": TEST_AUDIO_TAF,
        "mp3_mono": TEST_AUDIO_MONO_MP3,
        "taf_mono": TEST_AUDIO_MONO_TAF,
        "cover_image": TEST_COVER_JPEG
    }


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Provide a temporary output directory that mimics the app's output structure."""
    with tempfile.TemporaryDirectory() as temp_path:
        output_dir = Path(temp_path) / "output"
        output_dir.mkdir()
        yield output_dir


@pytest.fixture
def sample_list_file(temp_dir: Path, sample_audio_files: Dict[str, Path]) -> Path:
    """Create a sample .lst file with audio file paths."""
    list_file = temp_dir / "test_playlist.lst"
    
    with open(list_file, 'w') as f:
        f.write(f"{sample_audio_files['mp3_stereo']}\n")
        f.write(f"{sample_audio_files['mp3_mono']}\n")
    
    return list_file

@pytest.fixture
def sample_list_file_comment(temp_dir: Path, sample_audio_files: Dict[str, Path]) -> Path:
    """Create a sample .lst file with audio file paths and comments for filename parsing tests."""
    list_file = temp_dir / "test_playlist_comment.lst"
    
    with open(list_file, 'w') as f:
        f.write(f"{sample_audio_files['mp3_stereo']}\n")
        f.write(f"{sample_audio_files['mp3_mono']}\n")
        f.write("# This is a comment line\n")
        f.write("# Another comment line\n")
        f.write("# Filename: FancyCommentFile \n")
    return list_file


@pytest.fixture
def mock_audio_directory(temp_dir: Path, sample_audio_files: Dict[str, Path]) -> Path:
    """
    Create a mock directory structure with audio files for recursive testing.
    
    Structure (4 levels deep for --max-depth testing):
    audio_collection/
        single_file.mp3                      # Depth 0 - file in root
        Album 1/                             # Depth 1
            track1.mp3
            track2.mp3
            track3.mp3
            cover.jpg
        Album 2/                             # Depth 1
            track1.mp3
            track2.mp3
            Bonus/                           # Depth 2
                bonus_track.mp3
                hidden.mp3
        Artist/                              # Depth 1
            2023 - New Album/                # Depth 2
                01_intro.mp3
                02_main.mp3
                Deluxe Edition/              # Depth 3
                    bonus1.mp3
                    bonus2.mp3
                    Remixes/                 # Depth 4
                        remix1.mp3
        Podcasts/                            # Depth 1
            Episode 1/                       # Depth 2
                part1.mp3
            Episode 2/                       # Depth 2
                part1.mp3
                part2.mp3
    """
    audio_dir = temp_dir / "audio_collection"
    audio_dir.mkdir()
    
    # Root level file (depth 0)
    shutil.copy2(sample_audio_files['mp3_stereo'], audio_dir / "single_file.mp3")
    
    # Depth 1: Album 1
    album1 = audio_dir / "Album 1"
    album1.mkdir()
    shutil.copy2(sample_audio_files['mp3_stereo'], album1 / "track1.mp3")
    shutil.copy2(sample_audio_files['mp3_stereo'], album1 / "track2.mp3")
    shutil.copy2(sample_audio_files['mp3_stereo'], album1 / "track3.mp3")
    shutil.copy2(sample_audio_files['cover_image'], album1 / "cover.jpg")
    
    # Depth 1-2: Album 2 with Bonus subfolder
    album2 = audio_dir / "Album 2"
    album2.mkdir()
    shutil.copy2(sample_audio_files['mp3_mono'], album2 / "track1.mp3")
    shutil.copy2(sample_audio_files['mp3_stereo'], album2 / "track2.mp3")
    
    album2_bonus = album2 / "Bonus"
    album2_bonus.mkdir()
    shutil.copy2(sample_audio_files['mp3_stereo'], album2_bonus / "bonus_track.mp3")
    shutil.copy2(sample_audio_files['mp3_mono'], album2_bonus / "hidden.mp3")
    
    # Depth 1-4: Artist folder with deep nesting
    artist = audio_dir / "Artist"
    artist.mkdir()
    
    artist_album = artist / "2023 - New Album"
    artist_album.mkdir()
    shutil.copy2(sample_audio_files['mp3_stereo'], artist_album / "01_intro.mp3")
    shutil.copy2(sample_audio_files['mp3_stereo'], artist_album / "02_main.mp3")
    
    deluxe = artist_album / "Deluxe Edition"
    deluxe.mkdir()
    shutil.copy2(sample_audio_files['mp3_mono'], deluxe / "bonus1.mp3")
    shutil.copy2(sample_audio_files['mp3_stereo'], deluxe / "bonus2.mp3")
    
    remixes = deluxe / "Remixes"
    remixes.mkdir()
    shutil.copy2(sample_audio_files['mp3_stereo'], remixes / "remix1.mp3")
    
    # Depth 1-2: Podcasts folder
    podcasts = audio_dir / "Podcasts"
    podcasts.mkdir()
    
    episode1 = podcasts / "Episode 1"
    episode1.mkdir()
    shutil.copy2(sample_audio_files['mp3_mono'], episode1 / "part1.mp3")
    
    episode2 = podcasts / "Episode 2"
    episode2.mkdir()
    shutil.copy2(sample_audio_files['mp3_mono'], episode2 / "part1.mp3")
    shutil.copy2(sample_audio_files['mp3_stereo'], episode2 / "part2.mp3")
    
    return audio_dir


@pytest.fixture
def valid_taf_file() -> Path:
    """Provide path to a valid TAF file for testing."""
    return TEST_AUDIO_TAF


@pytest.fixture
def valid_mp3_file() -> Path:
    """Provide path to a valid MP3 file for testing."""
    return TEST_AUDIO_MP3


class MockTeddyCloudServer:
    """Mock TeddyCloud server for testing upload functionality."""
    
    def __init__(self):
        self.uploaded_files = []
        self.available_tags = ["tag1", "tag2", "tag3"]
        self.auth_required = False
        
    def upload_file(self, file_path: str, **kwargs) -> bool:
        """Mock file upload."""
        self.uploaded_files.append(file_path)
        return True
        
    def get_tags(self) -> list:
        """Mock tag retrieval."""
        return self.available_tags


@pytest.fixture
def mock_teddycloud_server():
    """Provide a mock TeddyCloud server for testing."""
    return MockTeddyCloudServer()


# Test configuration
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--venv-path",
        action="store",
        default=None,
        help="Path to virtual environment (e.g., venv/test or venv/py312)"
    )


@pytest.fixture(scope="session")
def venv_path(request) -> Path:
    """Provide path to virtual environment for tests.
    
    Can be overridden via --venv-path command line option.
    Defaults to venv/test.
    """
    custom_path = request.config.getoption("--venv-path")
    if custom_path:
        return Path(custom_path)
    
    # Default to venv/test
    base_dir = Path(__file__).parents[1]
    return base_dir / "venv" / "test"


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slower, with dependencies)"
    )
    config.addinivalue_line(
        "markers", "functional: marks tests as functional tests (end-to-end)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_ffmpeg: marks tests that require FFmpeg"
    )
    config.addinivalue_line(
        "markers", "requires_opus: marks tests that require Opus tools"
    )
    config.addinivalue_line(
        "markers", "requires_gui: marks tests that require GUI/tkinter"
    )


# Skip conditions for optional dependencies
def skip_if_no_ffmpeg():
    """Skip test if FFmpeg is not available."""
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True

def skip_if_no_gui():
    """Skip test if GUI (tkinter) is not available."""
    try:
        import tkinter
        return False
    except ImportError:
        return True