"""
Base Event Classes

This module provides the base classes for the domain events system.
All domain events should inherit from these base classes.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
import uuid


class BaseEvent(ABC):
    """
    Abstract base class for all events in the system.
    
    All events must have a unique ID and timestamp to ensure
    proper event tracking and ordering.
    """
    
    def __init__(self, event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the base event.
        
        Args:
            event_data: Optional dictionary containing event-specific data
        """
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.event_data = event_data or {}
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the type identifier for this event."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.event_id}, type={self.event_type}, timestamp={self.timestamp})"


class DomainEvent(BaseEvent):
    """
    Base class for domain-specific events.
    
    Domain events represent something that happened in the business domain
    and are used to communicate between different parts of the application.
    """
    
    def __init__(self, source: str, event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the domain event.
        
        Args:
            source: The source module/component that generated this event
            event_data: Optional dictionary containing event-specific data
        """
        super().__init__(event_data)
        self.source = source
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Get data from the event data dictionary.
        
        Args:
            key: The key to retrieve
            default: Default value if key is not found
            
        Returns:
            The value associated with the key, or default if not found
        """
        return self.event_data.get(key, default)
    
    def set_data(self, key: str, value: Any) -> None:
        """
        Set data in the event data dictionary.
        
        Args:
            key: The key to set
            value: The value to set
        """
        self.event_data[key] = value
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.event_id}, source={self.source}, type={self.event_type}, timestamp={self.timestamp})"


class SystemEvent(BaseEvent):
    """
    Base class for system-level events.
    
    System events represent low-level system occurrences like
    configuration changes, startup/shutdown events, etc.
    """
    
    def __init__(self, component: str, event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the system event.
        
        Args:
            component: The system component that generated this event
            event_data: Optional dictionary containing event-specific data
        """
        super().__init__(event_data)
        self.component = component
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.event_id}, component={self.component}, type={self.event_type}, timestamp={self.timestamp})"