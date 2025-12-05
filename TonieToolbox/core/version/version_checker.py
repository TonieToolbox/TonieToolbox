#!/usr/bin/python3
"""
Version checking and update management for TonieToolbox.

This module provides secure, configurable version checking with caching,
retry logic, and proper error handling.
"""
import json
import os
import ssl
import subprocess
import sys
import time
from typing import Tuple, Optional, Callable
from urllib import request
from urllib.error import URLError
import urllib.request

from packaging import version
from ..utils.logging import get_logger
from ... import __version__
from ..config import ConfigManager


class VersionCheckError(Exception):
    """Base exception for version checking errors.
    
    Root exception for all errors related to version checking, including
    network failures, cache issues, and parsing errors.
    
    Example:
        Generic version check error::
        
            raise VersionCheckError("Invalid version format in response")
        
        Catching all version check errors::
        
            try:
                latest_version = checker.check_for_updates()
            except VersionCheckError as e:
                logger.warning(f"Version check failed: {e}")
                # Continue with current version
    """
    pass


class NetworkError(VersionCheckError):
    """Network-related version check error.
    
    Raised when version checking fails due to network issues such as
    connection timeouts, DNS failures, or HTTP errors.
    
    Example:
        Connection timeout::
        
            try:
                response = requests.get(VERSION_URL, timeout=5)
            except requests.Timeout:
                raise NetworkError("Version check timed out")
        
        HTTP error::
        
            if response.status_code != 200:
                raise NetworkError(
                    f"Version check failed with HTTP {response.status_code}"
                )
    """
    pass


class CacheError(VersionCheckError):
    """Cache-related error.
    
    Raised when version cache cannot be read, written, or is corrupted.
    
    Example:
        Cache write failure::
        
            try:
                cache_file.write_text(json.dumps(version_data))
            except OSError as e:
                raise CacheError(f"Cannot write version cache: {e}")
        
        Corrupted cache::
        
            try:
                cached_data = json.loads(cache_file.read_text())
            except json.JSONDecodeError:
                raise CacheError("Version cache is corrupted")
    """
    pass


