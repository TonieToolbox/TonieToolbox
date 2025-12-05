#!/usr/bin/python3
"""
Base classes for integration management.
These classes provide common functionality and eliminate code duplication across platform integrations.
"""
import os
import sys
import json
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ...utils import get_logger
from ..completion import CompletionInstaller

logger = get_logger(__name__)


class BaseIntegration(ABC):
    """
    Enhanced base class for all platform-specific integrations.
    Eliminates duplication by providing common functionality shared across all platforms.
    """
    
    def __init__(self):
        """Initialize common integration components."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.exe_path = self._find_executable()
        self.output_dir = os.path.join(os.path.expanduser('~'), '.tonietoolbox')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Platform-specific paths - to be set by subclasses
        self.icon_path = None
        self._setup_platform_paths()
        
        # Configuration management
        self.config = self._load_or_create_config()
        self.log_level = self.config.get('log_level', 'SILENT')
        self.log_to_file = self.config.get('log_to_file', False)
        
        # Upload configuration
        self.upload_config = UploadConfiguration(self.config.get('upload', {}))
        
        # Shell completion installer
        self.completion_installer = CompletionInstaller()
        
        # Platform-specific setup
        self._extract_icon_if_needed()
        
        self.logger.debug("Integration initialized successfully")
        self.logger.debug("Upload enabled: %s", self.upload_config.is_enabled)
        self.logger.debug("Upload URL: %s", self.upload_config.url)
        self.logger.debug("Authentication: %s", self.upload_config.auth_type)
    
    @abstractmethod
    def _setup_platform_paths(self):
        """Set up platform-specific paths. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def install(self) -> bool:
        """Install the integration. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def uninstall(self) -> bool:
        """Uninstall the integration. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _extract_icon_if_needed(self):
        """Extract icon if needed. Platform-specific implementation."""
        pass
    
    def install_shell_completions(self) -> bool:
        """Install shell completion scripts for detected shells."""
        self.logger.debug("Installing shell completion scripts...")
        try:
            success = self.completion_installer.install_completions()
            if success:
                self.logger.info("Shell completions installed successfully")
            return success
        except Exception as e:
            self.logger.warning("Failed to install shell completions: %s", e)
            return False
    
    def uninstall_shell_completions(self) -> bool:
        """Remove shell completion scripts."""
        self.logger.debug("Removing shell completion scripts...")
        try:
            success = self.completion_installer.uninstall_completions()
            if success:
                self.logger.info("Shell completions removed successfully")
            return success
        except Exception as e:
            self.logger.warning("Failed to remove shell completions: %s", e)
            return False
    
    def _find_executable(self) -> str:
        """Find the tonietoolbox executable across different platforms."""
        if sys.platform.startswith('win'):
            possible_paths = [
                os.path.join(sys.prefix, 'Scripts', 'tonietoolbox.exe'),
                os.path.join(sys.exec_prefix, 'Scripts', 'tonietoolbox.exe'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Programs', 'Python', 'Python*', 'Scripts', 'tonietoolbox.exe'),
                os.path.join('C:', 'Program Files', 'Python*', 'Scripts', 'tonietoolbox.exe'),
                os.path.join('C:', 'Program Files (x86)', 'Python*', 'Scripts', 'tonietoolbox.exe'),
                os.path.join(os.path.expanduser('~'), '.local', 'bin', 'tonietoolbox.exe')
            ]
            commands = ['where', 'tonietoolbox']
            alt_commands = ['where', 'tonietoolbox.exe']
            fallback = os.path.join(sys.prefix, 'Scripts', 'tonietoolbox.exe')
        elif sys.platform == 'darwin':
            possible_paths = [os.path.join(sys.prefix, 'bin', 'tonietoolbox')]
            commands = ['which', 'tonietoolbox']
            alt_commands = None
            fallback = os.path.join(sys.prefix, 'bin', 'tonietoolbox')
        else:  # Linux
            possible_paths = [
                os.path.join(sys.prefix, 'bin', 'tonietoolbox'),
                '/usr/local/bin/tonietoolbox',
                '/usr/bin/tonietoolbox',
                os.path.expanduser('~/.local/bin/tonietoolbox')
            ]
            commands = ['which', 'tonietoolbox']
            alt_commands = None
            fallback = 'tonietoolbox'
        
        # Check possible paths with glob support
        import glob
        for path_pattern in possible_paths:
            if '*' in path_pattern:
                matches = glob.glob(path_pattern)
                for path in matches:
                    if os.path.isfile(path) and os.access(path, os.X_OK):
                        return path
            else:
                if os.path.isfile(path_pattern) and os.access(path_pattern, os.X_OK):
                    return path_pattern
        
        # Try system commands
        try:
            result = subprocess.run(commands, capture_output=True, text=True, 
                                  shell=sys.platform.startswith('win'))
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        # Try alternative commands
        if alt_commands:
            try:
                result = subprocess.run(alt_commands, capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
            except:
                pass
        
        return fallback
    
    def _load_or_create_config(self) -> Dict[str, Any]:
        """Load existing config or create default configuration dynamically."""
        config_path = os.path.join(self.output_dir, 'config.json')
        
        if not os.path.exists(config_path):
            # Use unified config system to create minimal config
            from ...config import get_config_manager
            config_manager = get_config_manager(config_path)
            return config_manager.load_config()
        else:
            return self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    self.logger.debug("Config file is empty, using minimal config")
                    from ...config.settings_registry import build_minimal_config
                    return build_minimal_config()
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning("Error loading config file: %s, using minimal config", e)
            from ...config.settings_registry import build_minimal_config
            return build_minimal_config()
    
    def _escape_path_for_platform(self, path: str) -> str:
        """Escape paths for platform-specific use. Override in subclasses if needed."""
        return path
    
    def get_log_level_arg(self) -> str:
        """Get the log level argument based on configuration."""
        level = str(self.log_level).strip().upper()
        log_level_map = {
            'DEBUG': '--debug',
            'TRACE': '--trace',
            'INFO': '',  # Default level
            'SILENT': '--silent',
            'QUIET': '--quiet'
        }
        return log_level_map.get(level, '')


class UploadConfiguration:
    """Manages upload configuration for integrations."""
    
    def __init__(self, upload_config: Dict[str, Any]):
        self.config = upload_config
        self.logger = get_logger(f"{__name__}.UploadConfiguration")
        
        # Parse configuration
        self.urls = upload_config.get('url', [])
        self.url = self.urls[0] if self.urls else ''
        self.ignore_ssl_verify = upload_config.get('ignore_ssl_verify', False)
        self.username = upload_config.get('username', '')
        self.password = upload_config.get('password', '')
        self.client_cert_path = upload_config.get('client_cert_path', '')
        self.client_cert_key_path = upload_config.get('client_cert_key_path', '')
        
        # Determine authentication type
        self.has_basic_auth = bool(self.username and self.password)
        self.has_client_cert = bool(self.client_cert_path and self.client_cert_key_path)
        
        # Validate configuration
        if self.has_basic_auth and self.has_client_cert:
            self.logger.warning("Both client certificate and basic authentication are set. "
                              "Only one can be used. Using client certificate.")
            self.has_basic_auth = False
        
        self.is_enabled = bool(self.url)
    
    @property
    def auth_type(self) -> str:
        """Get the authentication type as a string."""
        if self.has_client_cert:
            return "Client Certificate"
        elif self.has_basic_auth:
            return "Basic Authentication"
        elif self.is_enabled:
            return "None"
        else:
            return "Disabled"
    
    def get_basic_auth_args(self) -> str:
        """Get basic authentication arguments for CLI."""
        if self.has_basic_auth:
            return f'--username {self.username} --password {self.password}'
        return ''
    
    def get_client_cert_args(self, escape_func=None) -> str:
        """Get client certificate arguments for CLI."""
        if self.has_client_cert:
            cert_path = escape_func(self.client_cert_path) if escape_func else self.client_cert_path
            key_path = escape_func(self.client_cert_key_path) if escape_func else self.client_cert_key_path
            return f'--client-cert "{cert_path}" --client-key "{key_path}"'
        return ''
    
    def get_auth_args(self, escape_func=None) -> str:
        """Get authentication arguments for CLI."""
        if self.has_client_cert:
            return self.get_client_cert_args(escape_func)
        elif self.has_basic_auth:
            return self.get_basic_auth_args()
        return ''


class CommandBuilder:
    """Builds CLI commands for integrations."""
    
    def __init__(self, exe_path: str, upload_config: UploadConfiguration, 
                 log_level: str, log_to_file: bool):
        self.exe_path = exe_path
        self.upload_config = upload_config
        self.log_level = log_level
        self.log_to_file = log_to_file
        self.logger = get_logger(f"{__name__}.CommandBuilder")
    
    def build_base_command(self, **options) -> List[str]:
        """Build the base command with common options."""
        cmd = [self.exe_path]
        
        # Add log level
        if self.log_level:
            log_arg = self._get_log_level_arg()
            if log_arg:
                cmd.append(log_arg)
        
        # Add log to file
        if self.log_to_file:
            cmd.append('--log-file')
        
        # Add recursive flag
        if options.get('is_recursive', False):
            cmd.append('--recursive')
        
        # Always use output to source for integrations
        cmd.append('--output-to-source')
        
        # Add operation-specific flags
        if options.get('use_info', False):
            cmd.append('--info')
        
        if options.get('use_play', False):
            cmd.append('--play')
        
        if options.get('is_split', False):
            cmd.append('--split')
        
        # Add upload configuration
        if options.get('use_upload', False) and self.upload_config.is_enabled:
            cmd.extend(['--upload', f'"{self.upload_config.url}"'])
            
            auth_args = self.upload_config.get_auth_args(options.get('escape_func'))
            if auth_args:
                cmd.append(auth_args)
            
            if self.upload_config.ignore_ssl_verify:
                cmd.append('--ignore-ssl-verify')
        
        # Add additional options
        if options.get('use_artwork', False):
            cmd.append('--include-artwork')
        
        if options.get('use_json', False):
            cmd.append('--create-custom-json')
        
        return cmd
    
    def _get_log_level_arg(self) -> str:
        """Get the log level argument."""
        level = str(self.log_level).strip().upper()
        log_level_map = {
            'DEBUG': '--debug',
            'TRACE': '--trace',
            'INFO': '',  # Default level
            'SILENT': '--silent',
            'QUIET': '--quiet'
        }
        return log_level_map.get(level, '')