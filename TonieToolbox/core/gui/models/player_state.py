"""
Player state model for the GUI.
"""
from enum import Enum
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ...analysis.models import TafAnalysisResult

from ...events import (
    get_event_bus,
    PlayerStateChangedEvent,
    PlayerFileLoadedEvent,
    PlayerPositionChangedEvent,
    PlayerVolumeChangedEvent,
    PlayerDurationChangedEvent
)
from ...utils import get_logger

logger = get_logger(__name__)


class PlayerState(Enum):
    """Player state enumeration.
    
    Represents the current playback state of the TAF audio player. The player
    follows a finite state machine with well-defined transitions between states.
    
    State Transition Diagram::
    
        STOPPED ──load_file()──> LOADING
           ↑                        ↓
           │                    [success]
           │                        ↓
           └────stop()──────── PLAYING ←──resume()── PAUSED
                                  ↓                      ↑
                                pause()──────────────────┘
                                  ↓
                              [error]
                                  ↓
                               ERROR
    
    Valid State Transitions:
        - STOPPED → LOADING: When load_file() is called
        - LOADING → PLAYING: When file loads successfully and playback starts
        - LOADING → ERROR: When file loading fails
        - PLAYING → PAUSED: When pause() is called
        - PLAYING → STOPPED: When stop() is called or playback ends
        - PLAYING → ERROR: When playback error occurs
        - PAUSED → PLAYING: When resume() is called
        - PAUSED → STOPPED: When stop() is called
        - ERROR → STOPPED: When clearing error state
    
    Event Flow:
        Each state transition publishes a PlayerStateChangedEvent on the event bus,
        allowing GUI components to react to state changes (e.g., update play/pause
        button icons, enable/disable controls).
    
    Example:
        Handling state transitions in GUI::
        
            from TonieToolbox.core.gui.models import PlayerState, PlayerModel
            from TonieToolbox.core.events import get_event_bus
            
            player_model = PlayerModel()
            
            def on_state_changed(event):
                if event.state == PlayerState.PLAYING.value:
                    play_button.setText("⏸ Pause")
                    play_button.setEnabled(True)
                elif event.state == PlayerState.PAUSED.value:
                    play_button.setText("▶ Play")
                    play_button.setEnabled(True)
                elif event.state == PlayerState.STOPPED.value:
                    play_button.setText("▶ Play")
                    play_button.setEnabled(False)
                elif event.state == PlayerState.ERROR.value:
                    show_error_dialog(event.error_message)
            
            event_bus = get_event_bus()
            event_bus.subscribe('player_state_changed', on_state_changed)
    
    Attributes:
        STOPPED: No file loaded or playback stopped
        PLAYING: Audio is currently playing
        PAUSED: Playback paused, can be resumed
        LOADING: File is being loaded
        ERROR: An error occurred during playback
    """
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"
    ERROR = "error"


