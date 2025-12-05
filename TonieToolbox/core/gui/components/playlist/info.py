#!/usr/bin/env python3
"""
Playlist info panel for displaying playlist and current track information.
"""

from typing import Optional, Dict, Any
from pathlib import Path

try:
    from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, 
                                QScrollArea, QSizePolicy, QTextEdit, QLineEdit)
    from PyQt6.QtCore import pyqtSignal, Qt, QTimer
    from PyQt6.QtGui import QFont, QPixmap
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    # Mock classes for when PyQt6 is not available
    QWidget = object
    QLabel = object
    QVBoxLayout = object
    QHBoxLayout = object
    QFrame = object
    QScrollArea = object
    QSizePolicy = object
    QTextEdit = object
    pyqtSignal = lambda: None
    Qt = object
    QTimer = object
    QFont = object
    QPixmap = object

from ..base.component import QtBaseFrame
from ....utils import get_logger

logger = get_logger(__name__)


class PlaylistInfoPanel(QtBaseFrame):
    """
    Panel for displaying playlist information and current track details.
    Shows playlist metadata, current track info, and statistics.
    
    Signals:
        playlist_name_changed(str): Emitted when playlist name is edited by user
    """
    
    # Signals
    playlist_name_changed = pyqtSignal(str)  # new_name: str
    
    def __init__(self, parent=None, player_controller=None, **kwargs):
        """
        Initialize the playlist info panel.
        
        Args:
            parent: Parent widget
            player_controller: Reference to player controller
            **kwargs: Additional configuration
        """
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        theme_manager = kwargs.pop('theme_manager', None)
        
        super().__init__(parent, translation_manager=translation_manager, **kwargs)
        
        if not PYQT6_AVAILABLE:
            return
            
        self.player_controller = player_controller
        self.current_playlist_info = {}
        self.current_track_info = {}
        self._editing_playlist_name = False
        
        logger.debug("Playlist info panel initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        if not PYQT6_AVAILABLE:
            return
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        # Content layout
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Playlist info section
        playlist_frame = QFrame()
        playlist_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        playlist_layout = QVBoxLayout(playlist_frame)
        playlist_layout.setContentsMargins(8, 8, 8, 8)
        
        # Playlist title
        playlist_title = QLabel(self.tr("playlist", "info", "playlist_status"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        playlist_title.setFont(title_font)
        playlist_layout.addWidget(playlist_title)
        
        # Playlist details
        self.playlist_name_label = QLabel(self.tr("playlist", "info", "no_playlist_loaded"))
        self.playlist_name_label.setWordWrap(True)
        self.playlist_name_label.mousePressEvent = self._on_playlist_name_double_click
        self.playlist_name_label.setToolTip(self.tr("playlist", "info", "double_click_to_edit"))
        self.playlist_name_label.setStyleSheet("QLabel:hover { background-color: #f0f0f0; cursor: pointer; }")
        playlist_layout.addWidget(self.playlist_name_label)
        
        # Playlist name editor (hidden by default)
        self.playlist_name_edit = QLineEdit()
        self.playlist_name_edit.setVisible(False)
        self.playlist_name_edit.returnPressed.connect(self._save_playlist_name)
        self.playlist_name_edit.editingFinished.connect(self._cancel_playlist_name_edit)
        playlist_layout.addWidget(self.playlist_name_edit)
        
        self.playlist_stats_label = QLabel("")
        playlist_layout.addWidget(self.playlist_stats_label)
        
        self.playlist_duration_label = QLabel("")
        playlist_layout.addWidget(self.playlist_duration_label)
        
        layout.addWidget(playlist_frame)
        
        # Current track section
        track_frame = QFrame()
        track_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        track_layout = QVBoxLayout(track_frame)
        track_layout.setContentsMargins(8, 8, 8, 8)
        
        # Track title
        track_title = QLabel(self.tr("playlist", "info", "selected_track"))
        track_title.setFont(title_font)
        track_layout.addWidget(track_title)
        
        # Track details
        self.track_name_label = QLabel(self.tr("playlist", "info", "no_track_loaded"))
        self.track_name_label.setWordWrap(True)
        track_layout.addWidget(self.track_name_label)
        
        self.track_file_label = QLabel("")
        self.track_file_label.setWordWrap(True)
        self.track_file_label.setStyleSheet("color: #666; font-size: 9pt;")
        track_layout.addWidget(self.track_file_label)
        
        self.track_info_label = QLabel("")
        self.track_info_label.setWordWrap(True)
        track_layout.addWidget(self.track_info_label)
        
        layout.addWidget(track_frame)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        # Add scroll area to main layout (from QtBaseFrame) 
        self.main_layout.addWidget(scroll_area)
    
    def set_player_controller(self, controller):
        """Set the player controller reference."""
        self.player_controller = controller
    
    def update_playlist_info(self, playlist_info: Dict[str, Any]):
        """
        Update playlist information display.
        
        Args:
            playlist_info: Dictionary containing playlist metadata
        """
        if not PYQT6_AVAILABLE:
            return
            
        self.current_playlist_info = playlist_info
        
        # Determine display name
        # Check if we have a playlist by checking total_items, source_path, or playlist_name
        has_playlist = (
            playlist_info.get('has_playlist', False) or 
            playlist_info.get('total_items', 0) > 0 or
            playlist_info.get('source_path') is not None or
            playlist_info.get('playlist_name') is not None
        )
        
        if has_playlist:
            # Prioritize playlist name if available
            if playlist_info.get('playlist_name'):
                display_name = playlist_info['playlist_name']
            elif playlist_info.get('source_path'):
                source_path = playlist_info['source_path']
                if Path(source_path).is_dir():
                    display_name = self.tr("playlist", "info", "directory", name=Path(source_path).name)
                else:
                    display_name = self.tr("playlist", "info", "playlist", name=Path(source_path).name)
            else:
                display_name = self.tr("playlist", "info", "unnamed_playlist")
        else:
            display_name = self.tr("playlist", "info", "no_playlist_loaded")
        
        self.playlist_name_label.setText(display_name)
        
        # Update statistics
        total_items = playlist_info.get('total_items', 0)
        current_index = playlist_info.get('current_index', 0)
        
        if total_items > 1:
            stats_text = self.tr("playlist", "info", "tracks_playing", total=total_items, current=current_index + 1)
        elif total_items == 1:
            stats_text = self.tr("playlist", "info", "single_track")
        else:
            stats_text = self.tr("playlist", "info", "no_tracks")
            
        self.playlist_stats_label.setText(stats_text)
        
        # Update playlist settings
        self._update_settings_display(playlist_info)
        
        logger.debug(f"Updated playlist info: {display_name}, {total_items} tracks")
    
    def update_current_track_info(self, track_info: Dict[str, Any]):
        """
        Update current track information display.
        
        Args:
            track_info: Dictionary containing current track metadata
        """
        if not PYQT6_AVAILABLE:
            return
            
        self.current_track_info = track_info
        
        # Track name/title
        file_path = track_info.get('file_path', '')
        if file_path:
            path_obj = Path(file_path)
            track_name = track_info.get('title', path_obj.stem)
            self.track_name_label.setText(track_name)
            self.track_file_label.setText(str(path_obj))
        else:
            self.track_name_label.setText(self.tr("playlist", "info", "no_track_loaded"))
            self.track_file_label.setText("")
        
        # Track details
        details = []
        
        # Duration
        duration = track_info.get('total_time', '') or track_info.get('duration', '')
        if duration:
            details.append(self.tr("playlist", "info", "duration_label", duration=duration))
        
        # File size
        file_size = track_info.get('file_size', 0)
        if file_size:
            size_mb = file_size / (1024 * 1024)
            details.append(self.tr("playlist", "info", "size_label", size=f"{size_mb:.1f}"))
        
        # Audio format info
        channels = track_info.get('channels', 0)
        sample_rate = track_info.get('sample_rate', 0)
        if channels and sample_rate:
            details.append(self.tr("playlist", "info", "format_label", channels=channels, rate=sample_rate))
        
        # Bitrate
        bitrate = track_info.get('bitrate', 0)
        if bitrate:
            details.append(self.tr("playlist", "info", "bitrate_label", bitrate=bitrate))
        
        # Chapters - handle both chapter_count (int) and chapters (list)
        chapter_count = track_info.get('chapter_count', 0)
        if not chapter_count:
            chapters = track_info.get('chapters', [])
            if chapters:
                chapter_count = len(chapters) if isinstance(chapters, list) else chapters
        
        if chapter_count:
            details.append(self.tr("playlist", "info", "chapters_label", count=chapter_count))
        
        self.track_info_label.setText("\n".join(details))
        
        logger.debug(f"Updated track info: {track_name if file_path else 'None'}")
    
    def update_playback_progress(self, position: float, duration: float):
        """
        Update playback progress display.
        
        Args:
            position: Current position in seconds
            duration: Total duration in seconds
        """
        # This could be used to show current playback position
        # For now, we'll keep it simple and not clutter the info panel
        pass
    
    def _update_settings_display(self, playlist_info: Dict[str, Any]):
        """Update playlist settings display."""
        if not PYQT6_AVAILABLE:
            return
            
        settings = []
        
        # Auto-advance
        auto_advance = playlist_info.get('auto_advance', True)
        if auto_advance:
            settings.append(self.tr("playlist", "info", "auto_advance_enabled"))
        else:
            settings.append(self.tr("playlist", "info", "auto_advance_disabled"))
        
        # Shuffle
        is_shuffled = playlist_info.get('is_shuffled', False)
        if is_shuffled:
            settings.append(self.tr("playlist", "info", "shuffle_enabled"))
        
        # Repeat mode
        repeat_mode = playlist_info.get('repeat_mode', 'none')
        if repeat_mode != 'none':
            repeat_text = {
                'one': self.tr("playlist", "info", "repeat_one"),
                'all': self.tr("playlist", "info", "repeat_all")
            }.get(repeat_mode, repeat_mode)
            settings.append(self.tr("playlist", "info", "repeat_label", mode=repeat_text))
        
        # Settings display removed to avoid duplication with PlaylistControls
    
    def clear_info(self):
        """Clear all displayed information."""
        if not PYQT6_AVAILABLE:
            return
            
        self.playlist_name_label.setText(self.tr("playlist", "info", "no_playlist_loaded"))
        self.playlist_stats_label.setText("")
        self.playlist_duration_label.setText("")
        
        self.track_name_label.setText(self.tr("playlist", "info", "no_track_loaded"))
        self.track_file_label.setText("")
        self.track_info_label.setText("")
        
        logger.debug("Playlist info panel cleared")
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        if not PYQT6_AVAILABLE:
            return
        
        # Re-update playlist info if we have it
        if hasattr(self, 'current_playlist_info') and self.current_playlist_info:
            self.update_playlist_info(self.current_playlist_info)
        else:
            self.playlist_name_label.setText(self.tr("playlist", "info", "no_playlist_loaded"))
        
        # Re-update track info if we have it
        if hasattr(self, 'current_track_info') and self.current_track_info:
            self.update_current_track_info(self.current_track_info)
        else:
            self.track_name_label.setText(self.tr("playlist", "info", "no_track_loaded"))
        
        logger.debug("Playlist info retranslated")
    
    def _on_playlist_name_double_click(self, event):
        """Handle double-click on playlist name to enable editing."""
        if not PYQT6_AVAILABLE or self._editing_playlist_name:
            return
        
        # Check if it's a double-click (Qt doesn't provide native double-click for QLabel)
        # As a workaround, we'll just enable editing on single click for simplicity
        current_text = self.playlist_name_label.text()
        
        # Don't allow editing if no playlist is loaded
        if current_text == self.tr("playlist", "info", "no_playlist_loaded"):
            return
        
        # Switch to edit mode
        self._editing_playlist_name = True
        self.playlist_name_edit.setText(current_text)
        self.playlist_name_label.setVisible(False)
        self.playlist_name_edit.setVisible(True)
        self.playlist_name_edit.setFocus()
        self.playlist_name_edit.selectAll()
        
        logger.debug("Playlist name editing started")
    
    def _save_playlist_name(self):
        """Save the edited playlist name."""
        if not PYQT6_AVAILABLE or not self._editing_playlist_name:
            return
        
        new_name = self.playlist_name_edit.text().strip()
        
        if new_name and new_name != self.playlist_name_label.text():
            self.playlist_name_label.setText(new_name)
            self.playlist_name_changed.emit(new_name)
            logger.info(f"Playlist name changed to: {new_name}")
        
        # Exit edit mode
        self._exit_edit_mode()
    
    def _cancel_playlist_name_edit(self):
        """Cancel playlist name editing if focus is lost."""
        if not PYQT6_AVAILABLE or not self._editing_playlist_name:
            return
        
        # Only cancel if Enter wasn't pressed (which calls _save_playlist_name)
        # This is called on editingFinished which happens after returnPressed
        # So we need to use a flag or just always exit edit mode here
        if self.playlist_name_edit.isVisible():
            logger.debug("Playlist name editing cancelled")
            self._exit_edit_mode()
    
    def _exit_edit_mode(self):
        """Exit playlist name editing mode."""
        self._editing_playlist_name = False
        self.playlist_name_edit.setVisible(False)
        self.playlist_name_label.setVisible(True)
