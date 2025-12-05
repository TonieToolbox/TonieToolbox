#!/usr/bin/python3
"""
ToniesData manager for coordinating tonies JSON operations.
Provides high-level orchestration following Clean Architecture principles.
"""
from typing import Optional, Any
from .formats.v1 import ToniesJsonV1Handler
from .formats.v2 import ToniesJsonV2Handler
from ..utils import get_logger

logger = get_logger(__name__)


class ToniesDataManager:
    """
    Manager for coordinating tonies data operations across formats.
    
    Follows Clean Architecture by accepting repository interface instead of direct client.
    This allows proper dependency inversion and testability.
    """
    
    def __init__(self, repository: Optional[Any] = None):
        """
        Initialize the manager.
        
        Args:
            repository: TeddyCloud repository interface (ITeddyCloudRepository)
                       for server operations. Can be None for offline mode.
        """
        self.repository = repository
        self.logger = logger

    def get_v1_handler(self) -> ToniesJsonV1Handler:
        """Get a V1 format handler instance."""
        return ToniesJsonV1Handler(self.repository)

    def get_v2_handler(self) -> ToniesJsonV2Handler:
        """Get a V2 format handler instance."""
        return ToniesJsonV2Handler(self.repository)