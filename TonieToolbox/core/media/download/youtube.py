#!/usr/bin/python3
"""
YouTube audio download support via yt-dlp.

Allows list files (.lst) to contain YouTube URLs next to local file paths.
The referenced videos are downloaded as audio-only files using yt-dlp so
they can be converted like any other input file.

yt-dlp is an optional dependency. It is used either as Python module
(``pip install yt-dlp``) or as ``yt-dlp`` executable found in PATH.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

from ...utils import get_logger

logger = get_logger(__name__)

_YOUTUBE_URL_RE = re.compile(
    r'^https?://'
    r'(?:(?:www|m|music)\.)?'
    r'(?:youtube\.com/(?:watch\?|shorts/|live/|playlist\?|embed/)|youtu\.be/)'
    r'\S+$',
    re.IGNORECASE,
)

# Audio format the downloaded streams are extracted to. Opus is what YouTube
# usually serves, so in most cases this is a lossless remux, and .opus is a
# supported input format of the conversion pipeline.
DOWNLOAD_AUDIO_FORMAT = 'opus'


class YouTubeDownloadError(RuntimeError):
    """Raised when a YouTube URL could not be downloaded."""


def is_youtube_url(value: str) -> bool:
    """
    Check whether the given string is a YouTube URL.

    Args:
        value: String to check (e.g. a line of a list file)

    Returns:
        True if the string is a YouTube video, shorts, live or playlist URL
    """
    return bool(_YOUTUBE_URL_RE.match(value.strip()))


def is_youtube_playlist_url(url: str) -> bool:
    """
    Check whether the URL should be downloaded as a whole playlist.

    This is the case for playlist URLs and for video URLs carrying a ``list``
    parameter, except for auto-generated YouTube Mixes (list IDs starting
    with ``RD``), which are endless radio-like lists.
    """
    parsed = urlparse(url.strip())
    list_ids = parse_qs(parsed.query).get('list', [])
    if not list_ids or not list_ids[0]:
        return False
    return not list_ids[0].startswith('RD')


# yt-dlp needs a JavaScript runtime for most YouTube videos. Only deno is
# enabled by default, so other installed runtimes are enabled explicitly.
_JS_RUNTIMES = ('deno', 'node', 'bun', 'quickjs')


def find_js_runtime() -> Optional[str]:
    """Find an installed JavaScript runtime usable by yt-dlp."""
    for runtime in _JS_RUNTIMES:
        executable = 'qjs' if runtime == 'quickjs' else runtime
        if shutil.which(executable):
            return runtime
    return None


def find_yt_dlp_command() -> Optional[List[str]]:
    """
    Find a way to run yt-dlp.

    Returns:
        Command prefix to invoke yt-dlp, or None if yt-dlp is not available
    """
    executable = shutil.which('yt-dlp')
    if executable:
        return [executable]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, '-m', 'yt_dlp']
    except ImportError:
        return None


class YouTubeDownloader:
    """Downloads the audio track of YouTube videos using yt-dlp."""

    def __init__(self, ffmpeg_path: Optional[str] = None,
                 yt_dlp_command: Optional[List[str]] = None):
        """
        Initialize the downloader.

        Args:
            ffmpeg_path: Path to the ffmpeg binary used by yt-dlp for audio extraction
            yt_dlp_command: Command prefix to run yt-dlp (auto-detected if omitted)
        """
        self.ffmpeg_path = ffmpeg_path
        self._yt_dlp_command = yt_dlp_command
        self._js_runtime_args: Optional[List[str]] = None

    @property
    def js_runtime_args(self) -> List[str]:
        """Arguments enabling a non-default JavaScript runtime, if needed and supported."""
        if self._js_runtime_args is None:
            self._js_runtime_args = []
            runtime = find_js_runtime()
            if runtime and runtime != 'deno' and self._supports_option('--js-runtimes'):
                self._js_runtime_args = ['--js-runtimes', runtime]
        return self._js_runtime_args

    def _supports_option(self, option: str) -> bool:
        """Check whether the installed yt-dlp supports the given command line option."""
        try:
            completed = subprocess.run(self.yt_dlp_command + ['--help'],
                                       capture_output=True, text=True, check=False)
        except OSError:
            return False
        return option in completed.stdout

    @property
    def yt_dlp_command(self) -> List[str]:
        if self._yt_dlp_command is None:
            command = find_yt_dlp_command()
            if command is None:
                raise YouTubeDownloadError(
                    "yt-dlp is required to download YouTube URLs but was not found. "
                    "Install it with 'pip install yt-dlp' or make the 'yt-dlp' executable available in PATH."
                )
            self._yt_dlp_command = command
        return self._yt_dlp_command

    def build_command(self, url: str, target_dir: Path) -> List[str]:
        """Build the yt-dlp command line for downloading the given URL."""
        if is_youtube_playlist_url(url):
            output_template = '%(playlist_index)03d - %(title)s [%(id)s].%(ext)s'
            # Skip unavailable/private entries instead of failing the whole playlist
            playlist_args = ['--yes-playlist', '--ignore-errors']
        else:
            output_template = '%(title)s [%(id)s].%(ext)s'
            playlist_args = ['--no-playlist']

        command = list(self.yt_dlp_command) + [
            '--format', 'bestaudio/best',
            '--extract-audio',
            '--audio-format', DOWNLOAD_AUDIO_FORMAT,
            '--embed-metadata',
            '--no-progress',
            '--no-overwrites',
            '--restrict-filenames',
            '--paths', str(target_dir),
            '--output', output_template,
            '--print', 'after_move:filepath',
            *playlist_args,
            *self.js_runtime_args,
        ]
        if self.ffmpeg_path:
            command += ['--ffmpeg-location', str(self.ffmpeg_path)]
        command += ['--', url]
        return command

    def download(self, url: str, target_dir: Path) -> List[Path]:
        """
        Download the audio of a YouTube video or playlist.

        Args:
            url: YouTube URL
            target_dir: Directory to store the downloaded audio file(s) in

        Returns:
            Downloaded audio files, in playlist order

        Raises:
            YouTubeDownloadError: If yt-dlp is missing or the download fails
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        command = self.build_command(url, target_dir)

        logger.info("Downloading YouTube audio: %s", url)
        logger.debug("Running yt-dlp: %s", ' '.join(command))

        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as e:
            raise YouTubeDownloadError(f"Failed to run yt-dlp: {e}") from e

        files = []
        for line in completed.stdout.splitlines():
            path = Path(line.strip())
            if line.strip() and path.is_file() and path not in files:
                files.append(path)

        errors = [l for l in (completed.stderr or '').splitlines() if l.startswith('ERROR')]
        if completed.returncode != 0:
            reason = errors[-1] if errors else f"exit code {completed.returncode}"
            if not (files and is_youtube_playlist_url(url)):
                raise YouTubeDownloadError(f"yt-dlp failed to download {url}: {reason}")
            # Playlist with some unavailable entries: keep what could be downloaded
            for error in errors:
                logger.warning("Skipped playlist entry: %s", error)

        if not files:
            raise YouTubeDownloadError(f"yt-dlp did not produce any audio file for {url}")

        logger.info("Downloaded %d audio file(s) from %s", len(files), url)
        return files
