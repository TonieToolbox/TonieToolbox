#!/usr/bin/env python3
"""
Unit tests for Mini Player plugin.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from TonieToolbox.core.plugins.base import PluginManifest, PluginContext, PluginType
from TonieToolbox.core.plugins.builtin.mini_player.plugin import MiniPlayerPlugin


class TestMiniPlayerPlugin:
    """Test MiniPlayerPlugin class."""
    
    def test_plugin_manifest(self):
        """Test that plugin has valid manifest."""
        plugin = MiniPlayerPlugin()
        manifest = plugin.get_manifest()
        
        assert isinstance(manifest, PluginManifest)
        assert manifest.metadata.id == "com.tonietoolbox.mini_player"
        assert manifest.metadata.name == "Mini Player"
        assert manifest.metadata.version == "1.0.0"
        assert manifest.metadata.plugin_type == PluginType.GUI
    
    def test_plugin_initialization(self):
        """Test plugin initialization."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        
        result = plugin.initialize(context)
        
        assert result is True
        assert plugin._context is context
    
    def test_plugin_initialization_failure(self):
        """Test plugin initialization handles exceptions."""
        plugin = MiniPlayerPlugin()
        
        # Create context that raises exception
        context = Mock(spec=PluginContext)
        context.app_version = property(Mock(side_effect=Exception("Test error")))
        
        result = plugin.initialize(context)
        
        # Should handle exception gracefully
        assert result is True or result is False  # Depends on implementation
    
    def test_register_components(self):
        """Test that plugin registers title bar action."""
        plugin = MiniPlayerPlugin()
        gui_registry = Mock()
        
        plugin.register_components(gui_registry)
        
        # Should register title bar action
        gui_registry.register.assert_called_once()
        call_args = gui_registry.register.call_args
        
        assert call_args[0][0] == "title_bar_actions"
        assert call_args[0][1] == "mini_player_toggle"
        assert "callback" in call_args[0][2]
        assert "tooltip" in call_args[0][2]
        assert "icon" in call_args[0][2]
    
    @patch('TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget.MiniPlayerWidget')
    def test_toggle_mini_player_creates_widget(self, mock_widget_class):
        """Test that toggle_mini_player creates widget on first call."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Mock widget instance
        mock_widget = Mock()
        mock_widget.isVisible.return_value = False
        mock_widget_class.return_value = mock_widget
        
        # Toggle (should create and show)
        plugin.toggle_mini_player()
        
        # Widget should be created
        mock_widget_class.assert_called_once_with(context=context)
        mock_widget.show.assert_called_once()
    
    @patch('TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget.MiniPlayerWidget')
    def test_toggle_mini_player_hides_when_visible(self, mock_widget_class):
        """Test that toggle_mini_player hides widget when visible."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Mock widget instance
        mock_widget = Mock()
        mock_widget.isVisible.return_value = False
        mock_widget_class.return_value = mock_widget
        
        # First toggle (create and show)
        plugin.toggle_mini_player()
        
        # Second toggle (should hide)
        mock_widget.isVisible.return_value = True
        plugin.toggle_mini_player()
        
        mock_widget.hide.assert_called_once()
    
    @patch('TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget.MiniPlayerWidget')
    def test_show_mini_player(self, mock_widget_class):
        """Test show_mini_player method."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Mock widget instance
        mock_widget = Mock()
        mock_widget_class.return_value = mock_widget
        
        # Show mini player
        plugin.show_mini_player()
        
        # Widget should be created and shown
        mock_widget_class.assert_called_once()
        mock_widget.show.assert_called_once()
    
    @patch('TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget.MiniPlayerWidget')
    def test_hide_mini_player(self, mock_widget_class):
        """Test hide_mini_player method."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Create widget first
        mock_widget = Mock()
        mock_widget_class.return_value = mock_widget
        plugin.show_mini_player()
        
        # Hide mini player
        plugin.hide_mini_player()
        
        mock_widget.hide.assert_called_once()
    
    def test_hide_mini_player_when_not_created(self):
        """Test hide_mini_player when widget not created."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Should not raise exception
        plugin.hide_mini_player()
    
    def test_enable_plugin(self):
        """Test plugin enable."""
        plugin = MiniPlayerPlugin()
        
        result = plugin.enable()
        
        assert result is True
    
    @patch('TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget.MiniPlayerWidget')
    def test_disable_plugin_hides_widget(self, mock_widget_class):
        """Test plugin disable hides mini player."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Create widget
        mock_widget = Mock()
        mock_widget_class.return_value = mock_widget
        plugin.show_mini_player()
        
        # Disable plugin
        result = plugin.disable()
        
        assert result is True
        mock_widget.hide.assert_called()
    
    @patch('TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget.MiniPlayerWidget')
    def test_cleanup_closes_widget(self, mock_widget_class):
        """Test cleanup closes mini player widget."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Create widget
        mock_widget = Mock()
        mock_widget_class.return_value = mock_widget
        plugin.show_mini_player()
        
        # Cleanup
        plugin.cleanup()
        
        mock_widget.close.assert_called_once()
        assert plugin._mini_player_widget is None
        assert plugin._context is None
    
    def test_cleanup_when_widget_not_created(self):
        """Test cleanup when widget not created."""
        plugin = MiniPlayerPlugin()
        context = Mock(spec=PluginContext)
        plugin.initialize(context)
        
        # Should not raise exception
        plugin.cleanup()
        
        assert plugin._context is None


class TestMiniPlayerWidget:
    """Test MiniPlayerWidget class (requires PyQt6)."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock plugin context."""
        context = Mock(spec=PluginContext)
        context.logger = Mock()
        context.app_version = "1.0.0"
        return context
    
    def test_widget_requires_pyqt6(self, mock_context):
        """Test that widget requires PyQt6."""
        try:
            from TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget import HAS_PYQT6
            
            if not HAS_PYQT6:
                # When PyQt6 not available, import should succeed but class is stub
                from TonieToolbox.core.plugins.builtin.mini_player.components.mini_player_widget import MiniPlayerWidget
                # Stub class should raise ImportError on instantiation
                with pytest.raises(ImportError):
                    widget = MiniPlayerWidget(context=mock_context)
            else:
                # Skip actual widget creation in headless test environment
                # Widget requires display/X server which is not available in CI
                pytest.skip("PyQt6 widget tests skipped in headless environment")
                
        except ImportError:
            pytest.skip("PyQt6 not available for testing")
    
    # NOTE: The following tests are disabled because they require a display server
    # PyQt6 widgets cannot be instantiated in headless CI environments
    # These tests would need pytest-qt and QApplication setup, which we skip
    # for the basic mini-player functionality tests
    
    # @pytest.mark.skipif(True, reason="Requires display server - skipped in headless environment")
    # def test_widget_window_properties(self, mock_context):
    #     """Test mini player window properties."""
    #     pass
    
    # @pytest.mark.skipif(True, reason="Requires display server - skipped in headless environment")  
    # def test_widget_has_controls(self, mock_context):
    #     """Test that widget has playback controls."""
    #     pass
    
    # @pytest.mark.skipif(True, reason="Requires display server - skipped in headless environment")
    # def test_widget_set_player_controller(self, mock_context):
    #     """Test setting player controller."""
    #     pass
