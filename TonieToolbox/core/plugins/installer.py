#!/usr/bin/env python3
"""
Plugin installer for downloading and installing plugins.

Handles downloading plugins from git repositories or archives,
verifying checksums, and managing plugin installations.
"""
import os
import shutil
import hashlib
import subprocess
import urllib.request
import tempfile
import tarfile
import zipfile
from pathlib import Path
from typing import Optional, Callable, List, Dict
from ..utils import get_logger
from .base import PluginManifest, PluginInstallInfo
from .repository import PluginRepository

logger = get_logger(__name__)


class PluginInstaller:
    """
    Handles plugin installation, updates, and removal.
    
    Supports:
    - Git clone installation
    - Archive (zip/tar.gz) download and extraction
    - SHA512 checksum verification
    - Plugin updates
    - Plugin removal
    """
    
    def __init__(self, install_base_dir: Path, repository: PluginRepository):
        """
        Initialize the plugin installer.
        
        Args:
            install_base_dir: Base directory for plugin installations
                             (default: ~/.tonietoolbox/plugins)
            repository: PluginRepository instance
        """
        self.install_base_dir = Path(install_base_dir).expanduser()
        self.repository = repository
        
        # Ensure base directory exists
        self.install_base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PluginInstaller initialized with base dir: {self.install_base_dir}")
    
    def install(
        self,
        manifest: PluginManifest,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Install a plugin from manifest.
        
        Args:
            manifest: Plugin manifest
            progress_callback: Optional callback(message, progress_percent)
            
        Returns:
            True if installation succeeded
        """
        if not manifest.metadata.install_info:
            logger.error(f"No install info in manifest for {manifest.metadata.id}")
            return False
        
        plugin_id = manifest.metadata.id
        install_info = manifest.metadata.install_info
        
        # Extract author and plugin name from ID (e.g., com.author.plugin_name)
        parts = plugin_id.split('.')
        if len(parts) < 3:
            logger.error(f"Invalid plugin ID format: {plugin_id}")
            return False
        
        author = parts[1]
        plugin_name = parts[2]
        
        # Target installation directory: ~/.tonietoolbox/plugins/{author}/{plugin_name}
        install_dir = self.install_base_dir / author / plugin_name
        
        logger.info(f"Installing {plugin_id} to {install_dir}")
        
        if progress_callback:
            progress_callback(f"Installing {manifest.metadata.name}...", 0)
        
        try:
            # Remove existing installation if present
            if install_dir.exists():
                logger.info(f"Removing existing installation at {install_dir}")
                shutil.rmtree(install_dir)
            
            # Install based on source_type
            if install_info.source_type == "git":
                success = self._install_from_git(install_info, install_dir, progress_callback)
                archive_path = None
            elif install_info.source_type == "archive":
                success, archive_path = self._install_from_archive(install_info, install_dir, progress_callback)
            else:
                logger.error(f"Unsupported install type: {install_info.source_type}")
                return False
            
            if not success:
                return False
            
            # Verify checksum if provided
            if install_info.checksum:
                if progress_callback:
                    progress_callback("Verifying checksum...", 80)
                
                checksum_valid = False
                
                # For Git installs with commit hash, skip checksum (commit is verification)
                if install_info.source_type == "git" and install_info.commit:
                    logger.info("Skipping checksum verification (commit hash verified)")
                    checksum_valid = True
                
                # For archive installations, verify archive checksum
                elif archive_path and archive_path.exists():
                    logger.debug(f"Verifying archive checksum ({install_info.checksum_algorithm})...")
                    checksum_valid = self._verify_archive_checksum(
                        archive_path, 
                        install_info.checksum,
                        install_info.checksum_algorithm
                    )
                    # Clean up archive after verification
                    archive_path.unlink()
                
                # For other cases, skip (directory checksum is unreliable)
                else:
                    logger.warning("Checksum verification skipped (not supported for this installation type)")
                    checksum_valid = True
                
                if not checksum_valid:
                    logger.error(f"Checksum verification failed for {plugin_id}")
                    shutil.rmtree(install_dir)
                    return False
                else:
                    logger.info(f"Checksum verification passed for {plugin_id}")
            
            if progress_callback:
                progress_callback("Installation complete", 100)
            
            logger.info(f"Successfully installed {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install {plugin_id}: {e}", exc_info=True)
            if install_dir.exists():
                shutil.rmtree(install_dir)
            return False
    
    def _install_from_git(
        self,
        install_info: PluginInstallInfo,
        install_dir: Path,
        progress_callback: Optional[Callable[[str, int], None]]
    ) -> bool:
        """Install plugin from git repository."""
        try:
            if progress_callback:
                progress_callback("Cloning repository...", 10)
            
            # Build git clone command
            cmd = ["git", "clone"]
            
            if install_info.branch and not install_info.commit:
                cmd.extend(["--branch", install_info.branch])
            
            if not install_info.commit:
                cmd.extend(["--depth", "1"])  # Shallow clone only if not checking out specific commit
            
            cmd.extend([install_info.source_url, str(install_dir)])
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                return False
            
            # Checkout specific commit if specified
            if install_info.commit:
                if progress_callback:
                    progress_callback(f"Checking out commit {install_info.commit[:8]}...", 40)
                
                checkout_cmd = ["git", "checkout", install_info.commit]
                logger.debug(f"Running: {' '.join(checkout_cmd)}")
                
                result = subprocess.run(
                    checkout_cmd,
                    cwd=install_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    logger.error(f"Git checkout failed: {result.stderr}")
                    return False
                
                # Verify we're on the correct commit
                verify_cmd = ["git", "rev-parse", "HEAD"]
                result = subprocess.run(
                    verify_cmd,
                    cwd=install_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    actual_commit = result.stdout.strip()
                    if actual_commit != install_info.commit:
                        logger.error(f"Commit verification failed: expected {install_info.commit}, got {actual_commit}")
                        return False
                    logger.info(f"Verified commit: {actual_commit[:8]}")
                else:
                    logger.warning("Could not verify commit hash")
            
            # Remove .git directory to save space
            git_dir = install_dir / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)
            
            # Handle subdirectory if specified
            if install_info.subdirectory:
                subdir_path = install_dir / install_info.subdirectory
                if subdir_path.exists():
                    # Move contents of subdir to install_dir
                    temp_dir = install_dir.parent / f"{install_dir.name}_temp"
                    shutil.move(str(subdir_path), str(temp_dir))
                    shutil.rmtree(install_dir)
                    shutil.move(str(temp_dir), str(install_dir))
            
            # Flatten nested directories (if single directory with same name exists)
            self._flatten_nested_directory(install_dir)
            
            if progress_callback:
                progress_callback("Repository cloned successfully", 70)
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out")
            return False
        except Exception as e:
            logger.error(f"Git installation failed: {e}")
            return False
    
    def _install_from_archive(
        self,
        install_info: PluginInstallInfo,
        install_dir: Path,
        progress_callback: Optional[Callable[[str, int], None]]
    ) -> tuple[bool, Optional[Path]]:
        """Install plugin from archive (zip or tar.gz). Returns (success, tmp_archive_path)."""
        tmp_path = None
        try:
            if progress_callback:
                progress_callback("Downloading archive...", 10)
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.archive') as tmp_file:
                tmp_path = Path(tmp_file.name)
                
                logger.debug(f"Downloading from {install_info.source_url}")
                
                with urllib.request.urlopen(install_info.source_url, timeout=300) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    chunk_size = 8192
                    
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            percent = int((downloaded / total_size) * 50) + 10
                            progress_callback(f"Downloading... ({downloaded}/{total_size} bytes)", percent)
            
            if progress_callback:
                progress_callback("Extracting archive...", 60)
            
            # Extract archive
            install_dir.mkdir(parents=True, exist_ok=True)
            
            if install_info.source_url.endswith('.zip'):
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
            elif install_info.source_url.endswith('.tar.gz') or install_info.source_url.endswith('.tgz'):
                with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(install_dir)
            elif install_info.source_url.endswith('.tar'):
                with tarfile.open(tmp_path, 'r') as tar_ref:
                    tar_ref.extractall(install_dir)
            else:
                logger.error(f"Unsupported archive format: {install_info.source_url}")
                if tmp_path and tmp_path.exists():
                    tmp_path.unlink()
                return False, None
            
            # Handle subdirectory if specified
            if install_info.subdirectory:
                subdir_path = install_dir / install_info.subdirectory
                if subdir_path.exists():
                    temp_dir = install_dir.parent / f"{install_dir.name}_temp"
                    shutil.move(str(subdir_path), str(temp_dir))
                    shutil.rmtree(install_dir)
                    shutil.move(str(temp_dir), str(install_dir))
            
            # Flatten nested directories (if single directory with same name exists)
            self._flatten_nested_directory(install_dir)
            
            if progress_callback:
                progress_callback("Archive extracted successfully", 70)
            
            return True, tmp_path
            
        except Exception as e:
            logger.error(f"Archive installation failed: {e}")
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
            return False, None
    
    def _flatten_nested_directory(self, install_dir: Path) -> None:
        """
        Flatten nested directory structure if only one subdirectory exists.
        
        Example: If install_dir contains only one subdirectory with plugin files,
        move its contents up to install_dir level.
        
        Args:
            install_dir: Plugin installation directory to flatten
        """
        try:
            # Get all items in install_dir (excluding hidden files/dirs)
            items = [item for item in install_dir.iterdir() if not item.name.startswith('.')]
            
            # Check if there's exactly one directory
            if len(items) == 1 and items[0].is_dir():
                nested_dir = items[0]
                
                # Check if nested directory contains plugin files
                has_plugin_files = (nested_dir / "plugin.py").exists() or (nested_dir / "__init__.py").exists()
                
                if has_plugin_files:
                    logger.info(f"Flattening nested directory: {nested_dir.name}")
                    
                    # Move all contents from nested_dir to parent, then remove nested_dir
                    temp_dir = install_dir.parent / f"{install_dir.name}_flatten_temp"
                    
                    # Move nested directory to temp location
                    shutil.move(str(nested_dir), str(temp_dir))
                    
                    # Move all items from temp to install_dir
                    for item in temp_dir.iterdir():
                        dest = install_dir / item.name
                        shutil.move(str(item), str(dest))
                    
                    # Remove temp directory
                    temp_dir.rmdir()
                    
                    logger.debug(f"Successfully flattened directory structure")
        except Exception as e:
            logger.warning(f"Failed to flatten nested directory: {e}")
    
    def _verify_checksum(self, install_dir: Path, expected_checksum: str) -> bool:
        """
        Verify SHA512 checksum of installed plugin directory.
        
        Args:
            install_dir: Plugin installation directory
            expected_checksum: Expected SHA512 checksum
            
        Returns:
            True if checksum matches
        """
        try:
            # Calculate SHA512 of all files in directory
            sha512 = hashlib.sha512()
            
            for file_path in sorted(install_dir.rglob('*')):
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        while chunk := f.read(8192):
                            sha512.update(chunk)
            
            actual_checksum = sha512.hexdigest()
            
            if actual_checksum.lower() == expected_checksum.lower():
                logger.debug("Directory checksum verification passed")
                return True
            else:
                logger.debug(f"Directory checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                return False
                
        except Exception as e:
            logger.error(f"Directory checksum verification failed: {e}")
            return False
    
    def _verify_archive_checksum(self, archive_path: Path, expected_checksum: str, algorithm: str = "sha256") -> bool:
        """
        Verify checksum of archive file.
        
        Args:
            archive_path: Path to archive file
            expected_checksum: Expected checksum
            algorithm: Hash algorithm ("sha256" or "sha512")
            
        Returns:
            True if checksum matches
        """
        try:
            # Select hash algorithm
            if algorithm == "sha256":
                hasher = hashlib.sha256()
            elif algorithm == "sha512":
                hasher = hashlib.sha512()
            else:
                logger.error(f"Unsupported hash algorithm: {algorithm}")
                return False
            
            # Calculate hash
            with open(archive_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            
            actual_checksum = hasher.hexdigest()
            
            if actual_checksum.lower() == expected_checksum.lower():
                logger.debug(f"Archive {algorithm} checksum verification passed")
                return True
            else:
                logger.error(f"Archive {algorithm} checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                return False
                
        except Exception as e:
            logger.error(f"Archive checksum verification failed: {e}")
            return False
    
    def uninstall(self, author: str, plugin_name: str, plugin_id: Optional[str] = None) -> bool:
        """
        Uninstall a plugin and remove its cache directory.
        
        Args:
            author: Plugin author
            plugin_name: Plugin name
            plugin_id: Optional plugin ID for cache cleanup (e.g., com.author.plugin_name)
            
        Returns:
            True if uninstallation succeeded
        """
        install_dir = self.install_base_dir / author / plugin_name
        
        if not install_dir.exists():
            logger.warning(f"Plugin not found: {author}/{plugin_name}")
            return False
        
        try:
            logger.info(f"Uninstalling {author}/{plugin_name}")
            
            # Remove plugin installation directory
            shutil.rmtree(install_dir)
            logger.debug(f"Removed plugin directory: {install_dir}")
            
            # Remove author directory if empty
            author_dir = self.install_base_dir / author
            if author_dir.exists() and not any(author_dir.iterdir()):
                author_dir.rmdir()
                logger.debug(f"Removed empty author directory: {author_dir}")
            
            # Remove plugin cache directory if plugin_id provided
            if plugin_id:
                self._remove_plugin_cache(plugin_id)
            
            logger.info(f"Successfully uninstalled {author}/{plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to uninstall {author}/{plugin_name}: {e}")
            return False
    
    def _remove_plugin_cache(self, plugin_id: str) -> None:
        """
        Remove plugin cache directory.
        
        Uses the same centralized logic as PluginContext.get_cache_dir() to
        locate and remove plugin-specific cache directories.
        
        Args:
            plugin_id: Plugin ID (e.g., com.tonietoolbox.tonies_loader)
        """
        try:
            # Extract plugin name from ID
            parts = plugin_id.split('.')
            if len(parts) < 3:
                logger.warning(f"Invalid plugin ID format for cache cleanup: {plugin_id}")
                return
            
            plugin_name = parts[-1]  # Last part is the plugin name
            
            # Get the base cache directory (same logic as PluginContext.get_cache_dir)
            cache_base = Path.home() / '.tonietoolbox' / 'cache'
            
            if not cache_base.exists():
                logger.debug(f"Cache directory does not exist: {cache_base}")
                return
            
            # Remove the plugin-specific cache directory
            cache_dir = cache_base / plugin_name
            if cache_dir.exists() and cache_dir.is_dir():
                logger.info(f"Removing plugin cache directory: {cache_dir}")
                shutil.rmtree(cache_dir)
                logger.debug(f"Successfully removed cache: {cache_dir}")
            else:
                logger.debug(f"No cache directory found for plugin: {plugin_id}")
            
        except Exception as e:
            logger.warning(f"Failed to remove plugin cache for {plugin_id}: {e}")
    
    def get_installed_plugins(self) -> List[Dict[str, str]]:
        """
        Get list of installed plugins from disk.
        
        Returns:
            List of dicts with 'author', 'plugin_name', 'path', 'id', 'version' keys
        """
        installed = []
        
        if not self.install_base_dir.exists():
            return installed
        
        try:
            import json
            
            # Iterate through author directories
            for author_dir in self.install_base_dir.iterdir():
                if not author_dir.is_dir():
                    continue
                
                # Iterate through plugin directories
                for plugin_dir in author_dir.iterdir():
                    if not plugin_dir.is_dir():
                        continue
                    
                    # Check if it has a plugin.py or __init__.py
                    if (plugin_dir / "plugin.py").exists() or (plugin_dir / "__init__.py").exists():
                        plugin_info = {
                            'author': author_dir.name,
                            'plugin_name': plugin_dir.name,
                            'path': str(plugin_dir)
                        }
                        
                        # Try to read manifest to get ID and version
                        manifest_path = plugin_dir / "manifest.json"
                        if manifest_path.exists():
                            try:
                                with open(manifest_path, 'r') as f:
                                    manifest_data = json.load(f)
                                    plugin_info['id'] = manifest_data.get('id', '')
                                    plugin_info['version'] = manifest_data.get('version', '')
                            except Exception as e:
                                logger.debug(f"Could not read manifest at {manifest_path}: {e}")
                                plugin_info['id'] = ''
                                plugin_info['version'] = ''
                        else:
                            plugin_info['id'] = ''
                            plugin_info['version'] = ''
                        
                        installed.append(plugin_info)
            
            logger.debug(f"Found {len(installed)} installed plugins")
            return installed
            
        except Exception as e:
            logger.error(f"Failed to list installed plugins: {e}")
            return []
    
    def update(
        self,
        manifest: PluginManifest,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Update an installed plugin.
        
        Args:
            manifest: New version manifest
            progress_callback: Optional progress callback
            
        Returns:
            True if update succeeded
        """
        logger.info(f"Updating plugin {manifest.metadata.id} to version {manifest.metadata.version}")
        
        # Uninstall and reinstall is the simplest approach
        parts = manifest.metadata.id.split('.')
        if len(parts) >= 3:
            author = parts[1]
            plugin_name = parts[2]
            
            # Note: We don't uninstall first to allow rollback if installation fails
            return self.install(manifest, progress_callback)
        
        return False
    
    def install_python_dependencies(self, packages: List[str]) -> bool:
        """
        Install Python dependencies using pip.
        
        Args:
            packages: List of package specifications
            
        Returns:
            True if all packages installed successfully
        """
        if not packages:
            return True
        
        logger.info(f"Installing {len(packages)} Python packages: {packages}")
        
        try:
            cmd = [
                "pip", "install",
                "--user",  # Install to user site-packages
                *packages
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for pip
            )
            
            if result.returncode != 0:
                logger.error(f"pip install failed: {result.stderr}")
                return False
            
            logger.info("Python dependencies installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Python dependencies: {e}")
            return False
