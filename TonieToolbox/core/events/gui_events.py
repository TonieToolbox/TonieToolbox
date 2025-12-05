"""
GUI Domain Events

This module defines events related to GUI operations and state changes.
These events allow different GUI components to communicate without direct coupling
and enable other modules to trigger GUI updates.
"""

from typing import Optional, Dict, Any, Union
from .base_events import DomainEvent, SystemEvent


class GuiUpdateEvent(DomainEvent):
    """Base event for GUI updates."""
    
    def __init__(self, source: str, component: str, update_type: str,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize GUI update event.
        
        Args:
            source: Source module triggering the update
            component: GUI component to update
            update_type: Type of update to perform
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'component': component,
            'update_type': update_type
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "gui.update"
    
    @property
    def component(self) -> str:
        return self.get_data('component')
    
    @property
    def update_type(self) -> str:
        return self.get_data('update_type')


class StatusUpdateEvent(DomainEvent):
    """Event for updating status information in the GUI."""
    
    def __init__(self, source: str, message: str, status_type: str = "info",
                 progress: Optional[float] = None, 
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize status update event.
        
        Args:
            source: Source module updating status
            message: Status message to display
            status_type: Type of status (info, warning, error, success)
            progress: Optional progress value (0.0 to 1.0)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'message': message,
            'status_type': status_type,
            'progress': progress
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "gui.status_update"
    
    @property
    def message(self) -> str:
        return self.get_data('message')
    
    @property
    def status_type(self) -> str:
        return self.get_data('status_type', 'info')
    
    @property
    def progress(self) -> Optional[float]:
        return self.get_data('progress')


class ProgressUpdateEvent(DomainEvent):
    """Event for updating progress bars or indicators."""
    
    def __init__(self, source: str, progress: float, total: Optional[int] = None,
                 current: Optional[int] = None, operation: str = "processing",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize progress update event.
        
        Args:
            source: Source module updating progress
            progress: Progress value (0.0 to 1.0)
            total: Total number of items (optional)
            current: Current item number (optional)
            operation: Description of the operation
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'progress': max(0.0, min(1.0, progress)),  # Clamp between 0 and 1
            'total': total,
            'current': current,
            'operation': operation
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "gui.progress_update"
    
    @property
    def progress(self) -> float:
        return self.get_data('progress', 0.0)
    
    @property
    def total(self) -> Optional[int]:
        return self.get_data('total')
    
    @property
    def current(self) -> Optional[int]:
        return self.get_data('current')
    
    @property
    def operation(self) -> str:
        return self.get_data('operation', 'processing')


class ErrorDisplayEvent(DomainEvent):
    """Event for displaying error messages in the GUI."""
    
    def __init__(self, source: str, error_message: str, error_type: str = "error",
                 details: Optional[str] = None, 
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize error display event.
        
        Args:
            source: Source module reporting the error
            error_message: Main error message
            error_type: Type of error (error, warning, critical)
            details: Optional detailed error information
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'error_message': error_message,
            'error_type': error_type,
            'details': details
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "gui.error_display"
    
    @property
    def error_message(self) -> str:
        return self.get_data('error_message')
    
    @property
    def error_type(self) -> str:
        return self.get_data('error_type', 'error')
    
    @property
    def details(self) -> Optional[str]:
        return self.get_data('details')


class ThemeChangedEvent(SystemEvent):
    """Event fired when the GUI theme changes."""
    
    def __init__(self, new_theme: str, old_theme: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize theme changed event.
        
        Args:
            new_theme: The new theme name
            old_theme: The previous theme name (optional)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'new_theme': new_theme,
            'old_theme': old_theme
        })
        super().__init__("gui_manager", data)
    
    @property
    def event_type(self) -> str:
        return "gui.theme_changed"
    
    @property
    def new_theme(self) -> str:
        return self.event_data['new_theme']
    
    @property
    def old_theme(self) -> Optional[str]:
        return self.event_data.get('old_theme')


class LanguageChangedEvent(SystemEvent):
    """Event fired when the GUI language changes."""
    
    def __init__(self, new_language: str, old_language: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize language changed event.
        
        Args:
            new_language: The new language code (e.g., 'en_US', 'de_DE')
            old_language: The previous language code (optional)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'new_language': new_language,
            'old_language': old_language
        })
        super().__init__("translation_manager", data)
    
    @property
    def event_type(self) -> str:
        return "gui.language_changed"
    
    @property
    def new_language(self) -> str:
        return self.event_data['new_language']
    
    @property
    def old_language(self) -> Optional[str]:
        return self.event_data.get('old_language')


class WindowStateChangedEvent(SystemEvent):
    """Event fired when window state changes (minimized, maximized, etc.)."""
    
    def __init__(self, window_id: str, state: str, 
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize window state changed event.
        
        Args:
            window_id: Identifier of the window
            state: New window state (minimized, maximized, normal, closed)
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'window_id': window_id,
            'state': state
        })
        super().__init__("gui_window", data)
    
    @property
    def event_type(self) -> str:
        return "gui.window_state_changed"
    
    @property
    def window_id(self) -> str:
        return self.event_data['window_id']
    
    @property
    def state(self) -> str:
        return self.event_data['state']


class FileSelectionChangedEvent(DomainEvent):
    """Event fired when file selection changes in the GUI."""
    
    def __init__(self, source: str, selected_files: list, 
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize file selection changed event.
        
        Args:
            source: Source component that changed selection
            selected_files: List of selected file paths
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'selected_files': selected_files
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "gui.file_selection_changed"
    
    @property
    def selected_files(self) -> list:
        return self.get_data('selected_files', [])


class ConfigurationChangedEvent(DomainEvent):
    """Event fired when configuration settings change via GUI."""
    
    def __init__(self, source: str, config_section: str, changed_keys: list,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration changed event.
        
        Args:
            source: Source component that changed configuration
            config_section: Section of configuration that changed
            changed_keys: List of configuration keys that were modified
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'config_section': config_section,
            'changed_keys': changed_keys
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "gui.configuration_changed"
    
    @property
    def config_section(self) -> str:
        return self.get_data('config_section')
    
    @property
    def changed_keys(self) -> list:
        return self.get_data('changed_keys', [])