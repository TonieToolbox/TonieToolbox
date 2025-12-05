#!/usr/bin/python3
"""
Base class for TeddyCloud-specific processors.

This provides a simple base without dependencies on the old processing system.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from pathlib import Path


class BaseTeddyCloudProcessor(ABC):
    """Base class for TeddyCloud processors."""
    
    def __init__(self, logger: logging.Logger, dependencies: Dict[str, str]):
        """Initialize base processor with logger and dependencies."""
        self.logger = logger
        self.dependencies = dependencies
    
    @abstractmethod
    def process(self, args) -> int:
        """Process TeddyCloud operation according to the specific mode."""
        pass
    
    def _publish_processing_started(self, input_path: Path, processing_mode: str, **kwargs) -> None:
        """Publish processing started event (stub for TeddyCloud processors)."""
        self.logger.debug(f"Processing started: {input_path} (mode: {processing_mode})")
    
    def _publish_processing_completed(self, input_path: Path, **kwargs) -> None:
        """Publish processing completed event (stub for TeddyCloud processors)."""
        self.logger.debug(f"Processing completed: {input_path}")
    
    def _publish_processing_failed(self, input_path: Path, error: Exception, **kwargs) -> None:
        """Publish processing failed event (stub for TeddyCloud processors)."""
        self.logger.debug(f"Processing failed: {input_path}, error: {error}")