#!/usr/bin/env python3
"""
Playlist controls component for managing playlist playback options.
"""

from typing import Optional

try:
    from PyQt6.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, 
                                QLabel, QCheckBox, QComboBox, QFrame,
                                QSizePolicy, QButtonGroup)
    from PyQt6.QtCore import pyqtSignal, Qt
    from PyQt6.QtGui import QFont, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    # Mock classes for when PyQt6 is not available
    QPushButton = object
    QHBoxLayout = object
    QVBoxLayout = object
    QLabel = object
    QCheckBox = object
    QComboBox = object
    QFrame = object
    QSizePolicy = object
    QButtonGroup = object
    pyqtSignal = lambda: None
    Qt = object
    QFont = object
    QIcon = object

from ..base.component import QtBaseFrame
from ....utils import get_logger

logger = get_logger(__name__)


class PlaylistControls(QtBaseFrame):
    """
    Controls for playlist-specific functionality like shuffle, repeat, navigation.
    """
    
    # Signals
    shuffle_toggled = pyqtSignal(bool)  # Shuffle mode toggled
    repeat_mode_changed = pyqtSignal(str)  # Repeat mode changed ('none', 'one', 'all')
    auto_advance_toggled = pyqtSignal(bool)  # Auto-advance toggle
    
    def __init__(self, parent=None, player_controller=None, **kwargs):
        """
        Initialize playlist controls.
        
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
        
        logger.debug("Playlist controls initialized")
    
    def _setup_component(self):
        """Setup component-specific functionality after UI is created."""
        # Initially disabled until playlist is loaded  
        self.set_playlist_mode(False)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup the user interface."""
        if not PYQT6_AVAILABLE:
            return
            
        # Create content frame (similar to PlayerInfoPanel pattern)
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(8)
        
        # Settings header
        settings_label = QLabel(self.tr("playlist", "controls", "playlist_options"))
        settings_font = QFont()
        settings_font.setPointSize(10)
        settings_font.setBold(True)
        settings_label.setFont(settings_font)
        content_layout.addWidget(settings_label)
        
        # Playlist options frame
        options_frame = QFrame()
        options_layout = QVBoxLayout(options_frame)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(5)
        
        # Auto-advance checkbox
        self.auto_advance_cb = QCheckBox(self.tr("playlist", "controls", "auto_advance"))
        self.auto_advance_cb.setToolTip(self.tr("playlist", "controls", "auto_advance_tooltip"))
        self.auto_advance_cb.setChecked(True)  # Default enabled
        options_layout.addWidget(self.auto_advance_cb)
        
        # Shuffle checkbox
        self.shuffle_cb = QCheckBox(self.tr("playlist", "controls", "shuffle"))
        self.shuffle_cb.setToolTip(self.tr("playlist", "controls", "shuffle_tooltip"))
        options_layout.addWidget(self.shuffle_cb)
        
        # Repeat mode dropdown
        repeat_frame = QFrame()
        repeat_layout = QHBoxLayout(repeat_frame)
        repeat_layout.setContentsMargins(0, 0, 0, 0)
        
        repeat_label = QLabel(self.tr("playlist", "controls", "repeat"))
        repeat_layout.addWidget(repeat_label)
        
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems([
            self.tr("playlist", "controls", "repeat_none"),
            self.tr("playlist", "controls", "repeat_one"),
            self.tr("playlist", "controls", "repeat_all")
        ])
        self.repeat_combo.setToolTip(self.tr("playlist", "controls", "repeat_tooltip"))
        repeat_layout.addWidget(self.repeat_combo)
        
        options_layout.addWidget(repeat_frame)
        
        content_layout.addWidget(options_frame)
        
        # Status label for track position
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(9)
        self.status_label.setFont(status_font)
        content_layout.addWidget(self.status_label)
        
        # Add stretch to push controls to top
        content_layout.addStretch()
        
        # Add content frame to main layout (from QtBaseFrame)
        self.main_layout.addWidget(content_frame)
    
    def _setup_connections(self):
        """Setup signal connections."""
        if not PYQT6_AVAILABLE:
            return
            
        # Playlist options
        self.auto_advance_cb.toggled.connect(self._on_auto_advance_toggled)
        self.shuffle_cb.toggled.connect(self._on_shuffle_toggled)
        self.repeat_combo.currentTextChanged.connect(self._on_repeat_changed)
    
    def set_player_controller(self, controller):
        """Set the player controller reference."""
        self.player_controller = controller
    
    def set_playlist_mode(self, enabled: bool, has_multiple_tracks: bool = True):
        """
        Enable or disable playlist mode controls.
        
        Args:
            enabled: True if playlist is loaded and controls should be enabled
            has_multiple_tracks: Whether playlist has multiple tracks (unused, kept for compatibility)
        """
        if not PYQT6_AVAILABLE:
            return
        
        # Enable/disable all playlist options when playlist is loaded
        self.auto_advance_cb.setEnabled(enabled)
        self.shuffle_cb.setEnabled(enabled)
        self.repeat_combo.setEnabled(enabled)
        
        logger.debug(f"Playlist controls: {'enabled' if enabled else 'disabled'}")
    
    def update_playlist_status(self, current_index: int, total_tracks: int, 
                              is_shuffled: bool, repeat_mode: str):
        """
        Update controls to reflect current playlist state.
        
        Args:
            current_index: Current track index (0-based)
            total_tracks: Total number of tracks
            is_shuffled: Whether shuffle is enabled
            repeat_mode: Current repeat mode ('none', 'one', 'all')
        """
        if not PYQT6_AVAILABLE:
            return
            
        # Playlist controls are always enabled when in playlist mode
        # Track navigation is handled by PlayerControls
        
        # Update shuffle state (without triggering signal)
        self.shuffle_cb.blockSignals(True)
        self.shuffle_cb.setChecked(is_shuffled)
        self.shuffle_cb.blockSignals(False)
        
        # Update repeat mode (without triggering signal)
        repeat_map = {'none': 0, 'one': 1, 'all': 2}
        if repeat_mode.lower() in repeat_map:
            self.repeat_combo.blockSignals(True)
            self.repeat_combo.setCurrentIndex(repeat_map[repeat_mode.lower()])
            self.repeat_combo.blockSignals(False)
        
        # Update status
        track_num = current_index + 1
        status_text = self.tr("playlist", "controls", "track_status").format(
            current=track_num, total=total_tracks
        )
        self.status_label.setText(status_text)
        
        logger.debug(f"Updated playlist status: {track_num}/{total_tracks}, "
                    f"shuffle={is_shuffled}, repeat={repeat_mode}")
    
    def get_current_settings(self) -> dict:
        """
        Get current playlist settings.
        
        Returns:
            Dictionary with current settings
        """
        if not PYQT6_AVAILABLE:
            return {}
            
        repeat_modes = ['none', 'one', 'all']
        return {
            'auto_advance': self.auto_advance_cb.isChecked(),
            'shuffle': self.shuffle_cb.isChecked(),
            'repeat_mode': repeat_modes[self.repeat_combo.currentIndex()]
        }
    

    
    def _on_auto_advance_toggled(self, enabled: bool):
        """Handle auto-advance checkbox toggled."""
        self.auto_advance_toggled.emit(enabled)
        logger.debug(f"Auto-advance toggled: {enabled}")
    
    def _on_shuffle_toggled(self, enabled: bool):
        """Handle shuffle checkbox toggled."""
        self.shuffle_toggled.emit(enabled)
        logger.debug(f"Shuffle toggled: {enabled}")
    
    def _on_repeat_changed(self, text: str):
        """Handle repeat mode changed."""
        # Use index instead of text to avoid translation issues
        index = self.repeat_combo.currentIndex()
        repeat_modes = ['none', 'one', 'all']
        repeat_mode = repeat_modes[index] if 0 <= index < len(repeat_modes) else 'none'
        self.repeat_mode_changed.emit(repeat_mode)
        logger.debug(f"Repeat mode changed: {repeat_mode} (index: {index})")
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        if not PYQT6_AVAILABLE:
            return
        
        # Update labels and checkboxes
        if hasattr(self, 'auto_advance_cb') and self.auto_advance_cb:
            checked = self.auto_advance_cb.isChecked()
            self.auto_advance_cb.setText(self.tr("playlist", "controls", "auto_advance"))
            self.auto_advance_cb.setToolTip(self.tr("playlist", "controls", "auto_advance_tooltip"))
            self.auto_advance_cb.setChecked(checked)
        
        if hasattr(self, 'shuffle_cb') and self.shuffle_cb:
            checked = self.shuffle_cb.isChecked()
            self.shuffle_cb.setText(self.tr("playlist", "controls", "shuffle"))
            self.shuffle_cb.setToolTip(self.tr("playlist", "controls", "shuffle_tooltip"))
            self.shuffle_cb.setChecked(checked)
        
        # Update repeat combo box (block signals to prevent unwanted triggers)
        if hasattr(self, 'repeat_combo') and self.repeat_combo:
            current_index = self.repeat_combo.currentIndex()
            self.repeat_combo.blockSignals(True)
            self.repeat_combo.clear()
            self.repeat_combo.addItems([
                self.tr("playlist", "controls", "repeat_none"),
                self.tr("playlist", "controls", "repeat_one"),
                self.tr("playlist", "controls", "repeat_all")
            ])
            self.repeat_combo.setToolTip(self.tr("playlist", "controls", "repeat_tooltip"))
            self.repeat_combo.setCurrentIndex(current_index)
            self.repeat_combo.blockSignals(False)
        
        logger.debug("Playlist controls retranslated")