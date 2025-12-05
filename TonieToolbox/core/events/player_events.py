"""
Player Domain Events

This module defines events related to player operations and state changes.
These events allow different components to communicate about player activities
without direct coupling and enable proper separation of concerns.
"""

from typing import Optional, Dict, Any, Union, TYPE_CHECKING
from pathlib import Path
from .base_events import DomainEvent

if TYPE_CHECKING:
    from ..analysis.models import TafAnalysisResult, ChapterInfo


class PlayerStateChangedEvent(DomainEvent):
    """Event fired when player state changes (playing, paused, stopped, etc.)."""
    
    def __init__(self, source: str, state: str, previous_state: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player state changed event.
        
        Args:
            source: Source module triggering the event
            state: New player state
            previous_state: Previous player state (if available)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'state': state,
            'previous_state': previous_state
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.state_changed"
    
    @property
    def state(self) -> str:
        return self.get_data('state')
    
    @property
    def previous_state(self) -> Optional[str]:
        return self.get_data('previous_state')


class PlayerFileLoadedEvent(DomainEvent):
    """Event fired when a file is loaded into the player."""
    
    def __init__(self, source: str, file_path: Union[str, Path],
                 analysis_result: 'TafAnalysisResult',
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player file loaded event.
        
        Args:
            source: Source module triggering the event
            file_path: Path to the loaded file
            analysis_result: TAF analysis domain object (required)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'file_path': str(file_path),
            'analysis_result': analysis_result
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.file_loaded"
    
    @property
    def file_path(self) -> str:
        return self.get_data('file_path')
    
    @property
    def analysis_result(self) -> 'TafAnalysisResult':
        """Get the TAF analysis domain object."""
        return self.get_data('analysis_result')


class PlayerPositionChangedEvent(DomainEvent):
    """Event fired when player position changes."""
    
    def __init__(self, source: str, position: float, duration: Optional[float] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player position changed event.
        
        Args:
            source: Source module triggering the event
            position: Current position in seconds
            duration: Total duration in seconds (if available)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'position': position,
            'duration': duration
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.position_changed"
    
    @property
    def position(self) -> float:
        return self.get_data('position')
    
    @property
    def duration(self) -> Optional[float]:
        return self.get_data('duration')


class PlayerVolumeChangedEvent(DomainEvent):
    """Event fired when player volume changes."""
    
    def __init__(self, source: str, volume: float, is_muted: bool = False,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player volume changed event.
        
        Args:
            source: Source module triggering the event
            volume: Volume level (0.0 to 1.0)
            is_muted: Whether the player is muted
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'volume': volume,
            'is_muted': is_muted
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.volume_changed"
    
    @property
    def volume(self) -> float:
        return self.get_data('volume')
    
    @property
    def is_muted(self) -> bool:
        return self.get_data('is_muted', False)


class PlayerDurationChangedEvent(DomainEvent):
    """Event fired when player duration changes (new file loaded)."""
    
    def __init__(self, source: str, duration: float,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player duration changed event.
        
        Args:
            source: Source module triggering the event
            duration: Total duration in seconds
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'duration': duration
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.duration_changed"
    
    @property
    def duration(self) -> float:
        return self.get_data('duration')


class PlayerChapterChangedEvent(DomainEvent):
    """Event fired when player chapter changes."""
    
    def __init__(self, source: str, chapter_index: int,
                 chapter_info: Optional['ChapterInfo'] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player chapter changed event.
        
        Args:
            source: Source module triggering the event
            chapter_index: Index of the current chapter
            chapter_info: Chapter domain object
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'chapter_index': chapter_index,
            'chapter_info': chapter_info
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.chapter_changed"
    
    @property
    def chapter_index(self) -> int:
        return self.get_data('chapter_index')
    
    @property
    def chapter_info(self) -> Optional['ChapterInfo']:
        return self.get_data('chapter_info')


class PlayerErrorOccurredEvent(DomainEvent):
    """Event fired when a player error occurs."""
    
    def __init__(self, source: str, error_message: str, error_code: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize player error occurred event.
        
        Args:
            source: Source module triggering the event
            error_message: Error message
            error_code: Optional error code
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'error_message': error_message,
            'error_code': error_code
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "player.error_occurred"
    
    @property
    def error_message(self) -> str:
        return self.get_data('error_message')
    
    @property
    def error_code(self) -> Optional[str]:
        return self.get_data('error_code')