class VersionChecker:
    """
    Main class for handling version checking and updates.
    
    Features:
    - Secure HTTPS requests with proper SSL verification
    - Configurable caching with expiration
    - Retry logic for network failures
    - Proper error handling and logging
    - Non-blocking operation mode
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize version checker.
        
        Args:
            config: Configuration manager instance
        """
        self.config_manager = config
        self.logger = get_logger(__name__)
    
    @property 
    def cache_enabled(self) -> bool:
        """Whether caching is enabled."""
        return True  # Always enable caching with new system
    
    @property
    def cache_file(self) -> str:
        """Path to version cache file."""
        from ..config import TONIETOOLBOX_HOME
        import os
        return os.path.join(TONIETOOLBOX_HOME, "version_cache.json")
    
    @property
    def cache_dir(self) -> str:
        """Cache directory path."""
        from ..config import TONIETOOLBOX_HOME
        return TONIETOOLBOX_HOME
    
    @property
    def cache_expiry(self) -> int:
        """Cache expiry time in seconds."""
        return self.config_manager.get_setting("application.version.cache_expiry")
    
    @property
    def max_retries(self) -> int:
        """Maximum retry attempts."""
        return self.config_manager.get_setting("application.version.max_retries")
    
    @property
    def retry_delay(self) -> int:
        """Delay between retries."""
        return self.config_manager.get_setting("application.version.retry_delay")
    
    @property
    def timeout(self) -> int:
        """Network timeout."""
        return self.config_manager.get_setting("application.version.timeout")
    
    @property
    def pypi_url(self) -> str:
        """PyPI URL for version checking."""
        return self.config_manager.get_setting("application.version.pypi_url")
    
    @property
    def notify_if_not_latest(self) -> bool:
        """Whether to notify if not latest version."""
        return self.config_manager.version.notify_if_not_latest
    
    @property
    def auto_update(self) -> bool:
        """Whether auto-update is enabled."""
        return self.config_manager.version.auto_update
    
    def _create_secure_request(self, url: str) -> urllib.request.Request:
        """Create a secure request with proper headers."""
        headers = {
            'User-Agent': f'TonieToolbox/{__version__}',
            'Accept': 'application/json'
        }
        return urllib.request.Request(url, headers=headers)
    
    def _get_ssl_context(self) -> ssl.SSLContext:
        """Create secure SSL context."""
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    
    def _load_cache(self) -> Optional[dict]:
        """
        Load version cache from file.
        
        Returns:
            Cache data dictionary or None if cache is invalid/missing
        """
        if not self.cache_enabled:
            return None
            
        if not os.path.exists(self.cache_file):
            self.logger.debug("No cache file found")
            return None
        
        try:
            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)
            
            # Validate cache structure
            if not isinstance(cache_data, dict) or 'version' not in cache_data or 'timestamp' not in cache_data:
                raise CacheError("Invalid cache structure")
            
            cache_age = time.time() - cache_data.get('timestamp', 0)
            if cache_age >= self.cache_expiry:
                self.logger.debug("Cache expired (%d seconds old)", cache_age)
                return None
            
            self.logger.debug("Using cached version info: %s (age: %d seconds)", 
                            cache_data['version'], cache_age)
            return cache_data
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.debug("Cache file corrupt: %s", e)
            return None
        except Exception as e:
            self.logger.debug("Error loading cache: %s", e)
            return None
    
    def _save_cache(self, version_info: str) -> None:
        """
        Save version information to cache.
        
        Args:
            version_info: Version string to cache
        """
        if not self.cache_enabled:
            return
            
        try:
            # Ensure cache directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            cache_data = {
                "version": version_info,
                "timestamp": time.time(),
                "check_count": 1
            }
            
            with open(self.cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            
            self.logger.debug("Updated cache: %s", cache_data)
            
        except Exception as e:
            self.logger.debug("Error saving cache: %s", e)
    
    def _fetch_from_pypi(self) -> str:
        """
        Fetch latest version from PyPI with retry logic.
        
        Returns:
            Latest version string from PyPI
            
        Raises:
            NetworkError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug("Fetching from PyPI (attempt %d/%d)", 
                                attempt + 1, self.max_retries)
                
                req = self._create_secure_request(self.pypi_url)
                context = self._get_ssl_context()
                
                with urllib.request.urlopen(req, timeout=self.timeout, context=context) as response:
                    pypi_data = json.loads(response.read().decode("utf-8"))
                    latest_version = pypi_data["info"]["version"]
                    
                self.logger.debug("Latest version from PyPI: %s", latest_version)
                return latest_version
                
            except (URLError, json.JSONDecodeError, KeyError, TypeError) as e:
                last_error = e
                self.logger.debug("Attempt %d failed: %s", attempt + 1, e)
                
                if attempt < self.max_retries - 1:
                    self.logger.debug("Retrying in %d seconds...", self.retry_delay)
                    time.sleep(self.retry_delay)
        
        raise NetworkError(f"Failed to fetch version after {self.max_retries} attempts: {last_error}")
    
    def get_latest_version(self, force_refresh: bool = False) -> Tuple[str, Optional[str]]:
        """
        Get the latest version of TonieToolbox.
        
        Args:
            force_refresh: If True, bypass cache and fetch directly from PyPI
            
        Returns:
            Tuple of (latest_version, error_message)
            - On success: (latest_version, None)
            - On failure: (current_version, error_message)
        """
        self.logger.debug("Getting latest version (force_refresh=%s)", force_refresh)
        self.logger.debug("Current version: %s", __version__)
        
        # Try cache first if not forcing refresh
        if not force_refresh:
            cache_data = self._load_cache()
            if cache_data:
                return cache_data['version'], None
        
        # Fetch from PyPI
        try:
            latest_version = self._fetch_from_pypi()
            self._save_cache(latest_version)
            return latest_version, None
            
        except NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            self.logger.debug(error_msg)
            return __version__, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.debug(error_msg)
            return __version__, error_msg
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings according to PEP 440.
        
        Args:
            v1: First version string
            v2: Second version string
            
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        self.logger.debug("Comparing versions: '%s' vs '%s'", v1, v2)
        
        try:
            # Clean version strings (remove 'v' prefix if present)
            v1_clean = v1[1:] if v1.startswith('v') else v1
            v2_clean = v2[1:] if v2.startswith('v') else v2
            
            parsed_v1 = version.parse(v1_clean)
            parsed_v2 = version.parse(v2_clean)
            
            self.logger.debug("Parsed versions: %s vs %s", parsed_v1, parsed_v2)
            
            if parsed_v1 < parsed_v2:
                self.logger.debug("Result: '%s' is OLDER than '%s'", v1, v2)
                return -1
            elif parsed_v1 > parsed_v2:
                self.logger.debug("Result: '%s' is NEWER than '%s'", v1, v2)
                return 1
            else:
                self.logger.debug("Result: versions are EQUAL")
                return 0
                
        except Exception as e:
            self.logger.debug("Error comparing versions '%s' and '%s': %s", v1, v2, e)
            self.logger.debug("Falling back to string comparison")
            
            # Fallback to string comparison
            if v1 == v2:
                return 0
            elif v1 < v2:
                return -1
            else:
                return 1
    
    def check_for_updates(self, 
                         quiet: bool = False, 
                         force_refresh: bool = False,
                         callback: Optional[Callable[[bool, str, str], None]] = None
                         ) -> Tuple[bool, str, str, bool]:
        """
        Check if the current version is the latest available.
        
        Args:
            quiet: If True, suppress interactive prompts
            force_refresh: If True, bypass cache and check PyPI directly
            callback: Optional callback function for update notifications
            
        Returns:
            Tuple of (is_latest, latest_version, message, update_confirmed)
        """
        current_version = __version__
        update_confirmed = False
        
        self.logger.debug("Starting update check (quiet=%s, force_refresh=%s)", 
                        quiet, force_refresh)
        
        # Get latest version
        latest_version, error = self.get_latest_version(force_refresh)
        
        if error:
            self.logger.debug("Error occurred during update check: %s", error)
            return True, current_version, error, update_confirmed
        
        # Compare versions
        compare_result = self.compare_versions(current_version, latest_version)
        is_latest = compare_result >= 0
        
        self.logger.debug("Version comparison result: %d (is_latest=%s)", compare_result, is_latest)
        
        # Generate message
        if is_latest:
            message = f"You are using the latest version of TonieToolbox ({current_version})"
            if not quiet:
                self.logger.debug(message)
        else:
            message = f"Update available! Current version: {current_version}, Latest version: {latest_version}"
            
            if not quiet and self.notify_if_not_latest:
                self.logger.info(message)
                
                # Handle auto-update or user confirmation
                if self.auto_update:
                    update_confirmed = True
                    self.logger.info("Auto-update enabled. Attempting to install update...")
                else:
                    try:
                        response = input(f"Do you want to upgrade to TonieToolbox {latest_version}? [y/N]: ").lower().strip()
                        update_confirmed = response in ('y', 'yes')
                    except (EOFError, KeyboardInterrupt):
                        self.logger.debug("User input interrupted")
                        update_confirmed = False
                
                # Perform update if confirmed
                if update_confirmed:
                    if self.install_update():
                        self.logger.info(f"Successfully updated to TonieToolbox {latest_version}")
                        self.logger.info("Exiting program. Please restart TonieToolbox to use the new version.")
                        sys.exit(0)
                    else:
                        self.logger.error("Failed to install update automatically")
                        self.logger.error("Please update manually using: pip install --upgrade TonieToolbox")
                        sys.exit(1)
                else:
                    self.logger.info("Update skipped by user.")
            
            # Call callback if provided
            if callback:
                callback(is_latest, latest_version, message)
        
        return is_latest, latest_version, message, update_confirmed
    
    def install_update(self) -> bool:
        """
        Try to install the update using pip.
        
        Returns:
            True if the update was successfully installed, False otherwise
        """
        package_name = "TonieToolbox"
        commands = [
            [sys.executable, "-m", "pip", "install", "--upgrade", package_name],
            ["pip", "install", "--upgrade", package_name],
            ["pip3", "install", "--upgrade", package_name],
            ["pipx", "upgrade", package_name]
        ]
        
        for cmd in commands:
            try:
                self.logger.info(f"Attempting to install update using: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
                
                if result.returncode == 0:
                    self.logger.debug("Update command succeeded")
                    self.logger.debug(f"Output: {result.stdout}")
                    return True
                else:
                    self.logger.debug(f"Command failed with returncode {result.returncode}")
                    self.logger.debug(f"stdout: {result.stdout}")
                    self.logger.debug(f"stderr: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                self.logger.debug(f"Command timed out: {' '.join(cmd)}")
            except Exception as e:
                self.logger.debug(f"Exception while running {cmd[0]}: {str(e)}")
        
        return False
    
    def clear_cache(self) -> bool:
        """
        Clear the version cache file to force a refresh on next check.
        
        Returns:
            True if cache was cleared, False otherwise
        """
        try:
            if os.path.exists(self.cache_file):
                self.logger.debug("Removing version cache file: %s", self.cache_file)
                os.remove(self.cache_file)
                return True
            else:
                self.logger.debug("No cache file to remove")
                return False
        except Exception as e:
            self.logger.debug("Error clearing cache: %s", e)
            return False