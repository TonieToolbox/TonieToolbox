#!/usr/bin/env python3
"""
Player controls component for PyQt6 GUI.
Handles play, pause, stop, and chapter navigation.
"""
from typing import Optional, Callable

try:
    from PyQt6.QtWidgets import QPushButton, QHBoxLayout, QSizePolicy, QSlider, QLabel
    from PyQt6.QtCore import pyqtSignal, Qt
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QPushButton = object
    QHBoxLayout = object
    QSizePolicy = object
    QSlider = object
    QLabel = object
    pyqtSignal = lambda: None
    Qt = object
    QFont = object

from ..base.component import QtBaseFrame
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class PlayerControls(QtBaseFrame):
    """
    Audio player control buttons component.
    Handles play/pause, stop, previous/next chapter functionality.
    """
    
    # Signals
    play_toggle_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    prev_chapter_clicked = pyqtSignal()
    next_chapter_clicked = pyqtSignal()
    prev_track_clicked = pyqtSignal()  # Previous track in playlist
    next_track_clicked = pyqtSignal()  # Next track in playlist
    volume_changed = pyqtSignal(float)  # volume level (0.0 to 1.0)
    mute_toggled = pyqtSignal(bool)     # mute state (True = muted)
    
    def __init__(self, parent=None, **kwargs):
        """
        Initialize player controls.
        
        Args:
            parent: Parent widget
            **kwargs: Additional configuration
        """
        # Button references
        self.prev_track_button = None   # Previous track in playlist
        self.prev_button = None         # Previous chapter
        self.play_button = None
        self.stop_button = None
        self.next_button = None         # Next chapter  
        self.next_track_button = None   # Next track in playlist
        
        # Volume controls
        self.mute_button = None
        self.volume_slider = None
        self.volume_label = None
        
        # State tracking
        self._is_playing = False
        self._controls_enabled = False
        self._current_volume = 1.0  # Default volume (100%)
        self._is_muted = False
        self._volume_before_mute = 1.0
        self._has_playlist = False
        self._has_multiple_tracks = False
        
        # Component references for highlighting
        self._playlist_widget = None
        self._player_controller = None
        
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        theme_manager = kwargs.pop('theme_manager', None)
        
        super().__init__(parent, translation_manager=translation_manager, **kwargs)
    
    def _create_layout(self):
        """Create horizontal layout for controls."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
    
    def _setup_ui(self):
        """Create the control buttons."""
        if not PYQT6_AVAILABLE:
            return
        
        # Previous track button (playlist navigation)
        self.prev_track_button = QPushButton()
        self.prev_track_button.setText("⏮")  # Track navigation
        self.prev_track_button.setToolTip(self.tr("player", "controls", "previous_track"))
        self.prev_track_button.setMinimumHeight(35)
        self.prev_track_button.setMaximumHeight(35)
        self.prev_track_button.setMinimumWidth(40)
        self.prev_track_button.setMaximumWidth(40)
        self.prev_track_button.setFont(self._get_button_font())
        self.prev_track_button.clicked.connect(self._on_prev_track_clicked)
        self.prev_track_button.setEnabled(False)  # Initially disabled
        self.main_layout.addWidget(self.prev_track_button)
        
        # Previous chapter button (within current track)
        self.prev_button = QPushButton()
        self.prev_button.setText("⏪")  # Chapter navigation
        self.prev_button.setToolTip(self.tr("player", "controls", "previous_chapter"))
        self.prev_button.setMinimumHeight(35)
        self.prev_button.setMaximumHeight(35)
        self.prev_button.setMinimumWidth(40)
        self.prev_button.setMaximumWidth(40)
        self.prev_button.setFont(self._get_button_font())
        self.prev_button.clicked.connect(self._on_prev_chapter_clicked)
        self.main_layout.addWidget(self.prev_button)
        
        # Play/pause button
        self.play_button = QPushButton()
        self._update_play_button_text()
        self.play_button.setMinimumHeight(35)
        self.play_button.setMaximumHeight(35)
        self.play_button.setMinimumWidth(45)
        self.play_button.setMaximumWidth(45)
        self.play_button.setFont(self._get_button_font())
        self.play_button.clicked.connect(self._on_play_toggle_clicked)
        # Remove primary property to fix blue styling
        self.main_layout.addWidget(self.play_button)
        
        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setText("⏹️")  # Alternative: ⏹, ◼️, ⬜
        self.stop_button.setToolTip(self.tr("player", "controls", "stop"))
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setMaximumHeight(35)
        self.stop_button.setMinimumWidth(40)
        self.stop_button.setMaximumWidth(40)
        self.stop_button.setFont(self._get_button_font())
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.main_layout.addWidget(self.stop_button)
        
        # Next chapter button (within current track)
        self.next_button = QPushButton()
        self.next_button.setText("⏩")  # Chapter navigation
        self.next_button.setToolTip(self.tr("player", "controls", "next_chapter"))
        self.next_button.setMinimumHeight(35)
        self.next_button.setMaximumHeight(35)
        self.next_button.setMinimumWidth(40)
        self.next_button.setMaximumWidth(40)
        self.next_button.setFont(self._get_button_font())
        self.next_button.clicked.connect(self._on_next_chapter_clicked)
        self.main_layout.addWidget(self.next_button)
        
        # Next track button (playlist navigation)
        self.next_track_button = QPushButton()
        self.next_track_button.setText("⏭")  # Track navigation
        self.next_track_button.setToolTip(self.tr("player", "controls", "next_track"))
        self.next_track_button.setMinimumHeight(35)
        self.next_track_button.setMaximumHeight(35)
        self.next_track_button.setMinimumWidth(40)
        self.next_track_button.setMaximumWidth(40)
        self.next_track_button.setFont(self._get_button_font())
        self.next_track_button.clicked.connect(self._on_next_track_clicked)
        self.next_track_button.setEnabled(False)  # Initially disabled
        self.main_layout.addWidget(self.next_track_button)        # Add some spacing before volume controls
        self.main_layout.addStretch()
        
        # Mute button
        self.mute_button = QPushButton()
        self._update_mute_button_text()
        self.mute_button.setMinimumHeight(35)
        self.mute_button.setMaximumHeight(35)
        self.mute_button.setMinimumWidth(40)
        self.mute_button.setMaximumWidth(40)
        self.mute_button.setFont(self._get_button_font())
        self.mute_button.clicked.connect(self._on_mute_clicked)
        self.main_layout.addWidget(self.mute_button)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(int(self._current_volume * 100))
        self.volume_slider.setMinimumWidth(80)
        self.volume_slider.setMaximumWidth(120)
        self.volume_slider.setMinimumHeight(35)
        self.volume_slider.setMaximumHeight(35)
        self.volume_slider.valueChanged.connect(self._on_volume_slider_changed)
        self.main_layout.addWidget(self.volume_slider)
        
        # Volume percentage label
        self.volume_label = QLabel("100%")
        self.volume_label.setMinimumWidth(30)
        self.volume_label.setMaximumWidth(30)
        self.volume_label.setFont(self._get_button_font())
        self.main_layout.addWidget(self.volume_label)
        
        # Set initial state
        self._update_button_states()
        
        logger.debug("Player controls UI created")
    
    def _setup_component(self):
        """Setup component-specific functionality."""
        # Subscribe to player state changes directly via domain events
        from ....events import get_event_bus
        from ....events.player_events import PlayerStateChangedEvent, PlayerFileLoadedEvent, PlayerVolumeChangedEvent
        
        self.event_bus = get_event_bus()
        logger.debug(f"Setting up domain event subscriptions on event_bus: {id(self.event_bus)}")
        
        # Create wrapper functions to avoid weak reference issues with bound methods
        def state_changed_handler(event):
            self._on_player_state_changed(event)
            
        def file_loaded_handler(event):
            self._on_file_loaded(event)
            
        def volume_changed_handler(event):
            self._on_volume_changed_event(event)
            
        # Store references to prevent garbage collection
        self._state_changed_handler = state_changed_handler
        self._file_loaded_handler = file_loaded_handler
        self._volume_changed_handler = volume_changed_handler
        
        self.event_bus.subscribe(PlayerStateChangedEvent, state_changed_handler)
        self.event_bus.subscribe(PlayerFileLoadedEvent, file_loaded_handler)
        self.event_bus.subscribe(PlayerVolumeChangedEvent, volume_changed_handler)
        logger.debug("Domain event subscriptions completed")
    
    def _get_button_font(self):
        """Get font for buttons."""
        if not PYQT6_AVAILABLE:
            return None
        
        font = QFont()
        font.setPointSize(12)  # Smaller size for compact layout
        font.setWeight(QFont.Weight.Medium)
        return font
    
    def _on_play_toggle_clicked(self):
        """Handle play/pause button click."""
        logger.debug("Play toggle clicked")
        self.play_toggle_clicked.emit()
    
    def _on_stop_clicked(self):
        """Handle stop button click."""
        logger.debug("Stop clicked")
        self.stop_clicked.emit()
    
    def _on_prev_chapter_clicked(self):
        """Handle previous chapter button click."""
        logger.debug("Previous chapter clicked")
        self.prev_chapter_clicked.emit()
    
    def _on_next_chapter_clicked(self):
        """Handle next chapter button click."""
        logger.debug("Next chapter clicked")  
        self.next_chapter_clicked.emit()
    
    def _on_prev_track_clicked(self):
        """Handle previous track button click."""
        logger.debug("Previous track clicked")
        self.prev_track_clicked.emit()
    
    def _on_next_track_clicked(self):
        """Handle next track button click."""
        logger.debug("Next track clicked")
        self.next_track_clicked.emit()
    
    def _on_mute_clicked(self):
        """Handle mute button click."""
        self._is_muted = not self._is_muted
        logger.debug(f"Mute clicked: muted={self._is_muted}")
        
        # Only emit the mute signal - let the player controller handle volume logic
        # The UI will be updated when we receive the volume change event back from the model
        self.mute_toggled.emit(self._is_muted)
    
    def _on_volume_slider_changed(self, value):
        """Handle volume slider change."""
        volume = value / 100.0  # Convert from 0-100 to 0.0-1.0
        self._current_volume = volume
        
        logger.debug(f"Volume slider changed: value={value}, volume={volume}")
        self._update_volume_label()
        
        # Only emit volume change - let the player model handle mute state consistency
        self.volume_changed.emit(self._current_volume)
    
    def _update_mute_button_text(self):
        """Update mute button icon and tooltip based on mute state."""
        if not self.mute_button:
            return
        
        if self._is_muted:
            icon = "🔇"
            tooltip = self.tr("player", "controls", "unmute")
        else:
            icon = "🔊"
            tooltip = self.tr("player", "controls", "mute")
        
        self.mute_button.setText(icon)
        self.mute_button.setToolTip(tooltip)
    
    def _update_volume_slider(self):
        """Update volume slider position."""
        if not self.volume_slider:
            return
        
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(int(self._current_volume * 100))
        self.volume_slider.blockSignals(False)
        self._update_volume_label()
    
    def _update_volume_label(self):
        """Update volume percentage label."""
        if not self.volume_label:
            return
        
        percentage = int(self._current_volume * 100)
        self.volume_label.setText(self.tr("player.controls.volume_label", volume=percentage))
    
    def _on_player_state_changed(self, event):
        """
        Handle player state change domain event.
        
        Args:
            event: PlayerStateChangedEvent
        """
        try:
            # Extract state from domain event
            state_str = event.state if hasattr(event, 'state') else str(event.new_state if hasattr(event, 'new_state') else "")
            state_str = str(state_str).lower()
            
            logger.debug(f"Player state changed: {state_str}")

            # Update internal state
            self._is_playing = (state_str == "playing")
            self._controls_enabled = (state_str not in ["loading", "error"])
            
            # Update playlist highlighting if available
            if hasattr(self, '_playlist_widget') and self._playlist_widget and hasattr(self, '_player_controller') and self._player_controller and self._player_controller.taf_player:
                try:
                    # Get current track index from playlist manager
                    if (self._player_controller.taf_player.playlist_manager and 
                        hasattr(self._player_controller.taf_player.playlist_manager, 'playlist')):
                        current_index = self._player_controller.taf_player.playlist_manager.playlist.current_index
                        logger.debug(f"PlayerControls: Updating playlist highlighting - state: {state_str}, current_index: {current_index}")
                        self._playlist_widget.update_player_state(state_str)
                    else:
                        logger.debug(f"PlayerControls: No playlist manager available for highlighting")
                except Exception as e:
                    logger.error(f"Error updating playlist highlighting from PlayerControls: {e}")

        except Exception as e:
            logger.error(f"Error handling PlayerStateChangedEvent in controls: {e}")
        
        # Update UI
        self._update_play_button_text()
        self._update_button_states()
    
    def _on_file_loaded(self, event):
        """
        Handle file loaded domain event.
        
        Args:
            event: PlayerFileLoadedEvent
        """
        try:
            logger.debug(f"File loaded in controls: {event.file_path}")
            # Enable controls when file is loaded
            self._controls_enabled = True
            self._update_button_states()
            
            # Update playlist highlighting if available
            if hasattr(self, '_playlist_widget') and self._playlist_widget and hasattr(self, '_player_controller') and self._player_controller and self._player_controller.taf_player:
                try:
                    # Get current track index from playlist manager
                    if (self._player_controller.taf_player.playlist_manager and 
                        hasattr(self._player_controller.taf_player.playlist_manager, 'playlist')):
                        current_index = self._player_controller.taf_player.playlist_manager.playlist.current_index
                        logger.debug(f"PlayerControls: File loaded - setting current track index: {current_index}")
                        self._playlist_widget.set_current_track(current_index)
                    else:
                        logger.debug(f"PlayerControls: No playlist manager available for setting current track")
                except Exception as e:
                    logger.error(f"Error setting current track from PlayerControls: {e}")
        except Exception as e:
            logger.error(f"Error handling PlayerFileLoadedEvent in controls: {e}")
    
    def _on_volume_changed_event(self, event):
        """
        Handle volume change domain event.
        
        Args:
            event: PlayerVolumeChangedEvent
        """
        try:
            logger.debug(f"Volume changed in controls: volume={event.volume}, muted={event.is_muted}")
            # Update internal state from domain event
            self._current_volume = event.volume
            self._is_muted = event.is_muted
            
            # Update UI components
            self._update_volume_slider()
            self._update_mute_button_text()
        except Exception as e:
            logger.error(f"Error handling PlayerVolumeChangedEvent in controls: {e}")
    
    def _update_play_button_text(self):
        """Update play button icon and tooltip based on state."""
        if not self.play_button:
            return
        
        if self._is_playing:
            icon = "⏸️"  # Alternative: ⏸, ◼️, ⸸
            tooltip = self.tr("player", "controls", "pause")
        else:
            icon = "▶️"  # Alternative: ▶, ⏵️, ➤
            tooltip = self.tr("player", "controls", "play")
        
        self.play_button.setText(icon)
        self.play_button.setToolTip(tooltip)
    
    def _update_button_states(self):
        """Update button enabled states."""
        if not PYQT6_AVAILABLE:
            return
        enabled = self._controls_enabled
        
        # Main playback controls
        if self.prev_button:
            self.prev_button.setEnabled(enabled)
        if self.play_button:
            self.play_button.setEnabled(enabled)
        if self.stop_button:
            self.stop_button.setEnabled(enabled and (self._is_playing or self._controls_enabled))
        if self.next_button:
            self.next_button.setEnabled(enabled)
        
        # Update track navigation buttons based on playlist state
        self._update_track_navigation_buttons()
        
        # Volume controls are always enabled (can adjust volume even when not playing)
        if self.mute_button:
            self.mute_button.setEnabled(True)
        if self.volume_slider:
            self.volume_slider.setEnabled(True)

    # Public methods for external control
    def set_volume(self, volume):
        """Set volume from external source (e.g., player controller)."""
        if not PYQT6_AVAILABLE:
            return
        
        volume = max(0.0, min(1.0, volume))
        self._current_volume = volume
        self._update_volume_slider()
        logger.debug(f"Volume updated externally: {volume}")
    
    def set_mute(self, is_muted):
        """Set mute state from external source (e.g., player controller)."""
        if not PYQT6_AVAILABLE:
            return
        
        self._is_muted = is_muted
        self._update_mute_button_text()
        logger.debug(f"Mute state updated externally: {is_muted}")
    
    def set_playing_state(self, is_playing):
        """Set playing state from external source."""
        if not PYQT6_AVAILABLE:
            return
        
        self._is_playing = is_playing
        self._update_play_button_text()
        logger.debug(f"Playing state updated externally: {is_playing}")
    
    def set_controls_enabled(self, enabled):
        """Enable/disable controls from external source."""
        if not PYQT6_AVAILABLE:
            return
        
        self._controls_enabled = enabled
        self._update_button_states()
        logger.debug(f"Controls enabled state updated externally: {enabled}")
    
    def set_player_controller(self, player_controller):
        """
        Set the player controller reference.
        
        Note: Actual communication happens through domain events via event bus.
        """
        logger.debug("Player controller reference set (using domain events for communication)")
    
    def set_playing_state(self, is_playing: bool):
        """
        Set the playing state manually.
        
        Args:
            is_playing: Whether currently playing
        """
        self._is_playing = is_playing
        self._update_play_button_text()
        self._update_button_states()
    
    def set_controls_enabled(self, enabled: bool):
        """
        Set whether controls are enabled.
        
        Args:
            enabled: Whether controls should be enabled
        """
        self._controls_enabled = enabled
        self._update_button_states()
    
    def get_is_playing(self) -> bool:
        """
        Get current playing state.
        
        Returns:
            True if currently playing
        """
        return self._is_playing
    
    def set_player_controller(self, player_controller):
        """Set or update the player controller reference."""
        self.player_controller = player_controller
        # Optionally reconnect signals here if needed
    
    def set_volume(self, volume: float):
        """
        Set volume level from external source.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self._current_volume = max(0.0, min(1.0, volume))
        self._is_muted = (self._current_volume == 0.0)
        self._update_volume_slider()
        self._update_mute_button_text()
    
    def get_volume(self) -> float:
        """
        Get current volume level.
        
        Returns:
            Current volume (0.0 to 1.0)
        """
        return self._current_volume
    
    def get_is_muted(self) -> bool:
        """
        Get current mute state.
        
        Returns:
            True if muted
        """
        return self._is_muted
    
    def set_playlist_widget(self, playlist_widget):
        """Set reference to playlist widget for highlighting."""
        self._playlist_widget = playlist_widget
        logger.debug(f"Player controls: playlist widget reference set: {type(playlist_widget)}")
    
    def set_taf_player(self, player_controller):
        """Set reference to player controller for accessing TAF player."""
        self._player_controller = player_controller
        logger.debug(f"Player controls: Player controller reference set: {type(player_controller)}")
    
    def set_playlist_mode(self, has_playlist, has_multiple_tracks=True):
        """Enable/disable track navigation based on playlist status."""
        if not PYQT6_AVAILABLE:
            return
        
        # Store playlist state
        self._has_playlist = has_playlist
        self._has_multiple_tracks = has_multiple_tracks
        
        # Update track navigation buttons
        self._update_track_navigation_buttons()
        
        logger.debug(f"Playlist mode set: has_playlist={has_playlist}, multiple_tracks={has_multiple_tracks}")
    
    def _update_track_navigation_buttons(self):
        """Update track navigation button states based on playlist status."""
        if not PYQT6_AVAILABLE:
            return
        
        # Enable track navigation only if we have a playlist with multiple tracks
        track_nav_enabled = self._has_playlist and self._has_multiple_tracks
        
        if self.prev_track_button:
            self.prev_track_button.setEnabled(track_nav_enabled)
        if self.next_track_button:
            self.next_track_button.setEnabled(track_nav_enabled)
        
        logger.debug(f"Track navigation buttons enabled: {track_nav_enabled}")
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        if not PYQT6_AVAILABLE:
            return
        
        # Update button tooltips
        if self.prev_track_button:
            self.prev_track_button.setToolTip(self.tr("player", "controls", "previous_track"))
        if self.prev_button:
            self.prev_button.setToolTip(self.tr("player", "controls", "previous_chapter"))
        if self.stop_button:
            self.stop_button.setToolTip(self.tr("player", "controls", "stop"))
        if self.next_button:
            self.next_button.setToolTip(self.tr("player", "controls", "next_chapter"))
        if self.next_track_button:
            self.next_track_button.setToolTip(self.tr("player", "controls", "next_track"))
        
        # Update play button text and tooltip
        self._update_play_button_text()
        
        # Update mute button text and tooltip
        self._update_mute_button_text()
        
        # Update volume label
        if self.volume_label and self.volume_slider:
            percentage = self.volume_slider.value()
            self.volume_label.setText(self.tr("player", "controls", "volume_label", volume=percentage))
        
        logger.debug("Player controls retranslated")
    
    def _cleanup_component(self):
        """Component-specific cleanup."""
        logger.debug("Cleaning up player controls")