#!/usr/bin/python3
"""
Singleton service provider for TeddyCloud integration.

This module provides centralized access to the TeddyCloud service,
ensuring a single instance is shared across CLI, GUI, and plugins.
"""
import logging
from typing import Optional
from threading import Lock

from .application import TeddyCloudService
from .infrastructure import create_teddycloud_service, create_teddycloud_connection_from_args
from .domain import TeddyCloudConnection


class TeddyCloudServiceProvider:
    """
    Singleton service provider for TeddyCloud operations.
    
    Provides centralized access to TeddyCloudService with lifecycle management.
    Ensures single service instance shared across application components.
    
    Example:
        >>> # Initialize during app startup
        >>> provider = TeddyCloudServiceProvider.get_instance()
        >>> provider.initialize(config_manager, logger)
        >>> 
        >>> # Access from plugins
        >>> service = provider.get_service()
        >>> if service and service.is_connected:
        ...     tags = service.get_tags()
    """
    
    _instance: Optional['TeddyCloudServiceProvider'] = None
    _instance_lock = Lock()
    
    def __init__(self):
        """Private constructor. Use get_instance() instead."""
        if TeddyCloudServiceProvider._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton instance")
        
        self._service: Optional[TeddyCloudService] = None
        self._initialized = False
        self._logger: Optional[logging.Logger] = None
    
    @classmethod
    def get_instance(cls) -> 'TeddyCloudServiceProvider':
        """
        Get the singleton instance of TeddyCloudServiceProvider.
        
        Thread-safe singleton implementation.
        
        Returns:
            TeddyCloudServiceProvider: Singleton instance
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance.
        
        Useful for testing. Should not be called in production code.
        """
        with cls._instance_lock:
            if cls._instance and cls._instance._service:
                cls._instance._service = None
            cls._instance = None
    
    def initialize(self, config_manager=None, logger: Optional[logging.Logger] = None) -> bool:
        """
        Initialize the TeddyCloud service.
        
        Args:
            config_manager: Optional configuration manager for auto-connect
            logger: Optional logger instance
            
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        try:
            # Import utilities - use correct path relative to teddycloud module
            import sys
            from pathlib import Path
            
            # Get logger if not provided
            if logger is None:
                import logging
                self._logger = logging.getLogger(__name__)
            else:
                self._logger = logger
            
            # Create service instance
            self._service = create_teddycloud_service(logger=self._logger)
            
            # Auto-connect if configuration available
            if config_manager and hasattr(config_manager, 'teddycloud'):
                tc_config = config_manager.teddycloud
                
                if tc_config.url:
                    from .domain import AuthenticationType
                    
                    # Determine authentication type
                    auth_type = AuthenticationType.NONE
                    if tc_config.client_cert and tc_config.client_key:
                        auth_type = AuthenticationType.CERTIFICATE
                    elif tc_config.username and tc_config.password:
                        auth_type = AuthenticationType.BASIC
                    
                    # Create connection
                    connection = TeddyCloudConnection(
                        base_url=tc_config.url,
                        authentication_type=auth_type,
                        username=tc_config.username,
                        password=tc_config.password,
                        cert_file=tc_config.client_cert,
                        key_file=tc_config.client_key,
                        ignore_ssl_verify=tc_config.ignore_ssl_verify
                    )
                    
                    try:
                        success = self._service.connect(connection)
                        if success:
                            self._logger.info("TeddyCloud auto-connected from configuration")
                        else:
                            self._logger.warning("TeddyCloud auto-connect failed")
                    except Exception as e:
                        self._logger.warning(f"TeddyCloud auto-connect error: {e}")
            
            self._initialized = True
            self._logger.info("TeddyCloud service provider initialized")
            return True
            
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to initialize TeddyCloud service provider: {e}")
            return False
    
    def get_service(self) -> Optional[TeddyCloudService]:
        """
        Get the TeddyCloud service instance.
        
        Returns:
            TeddyCloudService instance or None if not initialized
        """
        if not self._initialized:
            if self._logger:
                self._logger.warning("TeddyCloud service provider not initialized")
            return None
        return self._service
    
    def is_initialized(self) -> bool:
        """
        Check if service provider is initialized.
        
        Returns:
            True if initialized
        """
        return self._initialized
    
    def is_connected(self) -> bool:
        """
        Check if TeddyCloud service is connected.
        
        Returns:
            True if service is connected to server
        """
        return self._service is not None and self._service.is_connected
    
    def connect_from_args(self, args) -> bool:
        """
        Connect to TeddyCloud using command-line arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            True if connection successful
        """
        if not self._initialized:
            if self._logger:
                self._logger.error("Service provider not initialized")
            return False
        
        try:
            connection = create_teddycloud_connection_from_args(args)
            if not connection:
                if self._logger:
                    self._logger.error("Failed to create connection from arguments")
                return False
            
            return self._service.connect(connection)
            
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to connect from args: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from TeddyCloud server."""
        if self._service:
            # Service doesn't currently have disconnect method
            # but we can reset the connection state
            self._service._is_connected = False
            self._service._connection = None
            if self._logger:
                self._logger.info("TeddyCloud disconnected")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.disconnect()
        self._service = None
        self._initialized = False


def get_teddycloud_provider() -> TeddyCloudServiceProvider:
    """
    Convenience function to get TeddyCloud service provider.
    
    Returns:
        TeddyCloudServiceProvider singleton instance
    """
    return TeddyCloudServiceProvider.get_instance()
