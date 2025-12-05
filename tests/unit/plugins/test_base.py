"""Unit tests for plugin base classes."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from TonieToolbox.core.plugins.base import (
    BasePlugin, GUIPlugin, ProcessorPlugin, IntegrationPlugin, ToolPlugin,
    PluginManifest, PluginMetadata, PluginType, PluginContext
)


class TestPluginManifest:
    """Test PluginManifest class."""
    
    def test_create_manifest(self):
        """Test creating a plugin manifest."""
        metadata = PluginMetadata(
            id="com.test.plugin",
            name="Test Plugin",
            version="1.0.0",
            author="Test Author",
            description="Test Description",
            plugin_type=PluginType.GUI
        )
        manifest = PluginManifest(metadata=metadata)
        
        assert manifest.metadata == metadata
        assert manifest.metadata.id == "com.test.plugin"
        assert manifest.metadata.plugin_type == PluginType.GUI


class TestPluginContext:
    """Test PluginContext class."""
    
    def test_create_context(self):
        """Test creating a plugin context."""
        logger = Mock()
        event_bus = Mock()
        config_manager = Mock()
        plugin_dir = Path("/test/plugin")
        
        context = PluginContext(
            app_version="1.0.0",
            config_manager=config_manager,
            event_bus=event_bus,
            logger=logger,
            plugin_dir=plugin_dir
        )
        
        assert context.app_version == "1.0.0"
        assert context.logger == logger
        assert context.event_bus == event_bus
        assert context.config_manager == config_manager
        assert context.plugin_dir == plugin_dir
    
    def test_get_cache_dir_basic(self):
        """Test get_cache_dir returns correct path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock Path.home()
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                context = PluginContext(
                    app_version="1.0.0",
                    config_manager=None,
                    event_bus=Mock(),
                    logger=Mock(),
                    plugin_dir=Path("/test")
                )
                
                # Set plugin namespace
                context.set_plugin_namespace("com.author.my_plugin")
                
                # Get cache dir
                cache_dir = context.get_cache_dir()
                
                # Should be ~/.tonietoolbox/cache/my_plugin
                expected = temp_path / '.tonietoolbox' / 'cache' / 'my_plugin'
                assert cache_dir == expected
                assert cache_dir.exists()  # Should be created by default
    
    def test_get_cache_dir_with_config_manager(self):
        """Test get_cache_dir uses config manager settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            custom_config = temp_path / 'custom_config'
            
            # Mock config manager
            config_manager = Mock()
            config_manager.get_setting.return_value = str(custom_config)
            
            context = PluginContext(
                app_version="1.0.0",
                config_manager=config_manager,
                event_bus=Mock(),
                logger=Mock(),
                plugin_dir=Path("/test")
            )
            
            context.set_plugin_namespace("com.author.my_plugin")
            
            # Get cache dir
            cache_dir = context.get_cache_dir()
            
            # Should use config directory
            expected = custom_config / 'cache' / 'my_plugin'
            assert cache_dir == expected
            assert cache_dir.exists()
    
    def test_get_cache_dir_without_namespace(self):
        """Test get_cache_dir raises error when plugin namespace not set."""
        context = PluginContext(
            app_version="1.0.0",
            config_manager=None,
            event_bus=Mock(),
            logger=Mock(),
            plugin_dir=Path("/test")
        )
        
        # Should raise ValueError without namespace
        with pytest.raises(ValueError, match="Plugin ID not set"):
            context.get_cache_dir()
    
    def test_get_cache_dir_with_explicit_plugin_id(self):
        """Test get_cache_dir with explicit plugin_id parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                context = PluginContext(
                    app_version="1.0.0",
                    config_manager=None,
                    event_bus=Mock(),
                    logger=Mock(),
                    plugin_dir=Path("/test")
                )
                
                # Get cache dir with explicit plugin_id (no namespace needed)
                cache_dir = context.get_cache_dir(plugin_id="com.other.plugin")
                
                expected = temp_path / '.tonietoolbox' / 'cache' / 'plugin'
                assert cache_dir == expected
    
    def test_get_cache_dir_no_create(self):
        """Test get_cache_dir with ensure_exists=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                context = PluginContext(
                    app_version="1.0.0",
                    config_manager=None,
                    event_bus=Mock(),
                    logger=Mock(),
                    plugin_dir=Path("/test")
                )
                
                context.set_plugin_namespace("com.author.my_plugin")
                
                # Get cache dir without creating
                cache_dir = context.get_cache_dir(ensure_exists=False)
                
                # Should not exist
                assert not cache_dir.exists()
    
    def test_get_data_dir_basic(self):
        """Test get_data_dir returns correct path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                context = PluginContext(
                    app_version="1.0.0",
                    config_manager=None,
                    event_bus=Mock(),
                    logger=Mock(),
                    plugin_dir=Path("/test")
                )
                
                context.set_plugin_namespace("com.author.my_plugin")
                
                # Get data dir
                data_dir = context.get_data_dir()
                
                # Should be ~/.tonietoolbox/data/my_plugin
                expected = temp_path / '.tonietoolbox' / 'data' / 'my_plugin'
                assert data_dir == expected
                assert data_dir.exists()
    
    def test_get_data_dir_with_config_manager(self):
        """Test get_data_dir uses config manager settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            custom_config = temp_path / 'custom_config'
            
            config_manager = Mock()
            config_manager.get_setting.return_value = str(custom_config)
            
            context = PluginContext(
                app_version="1.0.0",
                config_manager=config_manager,
                event_bus=Mock(),
                logger=Mock(),
                plugin_dir=Path("/test")
            )
            
            context.set_plugin_namespace("com.author.my_plugin")
            
            # Get data dir
            data_dir = context.get_data_dir()
            
            # Should use config directory
            expected = custom_config / 'data' / 'my_plugin'
            assert data_dir == expected
            assert data_dir.exists()
    
    def test_get_data_dir_invalid_plugin_id(self):
        """Test get_data_dir with invalid plugin ID format."""
        context = PluginContext(
            app_version="1.0.0",
            config_manager=None,
            event_bus=Mock(),
            logger=Mock(),
            plugin_dir=Path("/test")
        )
        
        # Should raise ValueError with invalid ID format
        with pytest.raises(ValueError, match="Invalid plugin ID format"):
            context.get_data_dir(plugin_id="invalid_id")


class ConcretePlugin(BasePlugin):
    """Concrete plugin implementation for testing."""
    
    def __init__(self):
        super().__init__()
        self.initialized = False
        self.enabled = False
    
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            metadata=PluginMetadata(
                id="com.test.concrete",
                name="Concrete Plugin",
                version="1.0.0",
                author="Test",
                description="Test plugin",
                plugin_type=PluginType.TOOL
            )
        )
    
    def initialize(self, context: PluginContext) -> bool:
        self._context = context
        self.initialized = True
        return True


class TestBasePlugin:
    """Test BasePlugin class."""
    
    def test_plugin_lifecycle(self):
        """Test plugin lifecycle: initialize → enable → disable → cleanup."""
        plugin = ConcretePlugin()
        context = PluginContext(
            app_version="1.0.0",
            config_manager=Mock(),
            event_bus=Mock(),
            logger=Mock(),
            plugin_dir=Path("/test")
        )
        
        # Initial state
        assert not plugin.is_enabled
        
        # Initialize
        assert plugin.initialize(context) is True
        assert plugin.initialized is True
        
        # Enable
        assert plugin.enable() is True
        assert plugin.is_enabled is True
        
        # Disable
        assert plugin.disable() is True
        assert plugin.is_enabled is False
        
        # Cleanup
        plugin.cleanup()
        # Note: cleanup() may or may not set _context to None depending on implementation
    
    def test_get_manifest(self):
        """Test getting plugin manifest."""
        plugin = ConcretePlugin()
        manifest = plugin.get_manifest()
        
        assert isinstance(manifest, PluginManifest)
        assert manifest.metadata.id == "com.test.concrete"
        assert manifest.metadata.plugin_type == PluginType.TOOL


class TestGUIPlugin:
    """Test GUIPlugin class."""
    
    def test_gui_plugin_has_register_components(self):
        """Test that GUIPlugin has register_components method."""
        class TestGUIPlugin(GUIPlugin):
            def get_manifest(self):
                return PluginManifest(
                    metadata=PluginMetadata(
                        id="com.test.gui",
                        name="Test GUI",
                        version="1.0.0",
                        author="Test",
                        description="Test",
                        plugin_type=PluginType.GUI
                    )
                )
            
            def initialize(self, context):
                return True
            
            def register_components(self, gui_registry):
                gui_registry.register("test", "item", {})
        
        plugin = TestGUIPlugin()
        assert hasattr(plugin, 'register_components')
        
        registry = Mock()
        plugin.register_components(registry)
        registry.register.assert_called_once_with("test", "item", {})


class TestProcessorPlugin:
    """Test ProcessorPlugin class."""
    
    def test_processor_plugin_has_register_processors(self):
        """Test that ProcessorPlugin has register_processors method."""
        class TestProcessorPlugin(ProcessorPlugin):
            def get_manifest(self):
                return PluginManifest(
                    metadata=PluginMetadata(
                        id="com.test.processor",
                        name="Test Processor",
                        version="1.0.0",
                        author="Test",
                        description="Test",
                        plugin_type=PluginType.PROCESSOR
                    )
                )
            
            def initialize(self, context):
                return True
            
            def register_processors(self, processor_registry):
                processor_registry.register("test", Mock())
        
        plugin = TestProcessorPlugin()
        assert hasattr(plugin, 'register_processors')
        
        registry = Mock()
        plugin.register_processors(registry)
        registry.register.assert_called_once()


class TestIntegrationPlugin:
    """Test IntegrationPlugin class."""
    
    def test_integration_plugin_has_register_integration(self):
        """Test that IntegrationPlugin has register_integration method."""
        class TestIntegrationPlugin(IntegrationPlugin):
            def get_manifest(self):
                return PluginManifest(
                    metadata=PluginMetadata(
                        id="com.test.integration",
                        name="Test Integration",
                        version="1.0.0",
                        author="Test",
                        description="Test",
                        plugin_type=PluginType.INTEGRATION
                    )
                )
            
            def initialize(self, context):
                return True
            
            def register_integration(self, integration_registry):
                integration_registry.register("test", Mock())
        
        plugin = TestIntegrationPlugin()
        assert hasattr(plugin, 'register_integration')
        
        registry = Mock()
        plugin.register_integration(registry)
        registry.register.assert_called_once()


class TestToolPlugin:
    """Test ToolPlugin class."""
    
    def test_tool_plugin_lifecycle(self):
        """Test ToolPlugin lifecycle."""
        class TestToolPlugin(ToolPlugin):
            def get_manifest(self):
                return PluginManifest(
                    metadata=PluginMetadata(
                        id="com.test.tool",
                        name="Test Tool",
                        version="1.0.0",
                        author="Test",
                        description="Test",
                        plugin_type=PluginType.TOOL
                    )
                )
            
            def initialize(self, context):
                self._context = context
                return True
            
            def register_tool(self, tool_registry):
                """Register test tool."""
                pass
        
        plugin = TestToolPlugin()
        context = PluginContext(
            app_version="1.0.0",
            config_manager=Mock(),
            event_bus=Mock(),
            logger=Mock(),
            plugin_dir=Path("/test")
        )
        
        assert plugin.initialize(context) is True
        assert plugin._context == context