class PlayerModel:
    """
    Simple player model that integrates with the core event system.
    
    This model maintains the player state and publishes events whenever state
    changes occur. It acts as the single source of truth for player state in
    the GUI application, following the Model-View-Controller pattern.
    
    State Management:
        The model uses a finite state machine (see PlayerState documentation)
        to ensure valid state transitions. Each state change publishes events
        that GUI components can subscribe to for reactive updates.
    
    Event Publishing:
        All property changes publish corresponding events:
        - state → PlayerStateChangedEvent
        - position → PlayerPositionChangedEvent
        - duration → PlayerDurationChangedEvent
        - volume → PlayerVolumeChangedEvent
        - file_path → PlayerFileLoadedEvent
    
    Example:
        Initialize and use player model in GUI::
        
            from TonieToolbox.core.gui.models import PlayerModel, PlayerState
            from TonieToolbox.core.events import get_event_bus
            from pathlib import Path
            
            # Create player model
            player_model = PlayerModel()
            
            # Subscribe to state changes
            event_bus = get_event_bus()
            event_bus.subscribe('player_state_changed', lambda e: print(f"State: {e.state}"))
            event_bus.subscribe('player_position_changed', lambda e: print(f"Position: {e.position}s"))
            
            # Load and play file
            player_model.load_file(Path('audio.taf'), analysis_result)
            player_model.state = PlayerState.PLAYING
            # Output: State: playing
            
            # Update position (e.g., from playback thread)
            player_model.position = 10.5
            # Output: Position: 10.5s
        
        Synchronize GUI controls with model::
        
            def update_ui_from_state(event):
                if event.state == 'playing':
                    play_button.setIcon(pause_icon)
                    progress_slider.setEnabled(True)
                elif event.state == 'paused':
                    play_button.setIcon(play_icon)
                elif event.state == 'stopped':
                    play_button.setIcon(play_icon)
                    progress_slider.setValue(0)
                    progress_slider.setEnabled(False)
            
            event_bus.subscribe('player_state_changed', update_ui_from_state)
        
        Handle volume changes::
        
            def on_volume_changed(event):
                if event.is_muted:
                    volume_slider.setEnabled(False)
                    volume_icon.setIcon(muted_icon)
                else:
                    volume_slider.setEnabled(True)
                    volume_slider.setValue(int(event.volume * 100))
                    volume_icon.setIcon(speaker_icon)
            
            event_bus.subscribe('player_volume_changed', on_volume_changed)
            
            # Mute/unmute
            player_model.is_muted = True
            # UI updates automatically via event
    """
    
    def __init__(self):
        """Initialize the player model."""
        self.event_bus = get_event_bus()
        
        # State properties
        self._state = PlayerState.STOPPED
        self._position = 0.0
        self._duration = 0.0
        self._volume = 0.5
        self._is_muted = False
        self._file_path: Optional[Path] = None
        self._analysis_result: Optional['TafAnalysisResult'] = None
        self._chapters: List[Dict[str, Any]] = []
        self._current_chapter = 0
        
        logger.debug("PlayerModel initialized")
    
    # Properties with event publishing
    @property
    def state(self) -> PlayerState:
        return self._state
    
    @state.setter
    def state(self, value: PlayerState):
        """Set player state and publish state change event.
        
        This setter implements the state transition logic and publishes a
        PlayerStateChangedEvent whenever the state changes. All state transitions
        should go through this setter to ensure proper event notification.
        
        Args:
            value: New player state
        
        Events:
            Publishes PlayerStateChangedEvent with:
            - source: "player_model"
            - state: New state value (str)
            - previous_state: Previous state value (str)
        
        Example:
            Transition from STOPPED to PLAYING::
            
                player_model.state = PlayerState.STOPPED
                # ... load file ...
                player_model.state = PlayerState.LOADING
                # ... file loads successfully ...
                player_model.state = PlayerState.PLAYING
                # Event published: state='playing', previous_state='loading'
            
            Handle pause/resume::
            
                # User clicks pause
                if player_model.state == PlayerState.PLAYING:
                    player_model.state = PlayerState.PAUSED
                    # Event: state='paused', previous_state='playing'
                
                # User clicks play/resume
                if player_model.state == PlayerState.PAUSED:
                    player_model.state = PlayerState.PLAYING
                    # Event: state='playing', previous_state='paused'
        """
        old_state = self._state
        self._state = value
        # Publish state change event
        event = PlayerStateChangedEvent(
            source="player_model",
            state=value.value,
            previous_state=old_state.value if old_state else None
        )
        self.event_bus.publish(event)
        logger.debug(f"State changed: {old_state} -> {value}")
    
    @property
    def position(self) -> float:
        return self._position
    
    @position.setter
    def position(self, value: float):
        self._position = value
        # Publish position change event
        event = PlayerPositionChangedEvent(
            source="player_model",
            position=value,
            duration=self._duration
        )
        self.event_bus.publish(event)
    
    @property
    def duration(self) -> float:
        return self._duration
    
    @duration.setter
    def duration(self, value: float):
        self._duration = value
        # Publish duration change event
        event = PlayerDurationChangedEvent(
            source="player_model",
            duration=value
        )
        self.event_bus.publish(event)
    
    @property
    def volume(self) -> float:
        return self._volume
    
    @volume.setter
    def volume(self, value: float):
        self._volume = max(0.0, min(1.0, value))  # Clamp to 0-1
        # Publish volume change event
        event = PlayerVolumeChangedEvent(
            source="player_model",
            volume=self._volume,
            is_muted=self._is_muted
        )
        self.event_bus.publish(event)
    
    @property
    def is_muted(self) -> bool:
        return self._is_muted
    
    @is_muted.setter
    def is_muted(self, value: bool):
        self._is_muted = value
        # Publish volume change event (mute affects volume)
        event = PlayerVolumeChangedEvent(
            source="player_model",
            volume=self._volume,
            is_muted=value
        )
        self.event_bus.publish(event)
    
    @property
    def file_path(self) -> Optional[Path]:
        return self._file_path
    
    @property
    def analysis_result(self) -> Optional['TafAnalysisResult']:
        return self._analysis_result
    
    @property
    def chapters(self) -> List[Dict[str, Any]]:
        return self._chapters
    
    @property
    def current_chapter(self) -> int:
        return self._current_chapter
    
    def load_file(self, file_path: Path, analysis_result: 'TafAnalysisResult'):
        """Load a file into the player model.
        
        Loads a TAF file and its analysis result into the player, extracting chapter
        information and initializing playback state. This triggers a state transition
        from STOPPED → LOADING → (ready for PLAYING).
        
        Args:
            file_path: Path to the TAF file
            analysis_result: Analysis result containing file metadata and chapters
        
        Events:
            Publishes PlayerFileLoadedEvent with:
            - source: "player_model"
            - file_path: Path to loaded file
            - analysis_result: TafAnalysisResult domain object
        
        State Transitions:
            Typical flow:
            1. STOPPED → call load_file() → LOADING
            2. File loading succeeds → ready for PLAYING state
            3. Set state to PLAYING to begin playback
        
        Example:
            Load file and start playback::
            
                from TonieToolbox.core.analysis.models import TafAnalysisResult
                from pathlib import Path
                
                # Analyze TAF file first
                analysis_result = analyze_taf_file(Path('audio.taf'))
                
                # Load into player
                player_model.load_file(Path('audio.taf'), analysis_result)
                # PlayerFileLoadedEvent published
                # Chapters populated: [{'id': 1, 'title': 'Chapter 1', ...}, ...]
                # Duration set: 1234.5 seconds
                # Position reset: 0.0
                
                # Start playback
                player_model.state = PlayerState.PLAYING
            
            Access loaded file information::
            
                def on_file_loaded(event):
                    print(f"Loaded: {event.file_path}")
                    print(f"Duration: {event.analysis_result.audio_analysis.duration_seconds}s")
                    print(f"Chapters: {len(event.analysis_result.tonie_header.chapters)}")
                
                event_bus.subscribe('player_file_loaded', on_file_loaded)
                player_model.load_file(file_path, analysis_result)
        """
        from ...analysis.models import TafAnalysisResult
        
        self._file_path = file_path
        self._analysis_result = analysis_result
        self._chapters = [
            {
                'id': chapter.id,
                'title': chapter.title,
                'duration': chapter.seconds,
                'start': sum(c.seconds for c in analysis_result.tonie_header.chapters[:i])  # Calculate start time
            }
            for i, chapter in enumerate(analysis_result.tonie_header.chapters)
        ]
        self._current_chapter = 0
        
        # Reset playback state
        self._position = 0.0
        self._duration = analysis_result.audio_analysis.duration_seconds
        
        # Publish file loaded event with domain object
        event = PlayerFileLoadedEvent(
            source="player_model",
            file_path=file_path,
            analysis_result=analysis_result
        )
        logger.info(f"Publishing PlayerFileLoadedEvent on event_bus {id(self.event_bus)}: file_path={file_path}, analysis_result={type(analysis_result).__name__}")
        self.event_bus.publish(event)
        
        logger.info(f"File loaded: {file_path}")