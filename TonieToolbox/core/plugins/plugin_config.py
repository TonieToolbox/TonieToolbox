#!/usr/bin/env python3
"""
Plugin configuration manager with schema validation.

Provides type-safe configuration management for plugins with
automatic validation against config_schema from manifests.
"""
from typing import Any, Dict, Optional
from pathlib import Path
from ..utils import get_logger
from .exceptions import PluginConfigurationError

logger = get_logger(__name__)


class PluginConfigManager:
    """
    Manages plugin-specific configuration with schema validation.
    
    Integrates with ConfigManager to store plugin configs in a centralized
    subtree under plugins.config.<plugin_id>.
    """
    
    def __init__(self, config_manager, plugin_registry):
        """
        Initialize plugin config manager.
        
        Args:
            config_manager: ConfigManager instance
            plugin_registry: PluginRegistry for accessing manifests
        """
        self.config_manager = config_manager
        self.plugin_registry = plugin_registry
        logger.debug("PluginConfigManager initialized")
    
    def get_config(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            key: Configuration key
            default: Default value (falls back to schema default)
            
        Returns:
            Configuration value
        """
        # Try to get from saved config first
        value = self.config_manager.plugins.get_plugin_config(plugin_id, key)
        
        if value is not None:
            return value
        
        # Fall back to schema default
        schema_default = self._get_schema_default(plugin_id, key)
        if schema_default is not None:
            return schema_default
        
        # Fall back to provided default
        return default
    
    def set_config(self, plugin_id: str, key: str, value: Any, validate: bool = True) -> bool:
        """
        Set a configuration value for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            key: Configuration key
            value: Configuration value
            validate: Whether to validate against schema
            
        Returns:
            True if set successfully
            
        Raises:
            PluginConfigurationError: If validation fails
        """
        if validate:
            if not self.validate_config_value(plugin_id, key, value):
                raise PluginConfigurationError(
                    f"Invalid configuration value for {plugin_id}.{key}: {value}"
                )
        
        self.config_manager.plugins.set_plugin_config(plugin_id, key, value)
        return True
    
    def get_all_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get all configuration for a plugin (merged with schema defaults).
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Dictionary of all configuration
        """
        # Start with schema defaults
        config = {}
        schema = self._get_config_schema(plugin_id)
        
        if schema:
            for key, spec in schema.items():
                if 'default' in spec:
                    config[key] = spec['default']
        
        # Override with saved configuration
        saved_config = self.config_manager.plugins.get_all_plugin_config(plugin_id)
        config.update(saved_config)
        
        return config
    
    def set_all_config(self, plugin_id: str, config_dict: Dict[str, Any], validate: bool = True) -> bool:
        """
        Set all configuration for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            config_dict: Dictionary of configuration values
            validate: Whether to validate against schema
            
        Returns:
            True if set successfully
            
        Raises:
            PluginConfigurationError: If validation fails
        """
        if validate:
            errors = self.validate_config(plugin_id, config_dict)
            if errors:
                raise PluginConfigurationError(
                    f"Configuration validation failed for {plugin_id}: {', '.join(errors)}"
                )
        
        self.config_manager.plugins.set_all_plugin_config(plugin_id, config_dict)
        return True
    
    def validate_config_value(self, plugin_id: str, key: str, value: Any) -> bool:
        """
        Validate a single configuration value against schema.
        
        Args:
            plugin_id: Plugin identifier
            key: Configuration key
            value: Value to validate
            
        Returns:
            True if valid
        """
        schema = self._get_config_schema(plugin_id)
        if not schema or key not in schema:
            # No schema or key not in schema - accept any value
            return True
        
        spec = schema[key]
        return self._validate_value_against_spec(value, spec)
    
    def validate_config(self, plugin_id: str, config_dict: Dict[str, Any]) -> list[str]:
        """
        Validate a configuration dictionary against schema.
        
        Args:
            plugin_id: Plugin identifier
            config_dict: Configuration dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        schema = self._get_config_schema(plugin_id)
        if not schema:
            return []  # No schema - all valid
        
        errors = []
        
        for key, value in config_dict.items():
            if key in schema:
                spec = schema[key]
                if not self._validate_value_against_spec(value, spec):
                    expected_type = spec.get('type', 'unknown')
                    errors.append(f"'{key}': expected {expected_type}, got {type(value).__name__}")
            # Note: Extra keys not in schema are allowed (forward compatibility)
        
        return errors
    
    def _get_config_schema(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get config schema from plugin manifest."""
        manifest = self.plugin_registry.get_manifest(plugin_id)
        if manifest:
            return manifest.config_schema
        return None
    
    def _get_schema_default(self, plugin_id: str, key: str) -> Optional[Any]:
        """Get default value from schema."""
        schema = self._get_config_schema(plugin_id)
        if schema and key in schema:
            return schema[key].get('default')
        return None
    
    def _validate_value_against_spec(self, value: Any, spec: Dict[str, Any]) -> bool:
        """
        Validate a value against a schema specification.
        
        Args:
            value: Value to validate
            spec: Schema specification dict
            
        Returns:
            True if valid
        """
        expected_type = spec.get('type')
        
        if not expected_type:
            return True  # No type specified - accept anything
        
        # Type mapping
        type_map = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_map.get(expected_type)
        
        if expected_python_type is None:
            logger.warning(f"Unknown schema type: {expected_type}")
            return True  # Unknown type - accept
        
        # Check type
        if not isinstance(value, expected_python_type):
            return False
        
        # Additional validations
        if expected_type == 'integer' or expected_type == 'number':
            # Check min/max
            if 'minimum' in spec and value < spec['minimum']:
                return False
            if 'maximum' in spec and value > spec['maximum']:
                return False
        
        elif expected_type == 'string':
            # Check minLength/maxLength
            if 'minLength' in spec and len(value) < spec['minLength']:
                return False
            if 'maxLength' in spec and len(value) > spec['maxLength']:
                return False
            # Check pattern (regex)
            if 'pattern' in spec:
                import re
                if not re.match(spec['pattern'], value):
                    return False
        
        elif expected_type == 'array':
            # Check minItems/maxItems
            if 'minItems' in spec and len(value) < spec['minItems']:
                return False
            if 'maxItems' in spec and len(value) > spec['maxItems']:
                return False
        
        return True
    
    def initialize_plugin_config(self, plugin_id: str) -> None:
        """
        Initialize plugin configuration with schema defaults.
        
        Called when a plugin is first loaded to ensure all config
        keys exist with their default values.
        
        Args:
            plugin_id: Plugin identifier
        """
        schema = self._get_config_schema(plugin_id)
        if not schema:
            logger.debug(f"No config schema for {plugin_id}")
            return
        
        current_config = self.config_manager.plugins.get_all_plugin_config(plugin_id)
        
        # Add missing keys with defaults
        updated = False
        for key, spec in schema.items():
            if key not in current_config and 'default' in spec:
                current_config[key] = spec['default']
                updated = True
        
        if updated:
            self.config_manager.plugins.set_all_plugin_config(plugin_id, current_config)
            self.config_manager.save_config()
            logger.info(f"Initialized configuration for {plugin_id} with schema defaults")
