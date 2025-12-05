#!/usr/bin/env python3
"""
Event utilities for Qt GUI.
"""

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None

from ...events import get_event_bus
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class QtEventBridge(QObject):
    """Event bridge for Qt GUI components.
    
    Bridges between the domain event bus and Qt signals, allowing GUI components
    to receive domain events as Qt signals. This enables reactive UI updates
    while maintaining separation between domain logic and presentation layer.
    
    Architecture:
        Domain Events (event bus) → QtEventBridge → Qt Signals → GUI Components
    
    Signals:
        player_state_changed(str): Emitted when player state changes
        file_loaded(object): Emitted when file is loaded (dict with file info)
        position_changed(float): Emitted when playback position changes
        volume_changed(float): Emitted when volume changes
        duration_changed(float): Emitted when duration is set
        error_occurred(str): Emitted on player errors
        chapter_changed(int): Emitted when current chapter changes
    
    Example:
        Connect GUI components to domain events::
        
            from TonieToolbox.core.gui.utils.events import QtEventBridge
            from PyQt6.QtWidgets import QPushButton, QLabel
            
            # Create event bridge
            event_bridge = QtEventBridge()
            
            # Connect Qt signals to GUI components
            event_bridge.player_state_changed.connect(
                lambda state: play_button.setText("⏸" if state == "playing" else "▶")
            )
            
            event_bridge.position_changed.connect(
                lambda pos: position_slider.setValue(int(pos))
            )
            
            event_bridge.duration_changed.connect(
                lambda dur: duration_label.setText(format_time(dur))
            )
            
            event_bridge.error_occurred.connect(
                lambda msg: show_error_dialog(msg)
            )
        
        Update UI based on file loading::
        
            def on_file_loaded(file_data):
                file_path = file_data['file_path']
                file_info = file_data['file_info']
                
                # Update UI
                title_label.setText(file_info.get('title', 'Unknown'))
                artist_label.setText(file_info.get('artist', 'Unknown'))
                duration_label.setText(format_duration(file_info.get('duration')))
                
                # Enable playback controls
                play_button.setEnabled(True)
                position_slider.setEnabled(True)
            
            event_bridge.file_loaded.connect(on_file_loaded)
        
        React to state changes::
        
            def update_controls(state):
                if state == "playing":
                    play_button.setIcon(pause_icon)
                    play_button.setEnabled(True)
                elif state == "paused":
                    play_button.setIcon(play_icon)
                    play_button.setEnabled(True)
                elif state == "stopped":
                    play_button.setIcon(play_icon)
                    play_button.setEnabled(False)
                    position_slider.setValue(0)
                elif state == "error":
                    play_button.setEnabled(False)
                    status_label.setText("Playback error")
            
            event_bridge.player_state_changed.connect(update_controls)
    """
    
    # Qt signals that GUI components expect
    player_state_changed = pyqtSignal(str)
    file_loaded = pyqtSignal(object)  # Changed to object to pass dict with file info
    position_changed = pyqtSignal(float)
    volume_changed = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    chapter_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.event_bus = get_event_bus()
        self._subscribe_to_events()
        logger.debug("Qt event bridge initialized")
    
    def _subscribe_to_events(self):
        """Subscribe to domain events and emit Qt signals."""
        from ...events.player_events import (
            PlayerStateChangedEvent,
            PlayerFileLoadedEvent,
            PlayerPositionChangedEvent,
            PlayerVolumeChangedEvent,
            PlayerDurationChangedEvent,
            PlayerErrorOccurredEvent,
            PlayerChapterChangedEvent
        )
        
        logger.info(f"QtEventBridge subscribing to events on event_bus: {id(self.event_bus)}")
        self.event_bus.subscribe(PlayerStateChangedEvent, self._on_state_changed)
        self.event_bus.subscribe(PlayerFileLoadedEvent, self._on_file_loaded)
        self.event_bus.subscribe(PlayerPositionChangedEvent, self._on_position_changed)
        self.event_bus.subscribe(PlayerVolumeChangedEvent, self._on_volume_changed)
        self.event_bus.subscribe(PlayerDurationChangedEvent, self._on_duration_changed)
        self.event_bus.subscribe(PlayerErrorOccurredEvent, self._on_error_occurred)
        self.event_bus.subscribe(PlayerChapterChangedEvent, self._on_chapter_changed)
        logger.info("QtEventBridge event subscriptions completed")
    
    def _on_state_changed(self, event):
        """Handle player state changed event."""
        self.player_state_changed.emit(event.new_state.value if hasattr(event.new_state, 'value') else str(event.new_state))
    
    def _on_file_loaded(self, event):
        """Handle file loaded event."""
        logger.info(f"QtEventBridge received PlayerFileLoadedEvent: {event.file_path}")
        # Emit dict with file path and file info
        file_data = {
            'file_path': str(event.file_path),
            'file_info': event.file_info
        }
        logger.info(f"QtEventBridge emitting file_loaded signal with data: {list(file_data.keys())}")
        self.file_loaded.emit(file_data)
    
    def _on_position_changed(self, event):
        """Handle position changed event."""
        self.position_changed.emit(event.position)
    
    def _on_volume_changed(self, event):
        """Handle volume changed event."""
        self.volume_changed.emit(event.volume)
    
    def _on_duration_changed(self, event):
        """Handle duration changed event."""
        self.duration_changed.emit(event.duration)
    
    def _on_error_occurred(self, event):
        """Handle error event."""
        self.error_occurred.emit(event.error_message)
    
    def _on_chapter_changed(self, event):
        """Handle chapter changed event."""
        self.chapter_changed.emit(event.chapter_index)
    
    def cleanup(self):
        """Clean up the event bridge."""
        logger.debug("Qt event bridge cleanup completed")
