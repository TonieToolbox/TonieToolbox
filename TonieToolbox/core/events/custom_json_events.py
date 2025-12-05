#!/usr/bin/python3
"""
Events for custom JSON operations.

Provides domain events for tracking tonies.custom.json creation and updates.
"""
from typing import Optional, Dict, Any
from .base_events import DomainEvent


class CustomJsonFetchStartedEvent(DomainEvent):
    """Emitted when fetching tonies.custom.json from server starts."""
    
    def __init__(self, source: str, event_data: Optional[Dict[str, Any]] = None):
        super().__init__(source, event_data)
    
    @property
    def event_type(self) -> str:
        return "custom_json.fetch.started"


class CustomJsonFetchCompletedEvent(DomainEvent):
    """Emitted when fetching tonies.custom.json completes successfully."""
    
    def __init__(self, source: str, file_path: str, entry_count: int, 
                 event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({
            'file_path': file_path,
            'entry_count': entry_count
        })
        super().__init__(source, data)
        self.file_path = file_path
        self.entry_count = entry_count
    
    @property
    def event_type(self) -> str:
        return "custom_json.fetch.completed"


class CustomJsonFetchFailedEvent(DomainEvent):
    """Emitted when fetching tonies.custom.json fails."""
    
    def __init__(self, source: str, error: str, event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({'error': error})
        super().__init__(source, data)
        self.error = error
    
    @property
    def event_type(self) -> str:
        return "custom_json.fetch.failed"


class CustomJsonProcessingStartedEvent(DomainEvent):
    """Emitted when custom JSON processing starts."""
    
    def __init__(self, source: str, file_count: int, event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({'file_count': file_count})
        super().__init__(source, data)
        self.file_count = file_count
    
    @property
    def event_type(self) -> str:
        return "custom_json.processing.started"


class CustomJsonProcessingCompletedEvent(DomainEvent):
    """Emitted when custom JSON processing completes."""
    
    def __init__(self, source: str, file_path: str, entries_added: int, 
                 entries_updated: int, total_entries: int,
                 event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({
            'file_path': file_path,
            'entries_added': entries_added,
            'entries_updated': entries_updated,
            'total_entries': total_entries
        })
        super().__init__(source, data)
        self.file_path = file_path
        self.entries_added = entries_added
        self.entries_updated = entries_updated
        self.total_entries = total_entries
    
    @property
    def event_type(self) -> str:
        return "custom_json.processing.completed"


class CustomJsonProcessingFailedEvent(DomainEvent):
    """Emitted when custom JSON processing fails."""
    
    def __init__(self, source: str, error: str, event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({'error': error})
        super().__init__(source, data)
        self.error = error
    
    @property
    def event_type(self) -> str:
        return "custom_json.processing.failed"


class CustomJsonEntryAddedEvent(DomainEvent):
    """Emitted when a new entry is added to custom JSON."""
    
    def __init__(self, source: str, taf_file: str, series: str, episodes: str,
                 event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({
            'taf_file': taf_file,
            'series': series,
            'episodes': episodes
        })
        super().__init__(source, data)
        self.taf_file = taf_file
        self.series = series
        self.episodes = episodes
    
    @property
    def event_type(self) -> str:
        return "custom_json.entry.added"


class CustomJsonEntryUpdatedEvent(DomainEvent):
    """Emitted when an existing entry is updated in custom JSON."""
    
    def __init__(self, source: str, taf_file: str, series: str, episodes: str, hash_added: str,
                 event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({
            'taf_file': taf_file,
            'series': series,
            'episodes': episodes,
            'hash_added': hash_added
        })
        super().__init__(source, data)
        self.taf_file = taf_file
        self.series = series
        self.episodes = episodes
        self.hash_added = hash_added
    
    @property
    def event_type(self) -> str:
        return "custom_json.entry.updated"


class CustomJsonSavedEvent(DomainEvent):
    """Emitted when custom JSON is saved to file."""
    
    def __init__(self, source: str, file_path: str, entry_count: int,
                 event_data: Optional[Dict[str, Any]] = None):
        data = event_data or {}
        data.update({
            'file_path': file_path,
            'entry_count': entry_count
        })
        super().__init__(source, data)
        self.file_path = file_path
        self.entry_count = entry_count
    
    @property
    def event_type(self) -> str:
        return "custom_json.saved"
