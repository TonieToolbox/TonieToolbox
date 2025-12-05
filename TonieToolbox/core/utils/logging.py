#!/usr/bin/python3
"""
Logging configuration for the TonieToolbox package.
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path


# Custom logging level for detailed tracing
TRACE = 5
logging.addLevelName(TRACE, 'TRACE')


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after every emit for immediate output."""
    
    def emit(self, record):
        """Emit a record and flush immediately."""
        super().emit(record)
        self.flush()


def trace(self: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log a message with TRACE level (more detailed than DEBUG)"""
    if self.isEnabledFor(TRACE):
        self.log(TRACE, message, *args, **kwargs)
logging.Logger.trace = trace
def get_log_file_path() -> Path:
    """
    Get the path to the log file in the .tonietoolbox folder with timestamp.
    
    Returns:
        Path: Path to the log file
        
    Raises:
        OSError: If log directory cannot be created
        PermissionError: If insufficient permissions to create directory
    """
    log_dir = Path.home() / '.tonietoolbox' / 'logs'
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f'tonietoolbox_{timestamp}.log'
    return log_file
def setup_logging(level: int = logging.INFO, log_to_file: bool = False) -> logging.Logger:
    """
    Set up logging configuration for the entire application.
    Args:
        level (int): Logging level (default: logging.INFO)
        log_to_file (bool): Whether to log to a file (default: False)
    Returns:
        logging.Logger: Root logger instance
    """
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    root_logger = logging.getLogger('TonieToolbox')
    root_logger.setLevel(level)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    console_handler = FlushingStreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)
    if log_to_file:
        try:
            log_file = get_log_file_path()
            file_handler = logging.FileHandler(
                log_file,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
            root_logger.info(f"Log file created at: {log_file}")
        except Exception as e:
            root_logger.error(f"Failed to set up file logging: {e}")
    return root_logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    Args:
        name (str): Logger name, typically the module name
    Returns:
        logging.Logger: Logger instance
    """
    if name.startswith('TonieToolbox.'):
        logger_name = name
    else:
        logger_name = f'TonieToolbox.{name}'
    
    logger = logging.getLogger(logger_name)
    return logger


def setup_logging_from_args(args: argparse.Namespace) -> None:
    """
    Setup logging based on command line arguments using unified configuration.
    
    Args:
        args: Parsed command line arguments
    """
    from ..config import get_config_manager
    
    # Get unified configuration manager
    config_manager = get_config_manager()
    
    # Determine log level from command line arguments
    log_level = _determine_log_level_from_args(args)
    
    # Update unified config with command line args (convert int level to string)
    config_manager.logging.level = logging.getLevelName(log_level)
    config_manager.logging.log_to_file = getattr(args, 'log_file', False)
    
    # Apply logging configuration using unified system (use numeric level)
    setup_logging(
        log_level, 
        log_to_file=config_manager.logging.log_to_file
    )


def _determine_log_level_from_args(args) -> int:
    """
    Determine log level from command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Logging level constant
    """
    if getattr(args, 'trace', False):
        return TRACE
    elif getattr(args, 'debug', False):
        return logging.DEBUG
    elif getattr(args, 'quiet', False):
        return logging.WARNING
    elif getattr(args, 'silent', False):
        return logging.ERROR
    else:
        return logging.INFO