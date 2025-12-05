#!/usr/bin/python3
"""
Argument parsing for TonieToolbox.

This module handles all command-line argument parsing and validation,
extracted from the original monolithic main function.
"""

import argparse
from typing import Dict, Any, Optional

from ... import __version__


class TonieToolboxArgumentParser:
    """Handles CLI argument parsing and validation."""
    
    def __init__(self, default_values: Optional[Dict[str, Any]] = None):
        """
        Initialize the argument parser with all available options.
        
        Args:
            default_values: Dictionary of default values for CLI arguments.
                          If None, system defaults will be used.
        """
        self.defaults = default_values or self._get_system_defaults()
        self.parser = self._create_parser()
    
    def _get_system_defaults(self) -> Dict[str, Any]:
        """Get system default values when no config is provided (match config defaults)."""
        return {
            'default_bitrate': 128,
            'connection_timeout': 10,
            'read_timeout': 300,
            'max_retries': 3,
            'retry_delay': 5,
        }
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the complete argument parser."""
        parser = argparse.ArgumentParser(
            description='Convert media files to Tonie compatible files.'
        )
        
        # Core arguments
        self._add_core_arguments(parser)
        
        # Processing options
        self._add_processing_arguments(parser)
        
        # File operations
        self._add_file_operation_arguments(parser)
        
        # Output control
        self._add_output_control_arguments(parser)
        
        # Tonie-specific options
        self._add_tonie_specific_arguments(parser)
        
        # Analysis & debugging
        self._add_analysis_arguments(parser)
        
        # System integration
        self._add_integration_arguments(parser)
        
        # TeddyCloud options
        self._add_teddycloud_arguments(parser)
        
        # Media tag options
        self._add_media_tag_arguments(parser)
        
        # Version and logging options
        self._add_version_arguments(parser)
        self._add_logging_arguments(parser)
        
        return parser
    
    def _add_core_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add core file I/O and basic program control arguments."""
        parser.add_argument('-v', '--version', action='version', 
                           version=f'TonieToolbox {__version__}',
                           help='show program version and exit')
        
        parser.add_argument('input_filename', metavar='SOURCE', type=str, nargs='?',
                           help='input file or directory or a file list (.lst)')
        parser.add_argument('output_filename', metavar='TARGET', nargs='?', type=str,
                           help='the output file name (default: ---ID---)')
    
    def _add_processing_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add audio encoding and conversion processing arguments."""
        processing_group = parser.add_argument_group('Processing Options')
        
        processing_group.add_argument('-f', '--ffmpeg', help='specify location of ffmpeg', default=None)
        # Get default from injected values
        default_bitrate = self.defaults['default_bitrate']
        processing_group.add_argument('-b', '--bitrate', type=int, 
                           help=f'set encoding bitrate in kbps for Opus & MP3 Conversion (default: {default_bitrate})', 
                           default=default_bitrate)
        processing_group.add_argument('--cbr', action='store_true', help='encode in cbr mode')
        processing_group.add_argument('-A', '--auto-download', action='store_true',
                           help='automatically download ffmpeg if not found')
        processing_group.add_argument('-M', '--no-mono-conversion', action='store_true',
                           help='Do not convert mono audio to stereo (default: convert mono to stereo)')
    
    def _add_file_operation_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for file operations and actions."""
        file_ops_group = parser.add_argument_group('File Operations')
        
        file_ops_group.add_argument('-i', '--info', action='store_true', 
                           help='Check and display info about Tonie file')
        file_ops_group.add_argument('-p', '--play', action='store_true', 
                           help='Play TAF using TonieToolbox GUI Player with auto-play')
        file_ops_group.add_argument('-g', '--gui', action='store_true',
                           help='Launch the TonieToolbox GUI')
        file_ops_group.add_argument('-s', '--split', action='store_true', 
                           help='Extract the OGG/Opus stream from TAF file and split by Chapters')
        file_ops_group.add_argument('-e', '--extract', action='store_true',
                           help='Extract the entire OGG/Opus stream from TAF file')
        file_ops_group.add_argument('-r', '--recursive', action='store_true', 
                           help='Process subdirectories recursively. Without --files-to-taf, combines files per folder into one TAF. With --files-to-taf, converts each file individually.')
        file_ops_group.add_argument('--files-to-taf', action='store_true', 
                           help='Convert each audio file to individual .taf files. Use with --recursive to process entire directory tree.')
        file_ops_group.add_argument('--max-depth', type=int, metavar='N',
                           help='Maximum directory depth for recursive processing (requires --recursive, default: unlimited)')
        file_ops_group.add_argument('-w', '--workers', type=int, metavar='N', default=1,
                           help='Number of parallel workers for recursive processing (default: 1, use 4-8 for optimal performance)')
        file_ops_group.add_argument('--convert-to-separate-mp3', action='store_true', 
                           help='Convert Tonie file to individual MP3 tracks')
        file_ops_group.add_argument('--convert-to-single-mp3', action='store_true', 
                           help='Convert Tonie file to a single MP3 file')
    
    def _add_output_control_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments controlling how and where output is saved."""
        output_group = parser.add_argument_group('Output Control')
        
        output_group.add_argument('-O', '--output-to-source', action='store_true', 
                           help='Save output files in the source directory instead of output directory')
        output_group.add_argument('-fc', '--force-creation', action='store_true', default=False,
                           help='Force creation of Tonie file even if it already exists')
    
    def _add_tonie_specific_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add Tonie TAF format specific arguments."""
        tonie_group = parser.add_argument_group('Tonie-Specific Options')
        
        tonie_group.add_argument('-t', '--timestamp', dest='user_timestamp', metavar='TIMESTAMP', action='store',
                           help='set custom timestamp / bitstream serial')
        tonie_group.add_argument('-a', '--append-tonie-tag', metavar='TAG', action='store',
                           help='append [TAG] to filename (must be an 8-character hex value)')
        tonie_group.add_argument('-n', '--no-tonie-header', action='store_true', 
                           help='do not write Tonie header')
        tonie_group.add_argument('-k', '--keep-temp', action='store_true', 
                           help='Keep temporary opus files in a temp folder for testing')
        tonie_group.add_argument('-u', '--use-legacy-tags', action='store_true',
                           help='Use legacy hardcoded tags instead of dynamic TonieToolbox tags')
    
    def _add_analysis_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add file comparison and debugging arguments."""
        analysis_group = parser.add_argument_group('Analysis & Debugging')
        
        analysis_group.add_argument('-c', '--compare', action='store', metavar='FILE2', 
                           help='Compare input file with another .taf file for debugging')
        analysis_group.add_argument('-D', '--detailed-compare', action='store', metavar='FILE2', nargs='?', const=True,
                           help='Show detailed OGG page differences when comparing files. Can be used with --compare or directly with a file path (e.g., --detailed-compare file2.taf)')
    
    def _add_integration_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add system integration arguments."""
        integration_group = parser.add_argument_group('System Integration')
        
        integration_group.add_argument('-C', '--config-integration', action='store_true',
                           help='Configure context menu integration')
        integration_group.add_argument('-I', '--install-integration', action='store_true',
                           help='Integrate with the system (e.g., create context menu entries)')
        integration_group.add_argument('-U', '--uninstall-integration', action='store_true',
                           help='Uninstall context menu integration')
    
    def _add_teddycloud_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add TeddyCloud-specific arguments."""
        teddycloud_group = parser.add_argument_group('TeddyCloud Options')
        
        teddycloud_group.add_argument('--upload', metavar='URL', action='store', nargs='?', const='',
                                     help='Upload to TeddyCloud instance. URL optional if configured (e.g., https://teddycloud.example.com). Supports .taf, .jpg, .jpeg, .png files.')
        teddycloud_group.add_argument('--include-artwork', action='store_true',
                                     help='Upload cover artwork image alongside the Tonie file when using --upload')
        teddycloud_group.add_argument('--assign-to-tag', 
                                     metavar='TAG_UID[,TAG_UID,...]',
                                     action='store',
                                     help='Assign uploaded file(s) to specific tag UID(s). '
                                          'Single file + multiple tags: assigns file to ALL tags. '
                                          'Multiple files (--recursive): assigns files sequentially to tags. '
                                          'Example: E0:04:03:50:1E:E9:18:F2,E00403501EE918F3')
        teddycloud_group.add_argument('--auto-select-tag', 
                                     action='store_true',
                                     help='Automatically assign to first available unassigned tag. '
                                          'With --recursive, finds unassigned tags for each file.')
        teddycloud_group.add_argument('--get-tags', action='store', metavar='URL', nargs='?', const='',
                                     help='Get available tags from TeddyCloud instance')
        teddycloud_group.add_argument('--ignore-ssl-verify', action='store_true',
                                     help='Ignore SSL certificate verification (for self-signed certificates)')
        teddycloud_group.add_argument('--special-folder', action='store', metavar='FOLDER',
                                     help='Special folder to upload to (currently only "library" is supported)', 
                                     default='library')
        teddycloud_group.add_argument('--path', action='store', metavar='PATH',
                                     help='Path where to write the file on TeddyCloud server (supports templates like "/{albumartist}/{album}")')
        
        # Connection settings - get defaults from injected values
        connection_timeout = self.defaults['connection_timeout']
        read_timeout = self.defaults['read_timeout']
        max_retries = self.defaults['max_retries']
        retry_delay = self.defaults['retry_delay']
        
        teddycloud_group.add_argument('--connection-timeout', type=int, metavar='SECONDS', 
                                     default=connection_timeout,
                                     help=f'Connection timeout in seconds (default: {connection_timeout})')
        teddycloud_group.add_argument('--read-timeout', type=int, metavar='SECONDS', 
                                     default=read_timeout,
                                     help=f'Read timeout in seconds (default: {read_timeout})')
        teddycloud_group.add_argument('--max-retries', type=int, metavar='RETRIES', 
                                     default=max_retries,
                                     help=f'Maximum number of retry attempts (default: {max_retries})')
        teddycloud_group.add_argument('--retry-delay', type=int, metavar='SECONDS', 
                                     default=retry_delay,
                                     help=f'Delay between retry attempts in seconds (default: {retry_delay})')
        
        # JSON options
        teddycloud_group.add_argument('--create-custom-json', action='store_true',
                                     help='Fetch and update custom Tonies JSON data')
        teddycloud_group.add_argument('--version-2', action='store_true',
                                     help='Use version 2 of the Tonies JSON format (default: version 1)')
        
        # Authentication
        teddycloud_group.add_argument('--username', action='store', metavar='USERNAME',
                                     help='Username for basic authentication')
        teddycloud_group.add_argument('--password', action='store', metavar='PASSWORD',
                                     help='Password for basic authentication')
        teddycloud_group.add_argument('--client-cert', action='store', metavar='CERT_FILE',
                                     help='Path to client certificate file for certificate-based authentication')
        teddycloud_group.add_argument('--client-key', action='store', metavar='KEY_FILE',
                                     help='Path to client private key file for certificate-based authentication')
    
    def _add_media_tag_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add media tag processing arguments."""
        media_tag_group = parser.add_argument_group('Media Tag Options')
        
        media_tag_group.add_argument('-m', '--use-media-tags', action='store_true',
                                   help='Use media tags from audio files for naming')
        media_tag_group.add_argument('--name-template', metavar='TEMPLATE', action='store',
                                   help='Template for naming files using media tags. Example: "{albumartist} - {album}"')
        media_tag_group.add_argument('--output-to-template', metavar='PATH_TEMPLATE', action='store',
                                   help='Template for output path using media tags. Example: "C:\\Music\\{albumartist}\\{album}"')
        media_tag_group.add_argument('--show-media-tags', action='store_true',
                                   help='Show available media tags from input files')
    
    def _add_version_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add version check arguments."""
        version_group = parser.add_argument_group('Version Check Options')
        
        version_group.add_argument('-S', '--skip-update-check', action='store_true',
                                 help='Skip checking for updates')
        version_group.add_argument('-F', '--force-update-check', action='store_true',
                                 help='Force refresh of update information from PyPI')
        version_group.add_argument('--clear-version-cache', action='store_true',
                                 help='Clear the version check cache and exit')
        version_group.add_argument('--check-updates-only', action='store_true',
                                 help='Only check for updates and exit (no other processing)')
        version_group.add_argument('--disable-notifications', action='store_true',
                                 help='Disable update notification messages')
        version_group.add_argument('--include-pre-releases', action='store_true',
                                 help='Include pre-release versions when checking for updates')
    
    def _add_logging_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add logging configuration arguments."""
        log_group = parser.add_argument_group('Logging Options')
        log_level_group = log_group.add_mutually_exclusive_group()
        
        log_level_group.add_argument('-d', '--debug', action='store_true', 
                                   help='Enable debug logging')
        log_level_group.add_argument('-T', '--trace', action='store_true', 
                                   help='Enable trace logging (very verbose)')
        log_level_group.add_argument('-q', '--quiet', action='store_true', 
                                   help='Show only warnings and errors')
        log_level_group.add_argument('-Q', '--silent', action='store_true', 
                                   help='Show only errors')
        
        log_group.add_argument('--log-file', action='store_true', default=False,
                             help='Save logs to a timestamped file in .tonietoolbox folder')
    
    def parse_args(self, args=None) -> argparse.Namespace:
        """Parse arguments with validation."""
        parsed_args = self.parser.parse_args(args)
        self._validate_arguments(parsed_args)
        return parsed_args
    
    def _validate_arguments(self, args: argparse.Namespace) -> None:
        """Validate argument combinations and requirements."""
        # Check if source is required
        if args.input_filename is None and not self._has_special_commands(args):
            self.parser.error("the following arguments are required: SOURCE")
        
        # Validate Tonie tag format
        if args.append_tonie_tag:
            hex_tag = args.append_tonie_tag
            if not all(c in '0123456789abcdefABCDEF' for c in hex_tag) or len(hex_tag) != 8:
                self.parser.error("TAG must be an 8-character hexadecimal value")
    
    def _has_special_commands(self, args: argparse.Namespace) -> bool:
        """Check if args contain commands that don't require input files."""
        return (args.get_tags is not None or args.upload is not None or 
                args.install_integration or args.uninstall_integration or 
                args.config_integration or args.auto_download or 
                args.clear_version_cache or args.gui
                or args.check_updates_only or args.create_custom_json)