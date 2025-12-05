#!/usr/bin/env python3
"""
Processing options value object.

This module defines the ProcessingOptions value object that encapsulates
all configuration options for processing operations.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum, auto


class QualityLevel(Enum):
    """Audio quality levels for processing."""
    
    LOW = auto()        # Fast processing, lower quality
    MEDIUM = auto()     # Balanced processing
    HIGH = auto()       # Slower processing, higher quality
    LOSSLESS = auto()   # Highest quality, largest files


class CompressionMode(Enum):
    """Compression modes for output files."""
    
    NONE = auto()       # No compression
    FAST = auto()       # Fast compression
    OPTIMAL = auto()    # Optimal compression (default)
    MAXIMUM = auto()    # Maximum compression


@dataclass(frozen=True)
class ProcessingOptions:
    """Value object containing all processing configuration options."""
    
    # Audio processing options
    quality_level: QualityLevel = QualityLevel.MEDIUM
    compression_mode: CompressionMode = CompressionMode.OPTIMAL
    normalize_audio: bool = False
    fade_in_duration: float = 0.0
    fade_out_duration: float = 0.0
    
    # File handling options
    preserve_timestamps: bool = True
    preserve_metadata: bool = True
    create_backup: bool = False
    cleanup_temp_files: bool = True
    
    # Processing behavior options
    continue_on_error: bool = True
    max_parallel_jobs: int = 1
    timeout_seconds: Optional[int] = None
    
    # Upload options
    upload_enabled: bool = False
    upload_after_processing: bool = True
    
    # Validation options
    validate_input: bool = True
    validate_output: bool = True
    strict_validation: bool = False
    
    # Progress and logging options
    show_progress: bool = True
    verbose_logging: bool = False
    
    # Custom options for extensibility
    custom_options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate processing options."""
        if self.fade_in_duration < 0:
            raise ValueError("Fade in duration cannot be negative")
        
        if self.fade_out_duration < 0:
            raise ValueError("Fade out duration cannot be negative")
        
        if self.max_parallel_jobs < 1:
            raise ValueError("Max parallel jobs must be at least 1")
        
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
    
    @classmethod
    def default(cls) -> 'ProcessingOptions':
        """Create default processing options."""
        return cls()
    
    @classmethod
    def for_batch_processing(cls, max_jobs: int = 4, continue_on_error: bool = True) -> 'ProcessingOptions':
        """Create options optimized for batch processing."""
        return cls(
            max_parallel_jobs=max_jobs,
            continue_on_error=continue_on_error,
            quality_level=QualityLevel.MEDIUM,
            compression_mode=CompressionMode.FAST,
            show_progress=True
        )
    
    @classmethod
    def for_high_quality(cls, normalize: bool = True) -> 'ProcessingOptions':
        """Create options for high-quality processing."""
        return cls(
            quality_level=QualityLevel.HIGH,
            compression_mode=CompressionMode.OPTIMAL,
            normalize_audio=normalize,
            preserve_metadata=True,
            validate_output=True,
            strict_validation=True
        )
    
    @classmethod
    def for_fast_processing(cls) -> 'ProcessingOptions':
        """Create options for fast processing."""
        return cls(
            quality_level=QualityLevel.LOW,
            compression_mode=CompressionMode.FAST,
            normalize_audio=False,
            validate_output=False,
            max_parallel_jobs=8
        )
    
    @classmethod
    def for_analysis_only(cls) -> 'ProcessingOptions':
        """Create options for analysis operations (no file modification)."""
        return cls(
            validate_input=True,
            validate_output=False,
            create_backup=False,
            cleanup_temp_files=True,
            show_progress=False
        )
    
    def with_upload_enabled(self, upload_config: Optional[Dict[str, Any]] = None) -> 'ProcessingOptions':
        """Create new options with upload enabled."""
        custom_opts = self.custom_options.copy()
        if upload_config:
            custom_opts['upload_config'] = upload_config
        
        return ProcessingOptions(
            **{field.name: getattr(self, field.name) for field in self.__dataclass_fields__.values()
               if field.name != 'custom_options'},
            upload_enabled=True,
            upload_after_processing=True,
            custom_options=custom_opts
        )
    
    def with_custom_option(self, key: str, value: Any) -> 'ProcessingOptions':
        """Create new options with additional custom option."""
        custom_opts = self.custom_options.copy()
        custom_opts[key] = value
        
        return ProcessingOptions(
            **{field.name: getattr(self, field.name) for field in self.__dataclass_fields__.values()
               if field.name != 'custom_options'},
            custom_options=custom_opts
        )
    
    def get_custom_option(self, key: str, default: Any = None) -> Any:
        """Get value of custom option."""
        return self.custom_options.get(key, default)
    
    def get_ffmpeg_quality_args(self) -> List[str]:
        """Get FFmpeg arguments based on quality level."""
        quality_args = {
            QualityLevel.LOW: ['-q:a', '5'],
            QualityLevel.MEDIUM: ['-q:a', '3'],
            QualityLevel.HIGH: ['-q:a', '1'],
            QualityLevel.LOSSLESS: ['-c:a', 'flac']
        }
        return quality_args.get(self.quality_level, ['-q:a', '3'])
    
    def get_compression_args(self) -> List[str]:
        """Get compression arguments based on compression mode."""
        compression_args = {
            CompressionMode.NONE: [],
            CompressionMode.FAST: ['-compression_level', '1'],
            CompressionMode.OPTIMAL: ['-compression_level', '6'],
            CompressionMode.MAXIMUM: ['-compression_level', '12']
        }
        return compression_args.get(self.compression_mode, [])
    
    def should_normalize_audio(self) -> bool:
        """Check if audio normalization is enabled."""
        return self.normalize_audio
    
    def should_create_backup(self) -> bool:
        """Check if backup creation is enabled."""
        return self.create_backup
    
    def should_validate_strictly(self) -> bool:
        """Check if strict validation is enabled."""
        return self.strict_validation
    
    @property
    def description(self) -> str:
        """Get human-readable description of processing options."""
        parts = []
        
        parts.append(f"Quality: {self.quality_level.name.lower()}")
        parts.append(f"Compression: {self.compression_mode.name.lower()}")
        
        if self.normalize_audio:
            parts.append("normalized")
        
        if self.max_parallel_jobs > 1:
            parts.append(f"{self.max_parallel_jobs} parallel jobs")
        
        if self.upload_enabled:
            parts.append("with upload")
        
        return ", ".join(parts)