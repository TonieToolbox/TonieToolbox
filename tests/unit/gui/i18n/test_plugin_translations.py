#!/usr/bin/env python3
"""
Unit tests for plugin translation system.
"""
import pytest
from pathlib import Path
from TonieToolbox.core.gui.i18n.manager import TranslationManager


class TestPluginTranslations:
    """Test plugin translation support in TranslationManager."""
    
    def test_load_plugin_translation(self):
        """Test loading plugin translations into namespaced structure."""
        manager = TranslationManager()
        
        # Load a plugin translation
        plugin_data = {
            "viewer": {
                "title": "Test Viewer",
                "search": "Search..."
            },
            "menu": {
                "label": "Test Menu"
            }
        }
        
        success = manager.load_plugin_translation(
            plugin_id="test_plugin",
            language_code="en_US",
            translation_data=plugin_data
        )
        
        assert success is True
        
        # Verify translations are accessible
        assert manager.translate("test_plugin", "viewer", "title") == "Test Viewer"
        assert manager.translate("test_plugin", "viewer", "search") == "Search..."
        assert manager.translate("test_plugin", "menu", "label") == "Test Menu"
    
    def test_load_plugin_translation_multiple_languages(self):
        """Test loading plugin translations for multiple languages."""
        manager = TranslationManager()
        
        # English translation
        en_data = {
            "greeting": "Hello"
        }
        manager.load_plugin_translation("test_plugin", "en_US", en_data)
        
        # German translation
        de_data = {
            "greeting": "Hallo"
        }
        manager.load_plugin_translation("test_plugin", "de_DE", de_data)
        
        # Set language to English
        manager.set_language("en_US")
        assert manager.translate("test_plugin", "greeting") == "Hello"
        
        # Set language to German
        manager.set_language("de_DE")
        assert manager.translate("test_plugin", "greeting") == "Hallo"
    
    def test_unload_plugin_translations(self):
        """Test unloading plugin translations."""
        manager = TranslationManager()
        
        # Load plugin translations
        plugin_data = {"test": "value"}
        manager.load_plugin_translation("test_plugin", "en_US", plugin_data)
        manager.load_plugin_translation("test_plugin", "de_DE", plugin_data)
        
        # Verify loaded
        assert manager.translate("test_plugin", "test") == "value"
        
        # Unload
        manager.unload_plugin_translations("test_plugin")
        
        # Verify unloaded (returns first missing key when not found)
        result = manager.translate("test_plugin", "test")
        assert "test_plugin" in result  # Should contain the plugin namespace
    
    def test_plugin_translation_isolation(self):
        """Test that plugin translations are isolated by namespace."""
        manager = TranslationManager()
        
        # Load translations for two different plugins
        plugin1_data = {"title": "Plugin 1 Title"}
        plugin2_data = {"title": "Plugin 2 Title"}
        
        manager.load_plugin_translation("plugin1", "en_US", plugin1_data)
        manager.load_plugin_translation("plugin2", "en_US", plugin2_data)
        
        # Verify isolation
        assert manager.translate("plugin1", "title") == "Plugin 1 Title"
        assert manager.translate("plugin2", "title") == "Plugin 2 Title"
    
    def test_plugin_translation_merge(self):
        """Test that loading translations for same plugin merges data."""
        manager = TranslationManager()
        
        # Load initial data
        initial_data = {
            "section1": {"key1": "value1"}
        }
        manager.load_plugin_translation("test_plugin", "en_US", initial_data)
        
        # Load additional data (should merge)
        additional_data = {
            "section2": {"key2": "value2"}
        }
        manager.load_plugin_translation("test_plugin", "en_US", additional_data)
        
        # Verify both sections are accessible
        assert manager.translate("test_plugin", "section1", "key1") == "value1"
        assert manager.translate("test_plugin", "section2", "key2") == "value2"
    
    def test_plugin_translation_with_formatting(self):
        """Test plugin translations with string formatting."""
        manager = TranslationManager()
        
        plugin_data = {
            "message": "Hello {name}, you have {count} items"
        }
        manager.load_plugin_translation("test_plugin", "en_US", plugin_data)
        
        result = manager.translate(
            "test_plugin", "message",
            name="Alice", count=5
        )
        
        assert result == "Hello Alice, you have 5 items"
    
    def test_plugin_translation_fallback(self):
        """Test fallback to English when translation not found in current language."""
        manager = TranslationManager()
        
        # Only load English translation
        en_data = {"greeting": "Hello"}
        manager.load_plugin_translation("test_plugin", "en_US", en_data)
        
        # Set language to German (not loaded)
        manager.set_language("de_DE")
        
        # Should fallback to English
        result = manager.translate("test_plugin", "greeting")
        assert result == "Hello"


class TestPluginContext:
    """Test plugin context translation support."""
    
    def test_plugin_context_tr_method(self):
        """Test PluginContext.tr() convenience method."""
        from TonieToolbox.core.plugins.base import PluginContext
        from TonieToolbox.core.events import get_event_bus
        from TonieToolbox.core.utils import get_logger
        
        manager = TranslationManager()
        plugin_data = {
            "viewer": {"title": "Test Title"}
        }
        manager.load_plugin_translation("test_plugin", "en_US", plugin_data)
        manager.set_language("en_US")
        
        # Create context
        context = PluginContext(
            app_version="1.0.0",
            config_manager=None,
            event_bus=get_event_bus(),
            logger=get_logger(__name__),
            plugin_dir=Path.cwd(),
            translation_manager=manager
        )
        
        # Set namespace
        context.set_plugin_namespace("test_plugin")
        
        # Use tr() method - should automatically prefix with plugin_id
        result = context.tr("viewer", "title")
        assert result == "Test Title"
    
    def test_plugin_context_tr_without_namespace(self):
        """Test PluginContext.tr() without namespace set."""
        from TonieToolbox.core.plugins.base import PluginContext
        from TonieToolbox.core.events import get_event_bus
        from TonieToolbox.core.utils import get_logger
        
        manager = TranslationManager()
        
        context = PluginContext(
            app_version="1.0.0",
            config_manager=None,
            event_bus=get_event_bus(),
            logger=get_logger(__name__),
            plugin_dir=Path.cwd(),
            translation_manager=manager
        )
        
        # Don't set namespace - should still work but without prefix
        result = context.tr("app", "title")
        assert result == "TonieToolbox"  # Core translation
    
    def test_plugin_context_tr_without_translation_manager(self):
        """Test PluginContext.tr() fallback when no translation manager."""
        from TonieToolbox.core.plugins.base import PluginContext
        from TonieToolbox.core.events import get_event_bus
        from TonieToolbox.core.utils import get_logger
        
        context = PluginContext(
            app_version="1.0.0",
            config_manager=None,
            event_bus=get_event_bus(),
            logger=get_logger(__name__),
            plugin_dir=Path.cwd(),
            translation_manager=None  # No translation manager
        )
        
        context.set_plugin_namespace("test_plugin")
        
        # Should return key path as fallback
        result = context.tr("viewer", "title")
        assert result == "viewer.title"
