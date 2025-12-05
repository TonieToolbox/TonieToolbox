#!/usr/bin/env python3
"""
PyQt6-based GUI module for TonieToolbox.

Provides a modern Qt-based graphical user interface with:
- Clean architecture and separation of concerns
- Internationalization (I18n) support
- Robust state management
- Comprehensive theme system
- Proper error handling
- Threading management
- Event system integration

This module serves as an alternative to the tkinter-based GUI with improved
user experience and modern UI patterns.
"""

# Use centralized GUI dependency management
from ..dependencies.gui import get_gui_dependency_manager

_gui_manager = get_gui_dependency_manager()
_pyqt6_info = _gui_manager.check_pyqt6()

PYQT6_AVAILABLE = _pyqt6_info.available
PYQT6_ERROR = _pyqt6_info.error

# Import PyQt6 classes if available
if PYQT6_AVAILABLE:
    QApplication = _pyqt6_info.modules.get('QApplication')
    QCoreApplication = _pyqt6_info.modules.get('QCoreApplication')
else:
    QApplication = None
    QCoreApplication = None

from ..utils import get_logger

logger = get_logger(__name__)

# Main application class
if PYQT6_AVAILABLE:
    from .app.application import TonieToolboxQtApplication
    
    def qt_gui_player(taf_file_path=None, auto_play=False, plugin_manager=None):
        """
        Start the PyQt6 GUI application with support for single files and playlists.
        
        Args:
            taf_file_path: Optional path to the TAF file, directory, or playlist to play
            auto_play: If True and taf_file_path is provided, automatically start playback
            plugin_manager: Optional PluginManager instance for plugin support
        """
        from pathlib import Path
        
        if taf_file_path:
            logger.info(f"Starting PyQt6 GUI application with file: {taf_file_path}")
        else:
            logger.info("Starting PyQt6 GUI application")
        
        try:
            app = TonieToolboxQtApplication(plugin_manager=plugin_manager)
            
            if taf_file_path:
                # Determine if this is single file or playlist mode
                from ..media.player.play_mode_detector import PlayModeDetector
                play_mode, needs_discovery = PlayModeDetector.determine_play_mode(taf_file_path)
                
                def on_ready():
                    """Callback when application is ready."""
                    logger.debug(f"on_ready called for: {taf_file_path} (mode: {play_mode})")
                    player_controller = app.get_player_controller()
                    if not player_controller:
                        logger.warning("Player controller not available in on_ready callback")
                        return

                    def on_load_complete(success, loaded_path):
                        """Callback to auto-start playback after loading."""
                        if success and auto_play:
                            logger.info("Auto-starting playback")
                            player_controller.play()

                    if play_mode == 'single':
                        # Single file mode
                        if needs_discovery:
                            try:
                                actual_file = PlayModeDetector.get_single_file_from_input(taf_file_path)
                                file_path = Path(actual_file)
                            except ValueError as e:
                                logger.error(f"Error resolving single file: {e}")
                                return
                        else:
                            file_path = Path(taf_file_path)
                        
                        logger.info(f"Loading single file: {file_path}")
                        player_controller.load_file(file_path, callback=on_load_complete)
                    
                    else:
                        # Playlist mode
                        logger.info(f"Loading playlist from: {taf_file_path}")
                        player_controller.load_playlist(taf_file_path, callback=on_load_complete)
                
                app.on_ready(on_ready)
            
            return app.run()
            
        except Exception as e:
            logger.error(f"Failed to start PyQt6 GUI application: {e}")
            import traceback
            traceback.print_exc()
            return 1

else:
    def qt_gui_player(taf_file_path=None, auto_play=False):
        """Fallback function when PyQt6 is not available."""
        logger.error(f"PyQt6 is not available: {PYQT6_ERROR}")
        print(f"Error: PyQt6 is not available: {PYQT6_ERROR}")
        print("Please install PyQt6: pip install PyQt6==6.10.0")
        return 1

# Export main interfaces
__all__ = [
    'qt_gui_player',
    'PYQT6_AVAILABLE',
    'PYQT6_ERROR'
]

if PYQT6_AVAILABLE:
    __all__.extend([
        'TonieToolboxQtApplication'
    ])