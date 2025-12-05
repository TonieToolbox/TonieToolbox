#!/usr/bin/env python3
"""
Player info panel component for PyQt6 GUI.
Displays file information and metadata.
"""
try:
    from PyQt6.QtWidgets import QLabel, QScrollArea, QFrame, QVBoxLayout
    from PyQt6.QtCore import pyqtSignal, Qt
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QLabel = object
    QScrollArea = object
    QFrame = object
    QVBoxLayout = object
    pyqtSignal = lambda: None
    Qt = object
    QFont = object

from typing import TYPE_CHECKING, Union
from ..base.component import QtBaseFrame
from TonieToolbox.core.utils import get_logger

if TYPE_CHECKING:
    from ....analysis.models import TafAnalysisResult

logger = get_logger(__name__)


class PlayerInfoPanel(QtBaseFrame):
    """
    Player information panel component.
    Displays file metadata, chapters, and other information.
    """
    
    def __init__(self, parent=None, **kwargs):
        """
        Initialize player info panel.
        
        Args:
            parent: Parent widget
            **kwargs: Additional configuration
        """
        # UI components
        self.scroll_area = None
        self.info_frame = None
        self.info_layout = None
        
        # Content labels
        self.title_label = None
        self.no_file_label = None
        self.info_labels = {}
        
        # State
        self._file_info = {}
        self._chapters = []
        
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        theme_manager = kwargs.pop('theme_manager', None)
        
        super().__init__(parent, translation_manager=translation_manager, **kwargs)
        
        # Set up domain event subscriptions
        self._setup_events()
    
    def _setup_ui(self):
        """Create the info panel UI."""
        if not PYQT6_AVAILABLE:
            return
        
        # Create scroll area for info content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create info frame
        self.info_frame = QFrame()
        self.info_layout = QVBoxLayout(self.info_frame)
        self.info_layout.setContentsMargins(10, 10, 10, 10)
        self.info_layout.setSpacing(8)
        
        # Title label
        self.title_label = QLabel(self.tr("player", "info", "file_info"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setProperty("class", "title")
        self.info_layout.addWidget(self.title_label)
        
        # No file message
        self.no_file_label = QLabel(self.tr("player", "info", "no_file"))
        self.no_file_label.setProperty("class", "subtitle")
        self.no_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_layout.addWidget(self.no_file_label)
        
        # Spacer
        self.info_layout.addStretch()
        
        # Set up scroll area
        self.scroll_area.setWidget(self.info_frame)
        self.main_layout.addWidget(self.scroll_area)
        
        logger.debug("Player info panel UI created")
    
    def _setup_events(self):
        """Setup component-specific functionality."""
        # Subscribe to domain events directly
        from ....events import get_event_bus
        from ....events.player_events import PlayerFileLoadedEvent, PlayerStateChangedEvent
        
        self.event_bus = get_event_bus()
        logger.debug(f"Setting up domain event subscriptions on event_bus: {id(self.event_bus)}")
        
        # Create wrapper functions to avoid weak reference issues with bound methods
        def file_loaded_handler(event):
            self._on_file_loaded(event)
            
        def state_changed_handler(event):
            self._on_state_changed(event)
            
        # Store references to prevent garbage collection
        self._file_loaded_handler = file_loaded_handler
        self._state_changed_handler = state_changed_handler
        
        self.event_bus.subscribe(PlayerFileLoadedEvent, file_loaded_handler)
        self.event_bus.subscribe(PlayerStateChangedEvent, state_changed_handler)
        logger.debug("Domain event subscriptions completed")
    
    def _on_file_loaded(self, event):
        """
        Handle file loaded domain event.
        
        Args:
            event: PlayerFileLoadedEvent
        """
        try:
            logger.info(f"INFO PANEL: Received PlayerFileLoadedEvent: {event.file_path}")

            # Extract analysis result from domain event
            analysis_result = event.analysis_result
            file_path = str(event.file_path)
            
            # Update with domain object data
            if analysis_result:
                self.set_analysis_result(analysis_result, file_path)
            else:
                logger.warning("No analysis result available in PlayerFileLoadedEvent")

        except Exception as e:
            logger.error(f"Error handling PlayerFileLoadedEvent in info panel: {e}")
    
    def _on_state_changed(self, event):
        """
        Handle player state change domain event.
        
        Args:
            event: PlayerStateChangedEvent
        """
        try:
            # Extract state from domain event
            state_str = event.state if hasattr(event, 'state') else str(event.new_state if hasattr(event, 'new_state') else "")
            state_str = str(state_str).lower()

            if state_str == "loading":
                self._show_loading()
            elif state_str == "error":
                self._show_error()
        except Exception as e:
            logger.error(f"Error handling state payload in info panel: {e}")
    
    def set_analysis_result(self, analysis_result: 'TafAnalysisResult', file_path: str):
        """
        Update the file information display from domain object.
        
        Args:
            analysis_result: TAF analysis domain object
            file_path: Path to the file
        """
        from pathlib import Path
        from ....analysis.models import TafAnalysisResult
        
        self._analysis_result = analysis_result
        self._file_path = file_path
        
        # Convert chapters from domain objects to the format expected by GUI
        self._chapters = [
            {
                'index': i,
                'title': chapter.title,
                'duration': chapter.seconds,
                'start': sum(c.seconds for c in analysis_result.tonie_header.chapters[:i])
            }
            for i, chapter in enumerate(analysis_result.tonie_header.chapters)
        ]
        
        # Convert analysis result to file_info format for display
        self._file_info = {
            'filename': Path(file_path).name,
            'file_size': analysis_result.file_size,
            'audio_size': analysis_result.audio_size,
            'sha1_hash': analysis_result.sha1_hash,
            'valid': analysis_result.valid,
            'sample_rate': analysis_result.opus_info.sample_rate,
            'channels': analysis_result.opus_info.channels,
            'bitstream_serial': analysis_result.opus_info.bitstream_serial,
            'opus_version': analysis_result.opus_info.version,
            'page_count': analysis_result.audio_analysis.page_count,
            'total_time': analysis_result.audio_analysis.duration_formatted,
            'duration': analysis_result.audio_analysis.duration_seconds,
            'bitrate': analysis_result.audio_analysis.bitrate_kbps,
            'opus_comments': analysis_result.opus_info.comments,
            'chapters': self._chapters
        }
        
        self._update_info_display()
    
    def set_file_info(self, file_info: dict):
        """
        Update the file information display (legacy method).
        
        .. deprecated:: 0.6.0
            Use :meth:`update_display` instead with the PlayerModel directly.
            This method will be removed in version 1.0.0.
        
        Args:
            file_info: Dictionary with file information
        """
        import warnings
        warnings.warn(
            "set_file_info() is deprecated and will be removed in version 1.0.0. "
            "Use update_display() with PlayerModel instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._file_info = file_info
        self._update_info_display()
    
    def set_chapters(self, chapters: list):
        """
        Update the chapters information.
        
        Args:
            chapters: List of chapter information
        """
        self._chapters = chapters
        self._update_info_display()
    
    def set_player_controller(self, player_controller):
        """Set or update the player controller reference."""
        self.player_controller = player_controller
        # Optionally reconnect signals here if needed
    
    def _update_info_display(self):
        """Update the information display."""
        if not self.info_layout:
            return
        
        # Clear existing info labels
        self._clear_info_labels()
        
        if not self._file_info:
            self.no_file_label.setVisible(True)
            return
        
        self.no_file_label.setVisible(False)
        
        # Add file information
        self._add_file_info_section()
        
        # Add chapters information if available
        if self._chapters:
            self._add_chapters_section()
    
    def _clear_info_labels(self):
        """Clear existing info labels."""
        for label in self.info_labels.values():
            if label:
                label.setParent(None)
                label.deleteLater()
        
        self.info_labels.clear()
    
    def _add_file_info_section(self):
        """Add file information section."""
        if not self._file_info:
            return
        
        # File name
        if 'filename' in self._file_info:
            self._add_info_item(
                "File", 
                self._file_info['filename']
            )
        
        # Duration
        if 'duration' in self._file_info:
            duration_str = self._format_duration(self._file_info['duration'])
            self._add_info_item(
                self.tr("player", "info", "duration", duration=""), 
                duration_str
            )
        
        # File size
        if 'file_size' in self._file_info:
            size_str = self._format_file_size(self._file_info['file_size'])
            self._add_info_item(
                self.tr("player", "info", "file_size", size=""), 
                size_str
            )
        
        # Sample rate
        if 'sample_rate' in self._file_info:
            self._add_info_item(
                self.tr("player", "info", "sample_rate", rate=""), 
                f"{self._file_info['sample_rate']} Hz"
            )
        
        # Channels
        if 'channels' in self._file_info:
            self._add_info_item(
                self.tr("player", "info", "channels", channels=""), 
                str(self._file_info['channels'])
            )
        
        # Bitrate
        if 'bitrate' in self._file_info:
            self._add_info_item(
                self.tr("player", "info", "bitrate", bitrate=""), 
                f"{self._file_info['bitrate']} kbps"
            )
    
    def _add_chapters_section(self):
        """Add chapters information section."""
        if not self._chapters:
            return
        
        # Add separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.info_layout.addWidget(separator)
        
        # Chapters header
        chapters_label = QLabel(self.tr("player", "info", "chapters", count=len(self._chapters)))
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setWeight(QFont.Weight.Bold)
        chapters_label.setFont(header_font)
        chapters_label.setProperty("class", "subtitle")
        self.info_layout.addWidget(chapters_label)
        
        # Chapter list
        for i, chapter in enumerate(self._chapters):
            chapter_text = f"Chapter {i + 1}"
            if isinstance(chapter, dict):
                if 'title' in chapter:
                    chapter_text = chapter['title']
                elif 'name' in chapter:
                    chapter_text = chapter['name']
                
                # Add duration if available
                if 'duration' in chapter:
                    duration_str = self._format_duration(chapter['duration'])
                    chapter_text += f" ({duration_str})"
            
            chapter_label = QLabel(f"  {chapter_text}")
            chapter_label.setProperty("class", "info")
            self.info_layout.addWidget(chapter_label)
    
    def _add_info_item(self, label: str, value: str):
        """
        Add an information item.
        
        Args:
            label: Information label
            value: Information value
        """
        info_text = f"{label}: {value}"
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        self.info_layout.addWidget(info_label)
        
        # Store reference for cleanup
        key = f"info_{len(self.info_labels)}"
        self.info_labels[key] = info_label
    
    def _format_duration(self, duration: Union[int, float, str]) -> str:
        """
        Format duration for display.
        
        Args:
            duration: Duration in seconds or as string
            
        Returns:
            Formatted duration string
        """
        if isinstance(duration, str):
            return duration
        
        try:
            seconds = float(duration)
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            
            if minutes >= 60:
                hours = minutes // 60
                minutes = minutes % 60
                return f"{hours}:{minutes:02d}:{secs:02d}"
            else:
                return f"{minutes}:{secs:02d}"
        except (ValueError, TypeError):
            return str(duration)
    
    def _format_file_size(self, size: Union[int, float, str]) -> str:
        """
        Format file size for display.
        
        Args:
            size: File size in bytes
            
        Returns:
            Formatted size string
        """
        try:
            size_bytes = int(size)
            
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except (ValueError, TypeError):
            return str(size)
    
    def _show_loading(self):
        """Show loading state."""
        self._clear_info_labels()
        self.no_file_label.setText(self.tr("player", "status", "loading"))
        self.no_file_label.setVisible(True)
    
    def _show_error(self):
        """Show error state."""
        self._clear_info_labels()
        self.no_file_label.setText(self.tr("player", "status", "error"))
        self.no_file_label.setProperty("class", "error")
        self.no_file_label.setVisible(True)
    
    def clear_info(self):
        """Clear all information."""
        self._file_info = {}
        self._chapters = []
        self._clear_info_labels()
        self.no_file_label.setText(self.tr("player", "info", "no_file"))
        self.no_file_label.setProperty("class", "subtitle")
        self.no_file_label.setVisible(True)
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        if not PYQT6_AVAILABLE:
            return
        
        # Update title label
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setText(self.tr("player", "info", "file_info"))
        
        # Re-update file info if we have it
        if self._file_info:
            self.update_file_info(self._file_info, self._chapters)
        else:
            if hasattr(self, 'no_file_label') and self.no_file_label:
                self.no_file_label.setText(self.tr("player", "info", "no_file"))
        
        logger.debug("Player info panel retranslated")
    
    def _cleanup_component(self):
        """Component-specific cleanup."""
        self._clear_info_labels()
        logger.debug("Cleaning up player info panel")