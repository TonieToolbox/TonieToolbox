#!/usr/bin/env python3
"""
File information cache for playlist management.

Provides in-memory caching of TAF file analysis results to improve
performance when working with large playlists by avoiding redundant
disk I/O and file parsing operations.
"""

from typing import Dict, Optional, List, TYPE_CHECKING, Any
from pathlib import Path
import time

if TYPE_CHECKING:
    from ...analysis.models import TafAnalysisResult

from ...utils import get_logger

logger = get_logger(__name__)


class PlaylistFileCache:
    """
    In-memory LRU cache for TAF file analysis results.
    
    Caches file analysis results to avoid redundant file parsing when:
    - Loading files into playlist
    - Reordering playlist items
    - Displaying file information
    - Switching between tracks
    
    Uses Least Recently Used (LRU) eviction policy to manage memory usage.
    
    Example:
        cache = PlaylistFileCache(max_size=100)
        
        # Check cache before analyzing
        result = cache.get(file_path)
        if not result:
            result = analyze_taf_file(file_path)
            cache.put(file_path, result)
        
        # Use cached result
        duration = result.audio_analysis.duration_seconds
    
    Attributes:
        max_size: Maximum number of cached entries (default: 100)
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the file cache.
        
        Args:
            max_size: Maximum number of files to cache (default: 100)
        """
        self._cache: Dict[str, 'TafAnalysisResult'] = {}
        self._max_size = max_size
        self._access_order: List[str] = []  # LRU tracking
        self._access_times: Dict[str, float] = {}
        self._hit_count = 0
        self._miss_count = 0
        
        logger.debug(f"PlaylistFileCache initialized with max_size={max_size}")
    
    def get(self, file_path: Path) -> Optional['TafAnalysisResult']:
        """
        Get cached analysis result for a file.
        
        Updates access time for LRU eviction policy.
        
        Args:
            file_path: Path to the TAF file
            
        Returns:
            Cached TafAnalysisResult if available, None otherwise
        """
        key = str(file_path.resolve())
        
        if key in self._cache:
            # Update LRU tracking
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            self._access_times[key] = time.time()
            
            self._hit_count += 1
            logger.debug(f"Cache HIT for {file_path.name} (hit_rate: {self.hit_rate:.1%})")
            return self._cache[key]
        
        self._miss_count += 1
        logger.debug(f"Cache MISS for {file_path.name} (hit_rate: {self.hit_rate:.1%})")
        return None
    
    def put(self, file_path: Path, result: 'TafAnalysisResult') -> None:
        """
        Cache an analysis result for a file.
        
        Evicts least recently used entry if cache is full.
        
        Args:
            file_path: Path to the TAF file
            result: Analysis result to cache
        """
        key = str(file_path.resolve())
        
        # Evict oldest entry if cache is full and this is a new entry
        if len(self._cache) >= self._max_size and key not in self._cache:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
                if oldest_key in self._access_times:
                    del self._access_times[oldest_key]
                logger.debug(f"Evicted LRU entry: {Path(oldest_key).name}")
        
        # Add or update cache entry
        self._cache[key] = result
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        self._access_times[key] = time.time()
        
        logger.debug(f"Cached analysis for {file_path.name} (cache_size: {len(self._cache)}/{self._max_size})")
    
    def invalidate(self, file_path: Path) -> None:
        """
        Remove a file from the cache.
        
        Use when file has been modified and cached data is stale.
        
        Args:
            file_path: Path to the TAF file to invalidate
        """
        key = str(file_path.resolve())
        
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            if key in self._access_times:
                del self._access_times[key]
            logger.debug(f"Invalidated cache entry: {file_path.name}")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        cache_size = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        self._access_times.clear()
        self._hit_count = 0
        self._miss_count = 0
        logger.debug(f"Cache cleared ({cache_size} entries removed)")
    
    @property
    def size(self) -> int:
        """Get current number of cached entries."""
        return len(self._cache)
    
    @property
    def hit_rate(self) -> float:
        """
        Get cache hit rate.
        
        Returns:
            Hit rate as a value between 0.0 and 1.0
        """
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return self._hit_count / total
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache performance metrics
        """
        return {
            'size': self.size,
            'max_size': self._max_size,
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'hit_rate': self.hit_rate,
            'total_requests': self._hit_count + self._miss_count
        }
