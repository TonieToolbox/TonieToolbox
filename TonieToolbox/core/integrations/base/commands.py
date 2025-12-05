#!/usr/bin/python3
"""
Command generation utilities for integrations.
"""
from typing import List, Dict, Any, Optional
from ...utils import get_logger

logger = get_logger(__name__)


class IntegrationCommand:
    """Represents a single integration command with its properties."""
    
    def __init__(self, name: str, description: str, **options):
        self.name = name
        self.description = description
        self.options = options
        
        # Common flags
        self.use_upload = options.get('use_upload', False)
        self.use_artwork = options.get('use_artwork', False)
        self.use_json = options.get('use_json', False)
        self.use_info = options.get('use_info', False)
        self.use_play = options.get('use_play', False)
        self.is_recursive = options.get('is_recursive', False)
        self.is_split = options.get('is_split', False)
        self.keep_open = options.get('keep_open', False)
        
        # File type filters
        self.file_extensions = options.get('file_extensions', [])
        self.mime_types = options.get('mime_types', [])
        self.applies_to_folders = options.get('applies_to_folders', False)
    
    def __str__(self):
        return f"IntegrationCommand({self.name}: {self.description})"


class CommandSet:
    """Manages a set of integration commands for a platform."""
    
    def __init__(self):
        self.commands = []
        self.logger = get_logger(f"{__name__}.CommandSet")
    
    def add_command(self, command: IntegrationCommand) -> None:
        """Add a command to the set."""
        self.commands.append(command)
        self.logger.debug("Added command: %s", command.name)
    
    def get_commands_for_audio_files(self) -> List[IntegrationCommand]:
        """Get commands that apply to audio files."""
        return [cmd for cmd in self.commands 
                if any(ext in cmd.file_extensions for ext in ['.mp3', '.wav', '.flac', '.ogg'])]
    
    def get_commands_for_taf_files(self) -> List[IntegrationCommand]:
        """Get commands that apply to TAF files."""
        return [cmd for cmd in self.commands 
                if '.taf' in cmd.file_extensions]
    
    def get_commands_for_folders(self) -> List[IntegrationCommand]:
        """Get commands that apply to folders."""
        return [cmd for cmd in self.commands if cmd.applies_to_folders]
    
    def get_all_commands(self) -> List[IntegrationCommand]:
        """Get all commands."""
        return self.commands.copy()


class StandardCommandFactory:
    """Factory for creating standard integration commands."""
    
    @staticmethod
    def create_standard_commands() -> CommandSet:
        """Create the standard set of integration commands."""
        command_set = CommandSet()
        
        # Import supported extensions
        from ...config.application_constants import SUPPORTED_EXTENSIONS
        
        audio_extensions = [ext.lower() for ext in SUPPORTED_EXTENSIONS]
        
        # Create audio conversion commands
        command_set.add_command(IntegrationCommand(
            name="convert_to_taf",
            description="Convert to Tonie Audio Format",
            file_extensions=audio_extensions,
            mime_types=StandardCommandFactory._get_audio_mime_types()
        ))
        
        command_set.add_command(IntegrationCommand(
            name="convert_to_taf_with_upload",
            description="Convert to TAF and Upload",
            file_extensions=audio_extensions,
            mime_types=StandardCommandFactory._get_audio_mime_types(),
            use_upload=True
        ))
        
        command_set.add_command(IntegrationCommand(
            name="convert_to_taf_with_artwork",
            description="Convert to TAF with Artwork",
            file_extensions=audio_extensions,
            mime_types=StandardCommandFactory._get_audio_mime_types(),
            use_artwork=True
        ))
        
        command_set.add_command(IntegrationCommand(
            name="convert_to_taf_with_json",
            description="Convert to TAF with Custom JSON",
            file_extensions=audio_extensions,
            mime_types=StandardCommandFactory._get_audio_mime_types(),
            use_json=True
        ))
        
        # Create TAF file commands
        command_set.add_command(IntegrationCommand(
            name="analyze_taf",
            description="Analyze TAF File",
            file_extensions=['.taf'],
            mime_types=['application/octet-stream'],
            use_info=True,
            keep_open=True
        ))
        
        command_set.add_command(IntegrationCommand(
            name="play_taf",
            description="Play TAF File",
            file_extensions=['.taf'],
            mime_types=['application/octet-stream'],
            use_play=True,
            keep_open=True
        ))
        
        command_set.add_command(IntegrationCommand(
            name="split_taf",
            description="Split TAF to MP3",
            file_extensions=['.taf'],
            mime_types=['application/octet-stream'],
            is_split=True
        ))
        
        command_set.add_command(IntegrationCommand(
            name="upload_taf",
            description="Upload TAF File",
            file_extensions=['.taf'],
            mime_types=['application/octet-stream'],
            use_upload=True
        ))
        
        # Create folder commands
        command_set.add_command(IntegrationCommand(
            name="convert_folder_recursive",
            description="Convert Folder (Recursive)",
            applies_to_folders=True,
            is_recursive=True
        ))
        
        command_set.add_command(IntegrationCommand(
            name="convert_folder_recursive_with_upload",
            description="Convert Folder and Upload (Recursive)",
            applies_to_folders=True,
            is_recursive=True,
            use_upload=True
        ))
        
        return command_set
    
    @staticmethod
    def _get_audio_mime_types() -> List[str]:
        """Get MIME types for audio files."""
        return [
            'audio/mpeg',      # MP3
            'audio/wav',       # WAV
            'audio/flac',      # FLAC
            'audio/ogg',       # OGG
            'audio/opus',      # Opus
            'audio/aac',       # AAC
            'audio/mp4',       # M4A/MP4
            'audio/x-ms-wma',  # WMA
            'audio/x-aiff',    # AIFF
            'audio/webm',      # WebM
            'audio/x-matroska', # MKA
            'audio/x-ape'      # APE
        ]


class PlatformCommandAdapter:
    """Adapts standard commands to platform-specific formats."""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = get_logger(f"{__name__}.PlatformCommandAdapter")
    
    def adapt_command_for_platform(self, command: IntegrationCommand, 
                                 builder_func, **platform_options) -> Any:
        """
        Adapt a command for a specific platform using the provided builder function.
        
        Args:
            command: The command to adapt
            builder_func: Platform-specific function to build the command
            **platform_options: Platform-specific options
            
        Returns:
            Platform-specific command representation
        """
        try:
            return builder_func(command, **platform_options)
        except Exception as e:
            self.logger.error("Failed to adapt command %s for %s: %s", 
                            command.name, self.platform_name, e)
            return None