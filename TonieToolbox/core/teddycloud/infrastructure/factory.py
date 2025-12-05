#!/usr/bin/python3
"""
Factory for creating TeddyCloud service instances with proper dependency injection.
Provides configured service instances following the factory pattern.
"""
import logging
from typing import Optional

from .http_repository import HttpTeddyCloudRepository
from .adapters import (
    StandardFileSystemService, StandardTemplateProcessor,
    MediaTagMetadataExtractor, SimpleMetadataExtractor
)
from ..application import TeddyCloudService
from ..domain import TeddyCloudConnection


def create_teddycloud_service(
    use_media_metadata: bool = True,
    logger: Optional[logging.Logger] = None
) -> TeddyCloudService:
    """
    Create a fully configured TeddyCloud service instance.
    
    Args:
        use_media_metadata: Whether to use media tag extraction (requires mutagen)
        logger: Optional logger instance
        
    Returns:
        Configured TeddyCloudService instance
    """
    if logger is None:
        from ...utils.logging import get_logger
        logger = get_logger(__name__)
    
    # Create infrastructure dependencies
    repository = HttpTeddyCloudRepository(logger)
    file_system_service = StandardFileSystemService(logger)
    template_processor = StandardTemplateProcessor(logger)
    
    # Choose metadata extractor based on requirements
    if use_media_metadata:
        try:
            metadata_extractor = MediaTagMetadataExtractor(logger)
        except ImportError:
            logger.warning("Media tag extraction not available, using simple extractor")
            metadata_extractor = SimpleMetadataExtractor(logger)
    else:
        metadata_extractor = SimpleMetadataExtractor(logger)
    
    # Create and return service
    return TeddyCloudService(
        repository=repository,
        template_processor=template_processor,
        metadata_extractor=metadata_extractor,
        file_system_service=file_system_service,
        logger=logger
    )


def create_teddycloud_connection_from_args(args) -> Optional[TeddyCloudConnection]:
    """
    Create TeddyCloudConnection from command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        TeddyCloudConnection instance or None if not applicable
    """
    from ..domain import TeddyCloudConnection, AuthenticationType
    
    # Determine URL
    url = None
    if hasattr(args, 'upload') and args.upload:
        url = args.upload
    elif hasattr(args, 'get_tags') and args.get_tags and args.get_tags != '':
        url = args.get_tags
    
    if not url:
        # Try to get from configuration
        try:
            from ...config import get_config_manager
            config_manager = get_config_manager()
            teddycloud_config = config_manager.teddycloud
            
            if teddycloud_config.url:
                url = teddycloud_config.url
                
                # Update args with config values if not set
                if not getattr(args, 'ignore_ssl_verify', False):
                    args.ignore_ssl_verify = teddycloud_config.ignore_ssl_verify
                if not getattr(args, 'username', None):
                    args.username = teddycloud_config.username or ''
                if not getattr(args, 'password', None):
                    args.password = teddycloud_config.password or ''
                if not getattr(args, 'client_cert', None):
                    args.client_cert = teddycloud_config.client_cert
                if not getattr(args, 'client_key', None):
                    args.client_key = teddycloud_config.client_key
                    
        except Exception:
            pass  # Configuration not available
    
    if not url:
        return None
    
    # Determine authentication type
    auth_type = AuthenticationType.NONE
    username = getattr(args, 'username', None)
    password = getattr(args, 'password', None)
    client_cert = getattr(args, 'client_cert', None)
    client_key = getattr(args, 'client_key', None)
    
    if client_cert:
        auth_type = AuthenticationType.CERTIFICATE
    elif username and password:
        auth_type = AuthenticationType.BASIC
    
    # Create connection
    try:
        return TeddyCloudConnection(
            base_url=url,
            authentication_type=auth_type,
            username=username,
            password=password,
            cert_file=client_cert,
            key_file=client_key,
            ignore_ssl_verify=getattr(args, 'ignore_ssl_verify', False),
            connection_timeout=getattr(args, 'connection_timeout', 30),
            read_timeout=getattr(args, 'read_timeout', 300),
            max_retries=getattr(args, 'max_retries', 3),
            retry_delay=getattr(args, 'retry_delay', 1)
        )
    except Exception as e:
        from ...utils.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to create TeddyCloud connection: {e}")
        return None


def get_teddycloud_service(logger: Optional[logging.Logger] = None) -> TeddyCloudService:
    """
    Get a configured TeddyCloud service instance.
    
    This is the main entry point for getting a TeddyCloud service.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        Configured TeddyCloudService instance
    """
    return create_teddycloud_service(logger=logger)