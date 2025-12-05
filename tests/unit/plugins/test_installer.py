"""Unit tests for plugin installer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import shutil
import tempfile

from TonieToolbox.core.plugins.installer import PluginInstaller
from TonieToolbox.core.plugins.base import PluginManifest, PluginMetadata, PluginType


class TestPluginInstaller:
    """Test PluginInstaller class."""
    
    @pytest.fixture
    def temp_install_dir(self):
        """Create a temporary installation directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock plugin repository."""
        return Mock()
    
    @pytest.fixture
    def installer(self, temp_install_dir, mock_repository):
        """Create a PluginInstaller instance."""
        return PluginInstaller(
            install_base_dir=temp_install_dir,
            repository=mock_repository
        )
    
    def test_initialization(self, temp_install_dir, mock_repository):
        """Test PluginInstaller initialization."""
        installer = PluginInstaller(
            install_base_dir=temp_install_dir,
            repository=mock_repository
        )
        
        assert installer.install_base_dir == temp_install_dir
        assert installer.repository == mock_repository
        assert temp_install_dir.exists()
    
    def test_uninstall_success(self, installer, temp_install_dir):
        """Test successful plugin uninstallation."""
        # Create a fake plugin directory
        author_dir = temp_install_dir / "testauthor"
        plugin_dir = author_dir / "testplugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.py").write_text("# test plugin")
        
        # Uninstall
        result = installer.uninstall("testauthor", "testplugin")
        
        assert result is True
        assert not plugin_dir.exists()
    
    def test_uninstall_removes_empty_author_dir(self, installer, temp_install_dir):
        """Test that uninstall removes empty author directory."""
        # Create a fake plugin directory
        author_dir = temp_install_dir / "testauthor"
        plugin_dir = author_dir / "testplugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.py").write_text("# test plugin")
        
        # Uninstall
        result = installer.uninstall("testauthor", "testplugin")
        
        assert result is True
        assert not plugin_dir.exists()
        assert not author_dir.exists()  # Should be removed since it's empty
    
    def test_uninstall_keeps_nonempty_author_dir(self, installer, temp_install_dir):
        """Test that uninstall keeps author directory with other plugins."""
        # Create two plugins from same author
        author_dir = temp_install_dir / "testauthor"
        plugin1_dir = author_dir / "plugin1"
        plugin2_dir = author_dir / "plugin2"
        plugin1_dir.mkdir(parents=True)
        plugin2_dir.mkdir(parents=True)
        (plugin1_dir / "plugin.py").write_text("# plugin1")
        (plugin2_dir / "plugin.py").write_text("# plugin2")
        
        # Uninstall only plugin1
        result = installer.uninstall("testauthor", "plugin1")
        
        assert result is True
        assert not plugin1_dir.exists()
        assert author_dir.exists()  # Should still exist
        assert plugin2_dir.exists()  # Other plugin still there
    
    def test_uninstall_nonexistent_plugin(self, installer):
        """Test uninstalling non-existent plugin."""
        result = installer.uninstall("nonexistent", "plugin")
        
        assert result is False
    
    def test_uninstall_with_cache_removal(self, installer, temp_install_dir, temp_cache_dir):
        """Test plugin uninstallation removes cache directory."""
        # Create a fake plugin directory
        author_dir = temp_install_dir / "testauthor"
        plugin_dir = author_dir / "testplugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.py").write_text("# test plugin")
        
        # Create a fake cache directory
        cache_dir = temp_cache_dir / "testplugin"
        cache_dir.mkdir(parents=True)
        (cache_dir / "cache_file.json").write_text('{"data": "test"}')
        
        # Mock Path.home() to return temp directory
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = temp_cache_dir.parent
            
            # Create .tonietoolbox/cache structure
            tonietoolbox_dir = temp_cache_dir.parent / '.tonietoolbox' / 'cache'
            tonietoolbox_dir.mkdir(parents=True, exist_ok=True)
            plugin_cache = tonietoolbox_dir / 'testplugin'
            plugin_cache.mkdir(parents=True, exist_ok=True)
            (plugin_cache / 'cache.json').write_text('{"cached": true}')
            
            # Uninstall with plugin_id
            result = installer.uninstall("testauthor", "testplugin", plugin_id="com.testauthor.testplugin")
            
            assert result is True
            assert not plugin_dir.exists()
            assert not plugin_cache.exists()  # Cache should be removed
    
    def test_remove_plugin_cache_simple_name(self, installer):
        """Test _remove_plugin_cache with standard plugin name format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock Path.home()
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                # Create cache directory structure
                cache_base = temp_path / '.tonietoolbox' / 'cache'
                cache_base.mkdir(parents=True)
                plugin_cache = cache_base / 'my_plugin'
                plugin_cache.mkdir()
                (plugin_cache / 'data.json').write_text('{}')
                
                # Remove cache
                installer._remove_plugin_cache("com.author.my_plugin")
                
                # Cache should be removed
                assert not plugin_cache.exists()
    
    def test_remove_plugin_cache_no_cache_dir(self, installer):
        """Test _remove_plugin_cache when cache directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock Path.home()
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                # Don't create cache directory
                
                # Should not raise exception
                installer._remove_plugin_cache("com.author.my_plugin")
    
    def test_remove_plugin_cache_invalid_plugin_id(self, installer):
        """Test _remove_plugin_cache with invalid plugin ID format."""
        # Should not raise exception with invalid ID
        installer._remove_plugin_cache("invalid_id")
    
    def test_remove_plugin_cache_handles_errors(self, installer):
        """Test _remove_plugin_cache handles errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock Path.home()
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                
                # Create cache directory
                cache_base = temp_path / '.tonietoolbox' / 'cache'
                cache_base.mkdir(parents=True)
                plugin_cache = cache_base / 'my_plugin'
                plugin_cache.mkdir()
                
                # Mock shutil.rmtree to raise exception
                with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
                    # Should not raise exception, just log warning
                    installer._remove_plugin_cache("com.author.my_plugin")
    
    def test_uninstall_without_plugin_id_skips_cache_removal(self, installer, temp_install_dir):
        """Test uninstall without plugin_id parameter doesn't attempt cache removal."""
        # Create a fake plugin directory
        author_dir = temp_install_dir / "testauthor"
        plugin_dir = author_dir / "testplugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.py").write_text("# test plugin")
        
        # Mock _remove_plugin_cache to track if it's called
        with patch.object(installer, '_remove_plugin_cache') as mock_remove_cache:
            # Uninstall without plugin_id
            result = installer.uninstall("testauthor", "testplugin")
            
            assert result is True
            # _remove_plugin_cache should not be called
            mock_remove_cache.assert_not_called()
    
    def test_uninstall_exception_handling(self, installer, temp_install_dir):
        """Test uninstall handles exceptions during directory removal."""
        # Create a fake plugin directory
        author_dir = temp_install_dir / "testauthor"
        plugin_dir = author_dir / "testplugin"
        plugin_dir.mkdir(parents=True)
        
        # Mock shutil.rmtree to raise exception
        with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
            result = installer.uninstall("testauthor", "testplugin")
            
            assert result is False
