"""
Unit tests for command-line argument parsing.

These tests verify that the argument parser correctly handles various command-line
input combinations and validates arguments appropriately.
"""

from pathlib import Path
import tempfile
import sys

try:
    import pytest
except ImportError:
    pass

# Import the modules we're testing
try:
    from TonieToolbox.core.parser import ArgumentParserFactory
except ImportError:
    # Fallback for direct imports
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from TonieToolbox.core.parser import ArgumentParserFactory


class TestArgumentParser:
    """Test command-line argument parsing functionality."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Use factory to create parser with system defaults
        self.parser = ArgumentParserFactory.create_parser(None)
    
    def test_basic_file_conversion_args(self):
        """Test parsing basic file conversion arguments."""
        args = self.parser.parse_args(['input.mp3'])
        
        assert args.input_filename == 'input.mp3'
        assert args.output_filename is None  # Should default to None
        assert args.bitrate == 128  # Default bitrate
        assert args.cbr is False  # Default VBR mode
        assert args.recursive is False
    
    def test_input_and_output_files(self):
        """Test parsing with both input and output files specified."""
        args = self.parser.parse_args(['input.mp3', 'output.taf'])
        
        assert args.input_filename == 'input.mp3'
        assert args.output_filename == 'output.taf'
    
    def test_bitrate_configuration(self):
        """Test bitrate argument parsing."""
        # Test custom bitrate
        args = self.parser.parse_args(['input.mp3', '--bitrate', '192'])
        assert args.bitrate == 192
        
        # Test CBR mode
        args = self.parser.parse_args(['input.mp3', '--cbr'])
        assert args.cbr is True
        
        # Test combined bitrate and CBR
        args = self.parser.parse_args(['input.mp3', '--bitrate', '256', '--cbr'])
        assert args.bitrate == 256
        assert args.cbr is True
    
    def test_tonie_tag_validation(self):
        """Test Tonie tag argument validation."""
        # Valid 8-character hex tag
        args = self.parser.parse_args(['input.mp3', '--append-tonie-tag', '7F8A6B2E'])
        assert args.append_tonie_tag == '7F8A6B2E'
        
        # Test with lowercase hex
        args = self.parser.parse_args(['input.mp3', '--append-tonie-tag', 'abcdef12'])
        assert args.append_tonie_tag == 'abcdef12'
        
        # Test invalid tag (wrong length)
        with pytest.raises(SystemExit):  # argparse calls sys.exit on error
            self.parser.parse_args(['input.mp3', '--append-tonie-tag', '123'])
        
        # Test invalid tag (non-hex characters)
        with pytest.raises(SystemExit):
            self.parser.parse_args(['input.mp3', '--append-tonie-tag', 'INVALID!'])
    
    def test_file_operations_flags(self):
        """Test file operation flags."""
        # Test info flag
        args = self.parser.parse_args(['file.taf', '--info'])
        assert args.info is True
        
        # Split flag removed with opus-tools dependency
        # args = self.parser.parse_args(['file.taf', '--split'])
        # assert args.split is True
        
        # Test recursive flag
        args = self.parser.parse_args(['directory/', '--recursive'])
        assert args.recursive is True
        
        # Test force creation
        args = self.parser.parse_args(['input.mp3', '--force-creation'])
        assert args.force_creation is True
    
    def test_media_tag_arguments(self):
        """Test media tag related arguments."""
        # Test use media tags
        args = self.parser.parse_args(['input.mp3', '--use-media-tags'])
        assert args.use_media_tags is True
        
        # Test name template
        template = "{artist} - {album}"
        args = self.parser.parse_args(['input.mp3', '--name-template', template])
        assert args.name_template == template
        
        # Test output template
        path_template = "/music/{albumartist}/{album}"
        args = self.parser.parse_args(['input.mp3', '--output-to-template', path_template])
        assert args.output_to_template == path_template
        
        # Test show tags
        args = self.parser.parse_args(['input.mp3', '--show-media-tags'])
        assert args.show_media_tags is True
    
    def test_teddycloud_arguments(self):
        """Test TeddyCloud upload arguments."""
        # Basic upload
        url = "https://teddycloud.example.com"
        args = self.parser.parse_args(['input.taf', '--upload', url])
        assert args.upload == url
        
        # Upload with artwork
        args = self.parser.parse_args(['input.taf', '--upload', url, '--include-artwork'])
        assert args.upload == url
        assert args.include_artwork is True
        
        # Upload with custom path
        custom_path = "/custom/path"
        args = self.parser.parse_args(['input.taf', '--upload', url, '--path', custom_path])
        assert args.path == custom_path
        
        # Upload with authentication
        args = self.parser.parse_args([
            'input.taf', '--upload', url, 
            '--username', 'user', '--password', 'pass'
        ])
        assert args.username == 'user'
        assert args.password == 'pass'
        
        # SSL options
        args = self.parser.parse_args(['input.taf', '--upload', url, '--ignore-ssl-verify'])
        assert args.ignore_ssl_verify is True
    
    def test_logging_arguments(self):
        """Test logging configuration arguments."""
        # Test debug mode
        args = self.parser.parse_args(['input.mp3', '--debug'])
        assert args.debug is True
        
        # Test quiet mode
        args = self.parser.parse_args(['input.mp3', '--quiet'])
        assert args.quiet is True
        
        # Test silent mode
        args = self.parser.parse_args(['input.mp3', '--silent'])
        assert args.silent is True
        
        # Test trace mode
        args = self.parser.parse_args(['input.mp3', '--trace'])
        assert args.trace is True
        
        # Test log file
        args = self.parser.parse_args(['input.mp3', '--log-file'])
        assert args.log_file is True
        
        # Test mutually exclusive logging levels
        with pytest.raises(SystemExit):  # Should conflict
            self.parser.parse_args(['input.mp3', '--debug', '--quiet'])
    
    def test_version_arguments(self):
        """Test version-related arguments."""
        # Skip update check
        args = self.parser.parse_args(['input.mp3', '--skip-update-check'])
        assert args.skip_update_check is True
        
        # Force update check
        args = self.parser.parse_args(['input.mp3', '--force-update-check'])
        assert args.force_update_check is True
        
        # Clear cache
        args = self.parser.parse_args(['--clear-version-cache'])
        assert args.clear_version_cache is True
    
    def test_integration_arguments(self):
        """Test system integration arguments."""
        # Install integration
        args = self.parser.parse_args(['--install-integration'])
        assert args.install_integration is True
        
        # Uninstall integration
        args = self.parser.parse_args(['--uninstall-integration'])
        assert args.uninstall_integration is True
        
        # Config integration
        args = self.parser.parse_args(['--config-integration'])
        assert args.config_integration is True
    
    def test_dependency_arguments(self):
        """Test dependency management arguments."""
        # Auto download
        args = self.parser.parse_args(['input.mp3', '--auto-download'])
        assert args.auto_download is True
        
        # Custom FFmpeg path
        ffmpeg_path = '/custom/ffmpeg'
        args = self.parser.parse_args(['input.mp3', '--ffmpeg', ffmpeg_path])
        assert args.ffmpeg == ffmpeg_path
        
        # Note: --opusenc argument was removed from the parser
    
    def test_file_comparison_arguments(self):
        """Test file comparison arguments."""
        # Basic comparison
        args = self.parser.parse_args(['file1.taf', '--compare', 'file2.taf'])
        assert args.compare == 'file2.taf'
        
        # Detailed comparison
        args = self.parser.parse_args(['file1.taf', '--compare', 'file2.taf', '--detailed-compare'])
        assert args.compare == 'file2.taf'
        assert args.detailed_compare is True
    
    def test_special_commands_no_input_required(self):
        """Test commands that don't require input files."""
        # Version display (this will exit, so we test the parser creation)
        try:
            args = self.parser.parse_args(['--version'])
        except SystemExit:
            pass  # Expected behavior for version argument
        
        # Clear cache
        args = self.parser.parse_args(['--clear-version-cache'])
        assert args.clear_version_cache is True
        
        # Install integration
        args = self.parser.parse_args(['--install-integration'])
        assert args.install_integration is True
    
    def test_invalid_argument_combinations(self):
        """Test invalid argument combinations."""
        # Multiple mutually exclusive logging options
        with pytest.raises(SystemExit):
            self.parser.parse_args(['input.mp3', '--debug', '--silent'])
        
        with pytest.raises(SystemExit):
            self.parser.parse_args(['input.mp3', '--quiet', '--trace'])
    
    def test_timestamp_argument(self):
        """Test timestamp argument parsing."""
        # Unix timestamp
        args = self.parser.parse_args(['input.mp3', '--timestamp', '1234567890'])
        assert args.user_timestamp == '1234567890'
        
        # Hex timestamp
        args = self.parser.parse_args(['input.mp3', '--timestamp', '0x6803C9EA'])
        assert args.user_timestamp == '0x6803C9EA'
        
        # Reference file
        args = self.parser.parse_args(['input.mp3', '--timestamp', 'reference.taf'])
        assert args.user_timestamp == 'reference.taf'
    
    def test_help_generation(self):
        """Test that help can be generated without errors."""
        try:
            self.parser.parse_args(['--help'])
        except SystemExit:
            pass  # Expected behavior for help argument
        
        # Ensure parser has all expected argument groups
        parser = self.parser.parser
        argument_groups = [group.title for group in parser._action_groups]
        
        expected_groups = [
            'TeddyCloud Options',
            'Media Tag Options', 
            'Version Check Options',
            'Logging Options'
        ]
        
        for group in expected_groups:
            assert group in argument_groups, f"Expected argument group '{group}' not found"


