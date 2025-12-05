#!/usr/bin/python3
"""
Base classes for tonies data handling.
Provides abstract interfaces for format handlers, converters, and operations.
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple
from ..utils import get_logger


class BaseFormatHandler(ABC):
    """Abstract base class for tonies JSON format handlers."""
    
    def __init__(self, repository=None):
        """
        Initialize the format handler.
        
        Args:
            repository: TeddyCloud repository interface (ITeddyCloudRepository)
                       for server operations. Can be None for offline mode.
        """
        self.repository = repository
        self.custom_json = []
        self.is_loaded = False
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def load_from_server(self) -> bool:
        """Load data from TeddyCloud server."""
        pass
    
    @abstractmethod 
    def load_from_file(self, file_path: str) -> bool:
        """Load data from local file."""
        pass
    
    @abstractmethod
    def save_to_file(self, file_path: str) -> bool:
        """Save data to local file."""
        pass
    
    @abstractmethod
    def add_entry_from_taf(self, taf_file: str, input_files: List[str], 
                          artwork_url: Optional[str] = None) -> bool:
        """Add entry from TAF file."""
        pass
    
    @abstractmethod
    def find_entry_by_hash(self, taf_hash: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Find entry by hash value."""
        pass
    
    @abstractmethod
    def find_entry_by_series_episodes(self, series: str, episodes: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Find entry by series and episodes."""
        pass


class BaseConverter(ABC):
    """
    Abstract base class for format converters.
    
    Defines the interface for converting tonies.custom.json data between different
    format versions (V1 ↔ V2). Implementations handle schema transformations,
    field mapping, and data migration while preserving metadata integrity.
    
    Example:
        >>> from TonieToolbox.core.tonies_data.formats import ToniesJsonV1Handler, ToniesJsonV2Handler
        >>> from TonieToolbox.core.tonies_data.formats.converters import V1ToV2Converter
        >>> 
        >>> # Load V1 format data
        >>> v1_handler = ToniesJsonV1Handler()
        >>> v1_handler.load_from_file('tonies.v1.json')
        >>> 
        >>> # Convert V1 to V2
        >>> converter = V1ToV2Converter()
        >>> v2_data = converter.convert(v1_handler.custom_json)
        >>> 
        >>> # Save as V2 format
        >>> v2_handler = ToniesJsonV2Handler()
        >>> v2_handler.custom_json = v2_data
        >>> v2_handler.save_to_file('tonies.v2.json')
        >>> 
        >>> print(f"Converted {len(v2_data)} entries from V1 to V2")
        Converted 42 entries from V1 to V2
    """
    
    def __init__(self):
        """Initialize the converter."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def convert(self, source_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert data from one format to another."""
        pass