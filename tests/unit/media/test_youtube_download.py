#!/usr/bin/env python3
"""
Unit tests for YouTube URL support in list files (.lst).
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from TonieToolbox.core.media.download import (
    YouTubeDownloader,
    YouTubeDownloadError,
    is_youtube_url,
    is_youtube_playlist_url,
)
from TonieToolbox.core.processing.domain import InputSpecification
from TonieToolbox.core.processing.domain.value_objects.input_specification import InputType
from TonieToolbox.core.processing.interface.adapters.files_to_taf_adapter import FilesToTafAdapter


@pytest.mark.unit
class TestYouTubeUrlDetection:

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "http://youtube.com/watch?v=jNQXAC9IVRw&t=10",
        "https://m.youtube.com/watch?v=jNQXAC9IVRw",
        "https://music.youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtu.be/jNQXAC9IVRw",
        "https://www.youtube.com/shorts/abcdefghijk",
        "https://www.youtube.com/playlist?list=PL1234567890",
        "  https://youtu.be/jNQXAC9IVRw  ",
    ])
    def test_detects_youtube_urls(self, url):
        assert is_youtube_url(url)

    @pytest.mark.parametrize("value", [
        "song.mp3",
        "/music/youtube.com/watch.mp3",
        "C:\\music\\track.mp3",
        "https://example.com/watch?v=jNQXAC9IVRw",
        "https://www.youtube.com/",
        "https://notyoutube.com/watch?v=x",
    ])
    def test_ignores_non_youtube_entries(self, value):
        assert not is_youtube_url(value)

    @pytest.mark.parametrize("url, expected", [
        ("https://www.youtube.com/playlist?list=PL123", True),
        ("https://www.youtube.com/watch?v=abc&list=PL123", True),
        ("https://www.youtube.com/watch?v=abc&list=RDabc&start_radio=1", False),
        ("https://www.youtube.com/watch?v=abc", False),
        ("https://youtu.be/abc", False),
    ])
    def test_playlist_detection(self, url, expected):
        assert is_youtube_playlist_url(url) is expected


@pytest.mark.unit
class TestYouTubeDownloader:

    @pytest.fixture(autouse=True)
    def no_js_runtime(self):
        with patch("TonieToolbox.core.media.download.youtube.find_js_runtime", return_value=None):
            yield

    def test_build_command_enables_node_runtime(self, tmp_path):
        downloader = YouTubeDownloader(yt_dlp_command=["yt-dlp"])
        with patch("TonieToolbox.core.media.download.youtube.find_js_runtime", return_value="node"), \
             patch.object(YouTubeDownloader, "_supports_option", return_value=True):
            command = downloader.build_command("https://youtu.be/abc", tmp_path)
        assert command[command.index("--js-runtimes") + 1] == "node"

    def test_playlist_with_unavailable_entries_keeps_downloaded_files(self, tmp_path):
        first = tmp_path / "001 - a.opus"
        first.write_bytes(b"x")
        completed = subprocess.CompletedProcess(
            [], 1, stdout=f"{first}\n", stderr="ERROR: [youtube] xyz: Video unavailable\n")

        downloader = YouTubeDownloader(yt_dlp_command=["yt-dlp"])
        with patch("subprocess.run", return_value=completed):
            files = downloader.download("https://www.youtube.com/playlist?list=PL1", tmp_path)

        assert files == [first]

    def test_build_command_single_video(self, tmp_path):
        downloader = YouTubeDownloader(ffmpeg_path="/opt/ffmpeg", yt_dlp_command=["yt-dlp"])
        command = downloader.build_command("https://youtu.be/abc", tmp_path)

        assert command[0] == "yt-dlp"
        assert "--no-playlist" in command
        assert command[command.index("--ffmpeg-location") + 1] == "/opt/ffmpeg"
        assert command[command.index("--paths") + 1] == str(tmp_path)
        assert command[-2:] == ["--", "https://youtu.be/abc"]

    def test_build_command_playlist(self, tmp_path):
        downloader = YouTubeDownloader(yt_dlp_command=["yt-dlp"])
        command = downloader.build_command("https://www.youtube.com/playlist?list=PL1", tmp_path)

        assert "--yes-playlist" in command
        assert "--ffmpeg-location" not in command

    def test_download_returns_printed_files(self, tmp_path):
        first = tmp_path / "001 - a.opus"
        second = tmp_path / "002 - b.opus"
        first.write_bytes(b"x")
        second.write_bytes(b"x")
        completed = subprocess.CompletedProcess([], 0, stdout=f"{first}\n{second}\n", stderr="")

        downloader = YouTubeDownloader(yt_dlp_command=["yt-dlp"])
        with patch("subprocess.run", return_value=completed):
            files = downloader.download("https://www.youtube.com/playlist?list=PL1", tmp_path)

        assert files == [first, second]

    def test_download_failure_raises(self, tmp_path):
        completed = subprocess.CompletedProcess([], 1, stdout="", stderr="ERROR: Video unavailable\n")

        downloader = YouTubeDownloader(yt_dlp_command=["yt-dlp"])
        with patch("subprocess.run", return_value=completed):
            with pytest.raises(YouTubeDownloadError, match="Video unavailable"):
                downloader.download("https://youtu.be/abc", tmp_path)

    def test_missing_yt_dlp_raises(self, tmp_path):
        downloader = YouTubeDownloader()
        with patch("TonieToolbox.core.media.download.youtube.find_yt_dlp_command", return_value=None):
            with pytest.raises(YouTubeDownloadError, match="yt-dlp is required"):
                downloader.download("https://youtu.be/abc", tmp_path)


@pytest.mark.unit
class TestFileListInputSpecification:

    def test_file_list_keeps_order(self, tmp_path):
        b = tmp_path / "b.mp3"
        a = tmp_path / "a.mp3"
        b.write_bytes(b"x")
        a.write_bytes(b"x")

        spec = InputSpecification.for_file_list([b, a], source_path=str(tmp_path / "list.lst"))

        assert spec.input_type == InputType.FILE_LIST
        assert spec.resolve_files() == [b, a]


@pytest.mark.unit
class TestListFileWithYouTubeUrls:

    @pytest.fixture
    def adapter(self):
        return FilesToTafAdapter(Mock(), Mock())

    def test_list_file_mixes_local_files_and_downloads(self, adapter, tmp_path):
        local_a = tmp_path / "a.mp3"
        local_b = tmp_path / "b.mp3"
        local_a.write_bytes(b"x")
        local_b.write_bytes(b"x")
        list_file = tmp_path / "playlist.lst"
        list_file.write_text(
            "# my playlist\n"
            "b.mp3\n"
            "https://www.youtube.com/watch?v=jNQXAC9IVRw\n"
            f"\"{local_a}\"\n",
            encoding="utf-8",
        )
        downloaded = tmp_path / "video.opus"

        with patch.object(YouTubeDownloader, "download", return_value=[downloaded]) as download:
            files = adapter._discover_input_files({
                "input_pattern": str(list_file),
                "ffmpeg_path": "/usr/bin/ffmpeg",
            })

        assert files == [local_b, downloaded, local_a]
        download.assert_called_once()
        assert download.call_args.args[0] == "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        adapter._cleanup_downloads()

    def test_download_dir_is_cleaned_up(self, adapter):
        download_dir = adapter._create_download_dir()
        assert download_dir.is_dir()

        adapter._cleanup_downloads()

        assert not download_dir.exists()

    def test_download_dir_is_kept_with_keep_temp(self, adapter):
        download_dir = adapter._create_download_dir()

        adapter._cleanup_downloads(keep=True)

        assert download_dir.is_dir()
        download_dir.rmdir()

    def test_download_error_fails_processing(self, adapter, tmp_path):
        list_file = tmp_path / "playlist.lst"
        list_file.write_text("https://youtu.be/jNQXAC9IVRw\n", encoding="utf-8")

        with patch.object(YouTubeDownloader, "download", side_effect=YouTubeDownloadError("boom")):
            result = adapter.execute({
                "input_pattern": str(list_file),
                "output_path": str(tmp_path / "out.taf"),
            })

        assert result == 1
        adapter.processing_service.execute_operation.assert_not_called()
