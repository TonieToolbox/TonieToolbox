#!/usr/bin/python3
"""
Media Tags Infrastructure Layer.

This module contains concrete implementations for media tag reading and artwork extraction.
Uses Mutagen library for parsing various audio formats and implements domain-defined interfaces.
Provides file system services and cover image detection across multiple audio file formats.
"""
from .mutagen_reader import MutagenTagReader, MutagenTagReaderFactory
from .mutagen_artwork import MutagenArtworkExtractor
from .filesystem import StandardFileSystemService, StandardCoverImageFinder

__all__ = [
    'MutagenTagReader',
    'MutagenTagReaderFactory', 
    'MutagenArtworkExtractor',
    'StandardFileSystemService',
    'StandardCoverImageFinder'
]