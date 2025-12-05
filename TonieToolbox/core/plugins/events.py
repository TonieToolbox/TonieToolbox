#!/usr/bin/env python3
"""
Plugin events for the TonieToolbox plugin system.
"""
from typing import Optional, Dict, Any, List
from ..events.base_events import DomainEvent


class PluginLoadedEvent(DomainEvent):
    """Event emitted when a plugin is successfully loaded."""
    
    def __init__(self, source: str = "plugin_manager", 
                 plugin_id: str = "",
                 plugin_name: str = "",
                 plugin_version: str = "",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin loaded event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            plugin_name: Plugin display name
            plugin_version: Plugin version string
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'plugin_id': plugin_id,
            'plugin_name': plugin_name,
            'plugin_version': plugin_version
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.loaded"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')
    
    @property
    def plugin_name(self) -> str:
        return self.get_data('plugin_name')
    
    @property
    def plugin_version(self) -> str:
        return self.get_data('plugin_version')


class PluginUnloadedEvent(DomainEvent):
    """Event emitted when a plugin is unloaded."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 reason: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin unloaded event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            reason: Optional reason for unloading
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'plugin_id': plugin_id,
            'reason': reason
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.unloaded"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')
    
    @property
    def reason(self) -> Optional[str]:
        return self.get_data('reason')


class PluginErrorEvent(DomainEvent):
    """Event emitted when a plugin encounters an error."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 error_message: str = "",
                 error_type: str = "",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin error event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            error_message: Error description
            error_type: Type of error that occurred
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'plugin_id': plugin_id,
            'error_message': error_message,
            'error_type': error_type
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.error"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')
    
    @property
    def error_message(self) -> str:
        return self.get_data('error_message')
    
    @property
    def error_type(self) -> str:
        return self.get_data('error_type')


class PluginEnabledEvent(DomainEvent):
    """Event emitted when a plugin is enabled."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin enabled event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({'plugin_id': plugin_id})
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.enabled"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')


class PluginDisabledEvent(DomainEvent):
    """Event emitted when a plugin is disabled."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin disabled event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({'plugin_id': plugin_id})
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.disabled"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')


class PluginInstalledEvent(DomainEvent):
    """Event emitted when a new plugin is installed."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 plugin_name: str = "",
                 plugin_path: str = "",
                 auto_enable: bool = False,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin installed event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            plugin_name: Plugin display name
            plugin_path: Path where plugin was installed
            auto_enable: Whether plugin was auto-enabled after install
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'plugin_id': plugin_id,
            'plugin_name': plugin_name,
            'plugin_path': plugin_path,
            'auto_enable': auto_enable
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.installed"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')
    
    @property
    def plugin_name(self) -> str:
        return self.get_data('plugin_name')
    
    @property
    def plugin_path(self) -> str:
        return self.get_data('plugin_path')
    
    @property
    def auto_enable(self) -> bool:
        return self.get_data('auto_enable', False)


class PluginReloadedEvent(DomainEvent):
    """Event emitted when a plugin is reloaded."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 plugin_name: str = "",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin reloaded event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            plugin_name: Plugin display name
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'plugin_id': plugin_id,
            'plugin_name': plugin_name
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.reloaded"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')
    
    @property
    def plugin_name(self) -> str:
        return self.get_data('plugin_name')


class PluginGuiComponentsChangedEvent(DomainEvent):
    """Event emitted when plugin GUI components need refresh."""
    
    def __init__(self, source: str = "plugin_manager",
                 plugin_id: str = "",
                 change_type: str = "updated",  # 'added', 'removed', 'updated'
                 component_categories: Optional[List[str]] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize GUI components changed event.
        
        Args:
            source: Source module triggering the event
            plugin_id: Unique plugin identifier
            change_type: Type of change ('added', 'removed', 'updated')
            component_categories: List of affected component categories
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'plugin_id': plugin_id,
            'change_type': change_type,
            'component_categories': component_categories or []
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "plugin.gui_components_changed"
    
    @property
    def plugin_id(self) -> str:
        return self.get_data('plugin_id')
    
    @property
    def change_type(self) -> str:
        return self.get_data('change_type', 'updated')
    
    @property
    def component_categories(self) -> List[str]:
        return self.get_data('component_categories', [])
