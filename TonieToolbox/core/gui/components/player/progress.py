#!/usr/bin/env python3
"""
Player progress component for PyQt6 GUI.
Handles progress bar and seeking functionality.
"""
try:
    from PyQt6.QtWidgets import QSlider, QLabel, QVBoxLayout, QHBoxLayout
    from PyQt6.QtCore import pyqtSignal, Qt
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QSlider = object
    QLabel = object
    QVBoxLayout = object
    QHBoxLayout = object
    pyqtSignal = lambda: None
    Qt = object
    QFont = object

import time

from ..base.component import QtBaseFrame
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class PlayerProgress(QtBaseFrame):
    """
    Player progress bar and time display component.
    Handles seeking and position display.
    """
    
    # Signals
    seek_requested = pyqtSignal(float)  # position
    
    def __init__(self, parent=None, **kwargs):
        """
        Initialize player progress.
        
        Args:
            parent: Parent widget
            **kwargs: Additional configuration
        """
        # UI components
        self.progress_slider = None
        self.position_label = None
        self.duration_label = None
        
        # State
        self._duration = 0.0
        self._position = 0.0
        self._is_seeking = False
        
        # Throttling for position updates
        self._last_position_update = 0.0
        self._update_throttle_ms = 50  # Only update UI every 50ms (20fps)
        
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        theme_manager = kwargs.pop('theme_manager', None)
        
        super().__init__(parent, translation_manager=translation_manager, **kwargs)
    
    def _setup_ui(self):
        """Create the progress UI."""
        if not PYQT6_AVAILABLE:
            return
        
        # Time labels layout
        time_layout = QHBoxLayout()
        
        # Position label
        self.position_label = QLabel("0:00")
        self.position_label.setFont(self._get_label_font())
        time_layout.addWidget(self.position_label)
        
        time_layout.addStretch()
        
        # Duration label
        self.duration_label = QLabel("0:00")
        self.duration_label.setFont(self._get_label_font())
        time_layout.addWidget(self.duration_label)
        
        self.main_layout.addLayout(time_layout)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)  # Use 1000 for smoother progress
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        
        # Connect slider signals
        self.progress_slider.sliderPressed.connect(self._on_seek_start)
        self.progress_slider.sliderReleased.connect(self._on_seek_end)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.valueChanged.connect(self._on_slider_value_changed)
        
        self.main_layout.addWidget(self.progress_slider)
        
        logger.debug("Player progress UI created")
    
    def _setup_component(self):
        """Setup component-specific functionality."""
        # Subscribe to domain events directly
        from ....events import get_event_bus
        from ....events.player_events import PlayerStateChangedEvent, PlayerFileLoadedEvent, PlayerPositionChangedEvent, PlayerDurationChangedEvent
        
        self.event_bus = get_event_bus()
        logger.debug(f"Setting up domain event subscriptions on event_bus: {id(self.event_bus)}")
        
        # Create wrapper functions to avoid weak reference issues with bound methods
        def position_changed_handler(event):
            self._on_position_changed(event.position)
            
        def duration_changed_handler(event):
            logger.debug(f"PROGRESS: Received duration update: {event.duration}")
            self._on_duration_changed(event.duration)
            
        def state_changed_handler(event):
            self._on_state_changed(event.state)
            
        def file_loaded_handler(event):
            # When file is loaded, reset position and get duration from file info
            self._position = 0.0
            self._update_progress_slider()
            self._update_position_label(self._position)
            logger.debug("Progress reset to 0 due to file loaded")
            
            if hasattr(event, 'file_info') and event.file_info:
                duration = event.file_info.get('duration', 0.0)
                self._on_duration_changed(duration)
            
        # Store references to prevent garbage collection
        self._position_changed_handler = position_changed_handler
        self._duration_changed_handler = duration_changed_handler
        self._state_changed_handler = state_changed_handler
        self._file_loaded_handler = file_loaded_handler
        
        self.event_bus.subscribe(PlayerPositionChangedEvent, position_changed_handler)
        self.event_bus.subscribe(PlayerDurationChangedEvent, duration_changed_handler)
        self.event_bus.subscribe(PlayerStateChangedEvent, state_changed_handler)
        self.event_bus.subscribe(PlayerFileLoadedEvent, file_loaded_handler)
        logger.debug("Domain event subscriptions completed")
    
    def _get_label_font(self):
        """Get font for time labels."""
        if not PYQT6_AVAILABLE:
            return None
        
        font = QFont()
        font.setPointSize(10)
        font.setFamily("monospace")  # Monospace for consistent width
        return font
    
    def _on_seek_start(self):
        """Handle seek start (slider pressed)."""
        self._is_seeking = True
        logger.debug("Seek started")
    
    def _on_seek_end(self):
        """Handle seek end (slider released)."""
        if self._is_seeking:
            # Calculate position from slider value
            slider_value = self.progress_slider.value()
            position = (slider_value / 1000.0) * self._duration
            
            logger.info(f"PROGRESS: Seeking to position: {position}s (slider: {slider_value}, duration: {self._duration})")
            self.seek_requested.emit(position)
        
        self._is_seeking = False
    
    def _on_slider_moved(self, value):
        """Handle slider being dragged by user."""
        if self._is_seeking and self._duration > 0:
            # Update position display during seeking
            position = (value / 1000.0) * self._duration
            self._update_position_label(position)
    
    def _on_slider_value_changed(self, value):
        """Handle slider value change (programmatic or user)."""
        # Only handle if not already handled by sliderMoved
        if not self._is_seeking:
            return
    
    def _on_position_changed(self, position: float):
        """
        Handle position change from player.
        
        Args:
            position: New position in seconds
        """
        try:
            # Domain event may pass a dict with keys 'position' and 'duration'
            pos = position
            if isinstance(position, dict):
                pos = position.get('position') or position.get('pos') or 0.0

            if not self._is_seeking:  # Don't update during manual seeking
                # Throttle updates to prevent flickering, except for position 0.0 (stop/reset)
                current_time = time.time() * 1000  # Convert to milliseconds
                should_update_ui = (
                    (current_time - self._last_position_update) >= self._update_throttle_ms
                    or float(pos) == 0.0  # Always update immediately when position is reset to 0
                )
                
                if should_update_ui:
                    self._position = float(pos)
                    self._update_progress_slider()
                    self._update_position_label(self._position)
                    self._last_position_update = current_time
                else:
                    # Just update the position value without UI update
                    self._position = float(pos)
        except Exception as e:
            logger.error(f"Error handling position_changed payload: {e}")
    
    def _on_duration_changed(self, duration: float):
        """
        Handle duration change from player.
        
        Args:
            duration: New duration in seconds
        """
        dur = duration
        if isinstance(duration, dict):
            dur = duration.get('duration') or duration.get('total_duration') or dur

        try:
            self._duration = float(dur)
        except Exception:
            self._duration = 0.0

        self._update_duration_label()

        # Enable slider if we have a valid duration
        if self.progress_slider:
            self.progress_slider.setEnabled(self._duration > 0)
    
    def _on_state_changed(self, state: str):
        """
        Handle player state changes.
        
        Args:
            state: New player state
        """
        try:
            state_str = state
            if isinstance(state, dict):
                state_str = state.get('state') or state.get('new_state') or str(state)
            if state_str is None:
                state_str = ""
            state_str = str(state_str).lower()

            # Reset progress when stopped
            if state_str == "stopped":
                self._position = 0.0
                self._update_progress_slider()
                self._update_position_label(self._position)
                logger.debug("Progress reset to 0 due to stopped state")

            # Enable/disable slider based on state
            if self.progress_slider:
                enabled = state_str not in ["loading", "error"] and self._duration > 0
                self.progress_slider.setEnabled(enabled)
        except Exception as e:
            logger.error(f"Error handling state_changed payload in progress: {e}")
    
    def _update_progress_slider(self):
        """Update progress slider position."""
        if not self.progress_slider or self._duration <= 0:
            return
        
        # Calculate slider value (0-1000)
        progress = min(self._position / self._duration, 1.0)
        slider_value = int(progress * 1000)
        
        # Block signals to prevent feedback loop
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(slider_value)
        self.progress_slider.blockSignals(False)
    
    def _update_position_label(self, position: float = None):
        """Update position label."""
        if not self.position_label:
            return
        
        pos = position if position is not None else self._position
        time_str = self._format_time(pos)
        self.position_label.setText(time_str)
    
    def _update_duration_label(self):
        """Update duration label."""
        if not self.duration_label:
            return
        
        time_str = self._format_time(self._duration)
        self.duration_label.setText(time_str)
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds to MM:SS format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds < 0:
            seconds = 0
        
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def set_position(self, position: float):
        """
        Set position manually.
        
        Args:
            position: Position in seconds
        """
        self._position = position
        if not self._is_seeking:
            self._update_progress_slider()
            self._update_position_label()
    
    def set_duration(self, duration: float):
        """
        Set duration manually.
        
        Args:
            duration: Duration in seconds
        """
        self._duration = duration
        self._update_duration_label()
        
        if self.progress_slider:
            self.progress_slider.setEnabled(duration > 0)
    
    def get_position(self) -> float:
        """
        Get current position.
        
        Returns:
            Current position in seconds
        """
        return self._position
    
    def get_duration(self) -> float:
        """
        Get current duration.
        
        Returns:
            Current duration in seconds
        """
        return self._duration
    
    def set_player_controller(self, player_controller):
        """Set or update the player controller reference."""
        self.player_controller = player_controller
        # Optionally reconnect signals here if needed
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        # Player progress doesn't have translatable text (just time labels)
        # But we keep this method for consistency
        pass
    
    def _cleanup_component(self):
        """Component-specific cleanup."""
        logger.debug("Cleaning up player progress")