class TestArgumentValidation:
    """Test argument validation logic."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.parser = ArgumentParserFactory.create_parser(None)
    
    def test_missing_required_source(self):
        """Test that missing source argument is detected."""
        # No arguments at all should fail
        with pytest.raises(SystemExit):
            self.parser.parse_args([])
    
    def test_tonie_tag_validation_details(self):
        """Test detailed Tonie tag validation."""
        # Test all valid hex characters
        valid_chars = "0123456789abcdefABCDEF"
        valid_tag = "".join([valid_chars[i % len(valid_chars)] for i in range(8)])
        
        args = self.parser.parse_args(['input.mp3', '--append-tonie-tag', valid_tag])
        assert args.append_tonie_tag == valid_tag
        
        # Test invalid characters
        invalid_tags = [
            "1234567G",  # Invalid character G
            "1234567!",  # Special character
            "1234567 ",  # Space
            "123456",    # Too short
            "123456789", # Too long
        ]
        
        for invalid_tag in invalid_tags:
            with pytest.raises(SystemExit):
                self.parser.parse_args(['input.mp3', '--append-tonie-tag', invalid_tag])


if __name__ == "__main__":
    # Run tests if called directly
    try:
        import pytest
        pytest.main([__file__])
    except ImportError:
        print("pytest not available, running basic tests...")
        # Basic test runner without pytest
        test_class = TestArgumentParser()
        test_class.setup_method()
        
        # Run a few basic tests
        test_methods = [
            test_class.test_basic_file_conversion_args,
            test_class.test_bitrate_configuration,
            test_class.test_file_operations_flags,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                print(f"✓ {test_method.__name__}")
            except Exception as e:
                print(f"✗ {test_method.__name__}: {e}")