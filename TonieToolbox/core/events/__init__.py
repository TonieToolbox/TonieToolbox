"""
Domain Events System

This module provides a domain events system for decoupling modules in the TonieToolbox application.
It allows modules to publish and subscribe to events without direct dependencies.
"""

from .event_bus import EventBus, get_event_bus
from .base_events import BaseEvent, DomainEvent

# Clean Architecture processing events
from .enhanced_processing_events import (
    ProcessingOperationStartedEvent,
    ProcessingOperationCompletedEvent,
    ProcessingOperationFailedEvent,
    ProcessingProgressEvent,
    FileProcessingStartedEvent,
    FileProcessingCompletedEvent,
    ValidationEvent
)
from .gui_events import (
    GuiUpdateEvent,
    StatusUpdateEvent,
    ThemeChangedEvent,
    LanguageChangedEvent,
    ProgressUpdateEvent,
    ErrorDisplayEvent,
    WindowStateChangedEvent,
)
from .player_events import (
    PlayerStateChangedEvent,
    PlayerFileLoadedEvent,
    PlayerPositionChangedEvent,
    PlayerVolumeChangedEvent,
    PlayerDurationChangedEvent,
    PlayerChapterChangedEvent,
    PlayerErrorOccurredEvent,
)

__all__ = [
    # Event Bus
    'EventBus',
    'get_event_bus',
    
    # Base Events
    'BaseEvent',
    'DomainEvent',
    
    # Processing Events (Clean Architecture)
    'ProcessingOperationStartedEvent',
    'ProcessingOperationCompletedEvent',
    'ProcessingOperationFailedEvent',
    'ProcessingProgressEvent',
    'FileProcessingStartedEvent',
    'FileProcessingCompletedEvent',
    'ValidationEvent',
    
    # GUI Events
    'GuiUpdateEvent',
    'StatusUpdateEvent',
    'ThemeChangedEvent',
    'LanguageChangedEvent',
    'ProgressUpdateEvent',
    'ErrorDisplayEvent',
    'WindowStateChangedEvent',
    
    # Player Events
    'PlayerStateChangedEvent',
    'PlayerFileLoadedEvent',
    'PlayerPositionChangedEvent',
    'PlayerVolumeChangedEvent',
    'PlayerDurationChangedEvent',
    'PlayerChapterChangedEvent',
    'PlayerErrorOccurredEvent',
]
# Import custom JSON events
from .custom_json_events import (
    CustomJsonFetchStartedEvent,
    CustomJsonFetchCompletedEvent,
    CustomJsonFetchFailedEvent,
    CustomJsonProcessingStartedEvent,
    CustomJsonProcessingCompletedEvent,
    CustomJsonProcessingFailedEvent,
    CustomJsonEntryAddedEvent,
    CustomJsonEntryUpdatedEvent,
    CustomJsonSavedEvent,
)

# Add to __all__ (append before closing bracket)
__all__.extend([
    # Custom JSON Events
    'CustomJsonFetchStartedEvent',
    'CustomJsonFetchCompletedEvent',
    'CustomJsonFetchFailedEvent',
    'CustomJsonProcessingStartedEvent',
    'CustomJsonProcessingCompletedEvent',
    'CustomJsonProcessingFailedEvent',
    'CustomJsonEntryAddedEvent',
    'CustomJsonEntryUpdatedEvent',
    'CustomJsonSavedEvent',
])
