#!/usr/bin/env python3
"""
Unit tests for ConfigManager.

Tests cover configuration loading, saving, validation, and access patterns.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from TonieToolbox.core.config.manager import ConfigManager
from TonieToolbox.core.config.settings_registry import SETTINGS_REGISTRY


class TestConfigManagerInitialization:
    """Test ConfigManager initialization and file handling."""
    
    def test_initialization_with_default_path(self):
        """Test manager initializes with default config path."""
        with patch('os.path.exists', return_value=False):
            with patch.object(ConfigManager, 'create_default_config'):
                manager = ConfigManager()
                assert manager.config_file is not None
                assert manager.config_file.endswith('config.json')
    
    def test_initialization_with_custom_path(self):
        """Test manager initializes with custom config path."""
        custom_path = "/custom/path/config.json"
        with patch('os.path.exists', return_value=False):
            with patch.object(ConfigManager, 'create_default_config'):
                manager = ConfigManager(config_file=custom_path)
                assert manager.config_file == custom_path
    
    def test_loads_existing_config(self):
        """Test manager loads existing config file."""
        test_config = {"logging": {"level": "DEBUG"}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_file=temp_path)
            loaded_config = manager.load_config()
            assert loaded_config is not None
            assert "logging" in loaded_config
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_creates_config_if_missing(self):
        """Test manager creates default config if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent" / "config.json"
            manager = ConfigManager(config_file=str(config_path))
            assert config_path.exists()


class TestConfigManagerSettings:
    """Test getting and setting configuration values."""
    
    @pytest.fixture
    def manager(self):
        """Create a config manager with temporary file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"logging": {"level": "INFO"}}, f)
            temp_path = f.name
        
        manager = ConfigManager(config_file=temp_path)
        yield manager
        Path(temp_path).unlink(missing_ok=True)
    
    def test_get_existing_setting(self, manager):
        """Test retrieving an existing setting."""
        value = manager.get_setting("application.logging.level")
        assert value == "INFO"
    
    def test_get_valid_setting_path(self, manager):
        """Test getting valid setting from registry."""
        # Get a setting that should exist with default
        value = manager.get_setting("application.logging.level")
        assert value is not None
    
    def test_set_and_get_setting(self, manager):
        """Test setting and retrieving a value."""
        manager.set_setting("application.logging.level", "DEBUG")
        assert manager.get_setting("application.logging.level") == "DEBUG"
    
    def test_set_valid_setting_succeeds(self, manager):
        """Test setting valid value returns True."""
        result = manager.set_setting("application.logging.level", "DEBUG")
        assert result is True


class TestConfigManagerAccessors:
    """Test typed configuration accessors."""
    
    @pytest.fixture
    def manager(self):
        """Create a config manager."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "logging": {"level": "INFO"},
                "teddycloud": {"enabled": True, "host": "localhost"},
                "gui": {"theme": "default"}
            }
            json.dump(config, f)
            temp_path = f.name
        
        manager = ConfigManager(config_file=temp_path)
        yield manager
        Path(temp_path).unlink(missing_ok=True)
    
    def test_logging_accessor(self, manager):
        """Test logging configuration accessor."""
        logging_config = manager.logging
        assert logging_config is not None
        assert logging_config.level == "INFO"
    
    def test_config_accessors_exist(self, manager):
        """Test configuration accessors are available."""
        assert hasattr(manager, 'logging')
        assert manager.logging is not None
    
    def test_multiple_accessors(self, manager):
        """Test multiple configuration accessors."""
        assert hasattr(manager, 'logging')
        assert hasattr(manager, 'gui')
        assert manager.logging is not None


class TestConfigManagerPersistence:
    """Test configuration file saving and loading."""
    
    def test_save_config_creates_directory(self):
        """Test save_config creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "new" / "dir" / "config.json"
            manager = ConfigManager(config_file=str(config_path))
            manager.set_setting("application.logging.level", "DEBUG")
            result = manager.save_config()
            
            assert result is True
            assert config_path.exists()
            assert config_path.parent.exists()
    
    def test_save_and_reload_config(self):
        """Test saving and reloading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "config.json"
            
            # Create, modify, and save
            manager1 = ConfigManager(config_file=str(temp_path))
            # Use a non-initial setting that will persist correctly
            manager1.set_setting("processing.audio.default_bitrate", 256)
            result = manager1.save_config()
            assert result is True
            
            # Verify file was created
            assert temp_path.exists()
            
            # Reload in new instance
            manager2 = ConfigManager(config_file=str(temp_path))
            assert manager2.get_setting("processing.audio.default_bitrate") == 256
    
    def test_save_minimal_config(self):
        """Test save_config only saves non-default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            manager = ConfigManager(config_file=str(config_path))
            
            # Only set one value different from default
            manager.set_setting("application.logging.level", "DEBUG")
            manager.save_config()
            
            # Read saved file
            with open(config_path) as f:
                saved_config = json.load(f)
            
            # Should contain application section
            assert "application" in saved_config
            # Should not contain all possible settings
            assert len(saved_config) < len(SETTINGS_REGISTRY)


class TestConfigManagerReset:
    """Test configuration reset functionality."""
    
    def test_create_default_config(self):
        """Test creating default configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            manager = ConfigManager(config_file=str(config_path))
            
            # Should create default config
            assert config_path.exists()
            
            # Should have initial settings
            loaded = manager.load_config()
            assert loaded is not None
            assert "application" in loaded


class TestConfigManagerValidation:
    """Test configuration validation."""
    
    def test_validate_on_set(self):
        """Test validation occurs when setting values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_file=temp_path)
            
            # Valid value should work
            result = manager.set_setting("application.logging.level", "DEBUG")
            assert result is True
            
            # Invalid value should return False
            result = manager.set_setting("application.logging.level", 12345)
            assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_config_file_path_property(self):
        """Test config_file_path property."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = ConfigManager(config_file=temp_path)
            assert manager.config_file_path == temp_path
        finally:
            Path(temp_path).unlink(missing_ok=True)
