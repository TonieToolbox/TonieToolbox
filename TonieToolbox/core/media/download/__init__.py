#!/usr/bin/python3
"""
Download support for remote media sources (e.g. YouTube URLs in list files).
"""
from .youtube import (
    YouTubeDownloader,
    YouTubeDownloadError,
    find_yt_dlp_command,
    is_youtube_url,
    is_youtube_playlist_url,
)

__all__ = [
    'YouTubeDownloader',
    'YouTubeDownloadError',
    'find_yt_dlp_command',
    'is_youtube_url',
    'is_youtube_playlist_url',
]
