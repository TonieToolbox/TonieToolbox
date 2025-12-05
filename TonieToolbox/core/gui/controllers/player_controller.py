#!/usr/bin/env python3
"""
Qt-specific player controller for the GUI.
"""
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None
    QTimer = object

from ..models.player_state import PlayerModel, PlayerState
from ...events import (
    get_event_bus,
    PlayerStateChangedEvent,
    PlayerFileLoadedEvent,
    PlayerPositionChangedEvent,
    PlayerVolumeChangedEvent,
    PlayerDurationChangedEvent,
    PlayerChapterChangedEvent,
    PlayerErrorOccurredEvent
)
from ...media.player.engine import TAFPlayer, TAFPlayerError
from ...media.playlist.models import RepeatMode
from ...analysis import get_header_info
from ...utils import get_logger

logger = get_logger(__name__)

# Update interval for position timer (milliseconds) - 100ms = 10 updates per second
POSITION_UPDATE_INTERVAL_MS = 100


class QtPlayerController(QObject):
    """Qt player controller that bridges the player model with Qt signals."""
    
    # Qt signals
    state_changed = pyqtSignal(str)
    file_loaded = pyqtSignal(str)
    position_changed = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    volume_changed = pyqtSignal(float)
    mute_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    chapter_changed = pyqtSignal(int)
    
    def __init__(self, player_model=None, thread_manager=None):
        """Initialize the Qt player controller."""
        super().__init__()
        
        self.model = player_model or PlayerModel()
        self.event_bus = get_event_bus()
        self.taf_player = None
        
        # GUI component references
        self.playlist_widget = None
        self.player_controls = None
        self.playlist_controls = None
        self.playlist_info_panel = None
        self.chapter_widget = None
        self.main_window = None
        
        # Mute state management
        self._volume_before_mute = 1.0
        
        # Position update timer
        self._position_timer = None
        if PYQT6_AVAILABLE:
            self._position_timer = QTimer()
            self._position_timer.timeout.connect(self._update_position)
            self._position_timer.setInterval(POSITION_UPDATE_INTERVAL_MS)
            logger.debug("Position timer created")
        
        self._setup_event_subscriptions()
        logger.info("Qt player controller initialized")
    
    def _setup_event_subscriptions(self):
        """Subscribe to domain events from the event bus."""
        self.event_bus.subscribe(PlayerStateChangedEvent, self._on_state_changed)
        self.event_bus.subscribe(PlayerFileLoadedEvent, self._on_file_loaded_unique)
        self.event_bus.subscribe(PlayerPositionChangedEvent, self._on_position_changed)
        self.event_bus.subscribe(PlayerVolumeChangedEvent, self._on_volume_changed)
        self.event_bus.subscribe(PlayerDurationChangedEvent, self._on_duration_changed)
        self.event_bus.subscribe(PlayerChapterChangedEvent, self._on_chapter_changed)
        self.event_bus.subscribe(PlayerErrorOccurredEvent, self._on_error_occurred)
        logger.debug("Event subscriptions completed")
    
    def _on_state_changed(self, event: PlayerStateChangedEvent) -> None:
        """Handle player state change events from the event bus.
        
        Updates UI components with new state and manages widget highlighting.
        
        Args:
            event: State change event containing new player state
        """
        # Map player state to string for UI components
        state_str = str(event.state).split('.')[-1].lower()
        
        # Emit Qt signal with state string for status bar
        self.state_changed.emit(state_str)
        logger.debug(f"Emitted state_changed signal: {state_str}")
        
        # Update playlist widget highlighting with player state
        if self.playlist_widget and hasattr(self.playlist_widget, 'update_player_state'):
            self.playlist_widget.update_player_state(state_str)
            
        # Update chapter widget highlighting with player state
        if self.chapter_widget and hasattr(self.chapter_widget, 'update_player_state'):
            self.chapter_widget.update_player_state(state_str)
        
        # Also update current track highlighting for playlist (important for auto-advance)
        if (self.taf_player and hasattr(self.taf_player, 'playlist_manager') and 
            self.taf_player.playlist_manager and self.playlist_widget):
            self._update_current_track_highlighting()
            logger.debug(f"Updated playlist highlighting after state change: {state_str}")
    
    def _on_file_loaded_unique(self, event: PlayerFileLoadedEvent) -> None:
        """Handle file loaded events from the event bus.
        
        Updates playlist selection, loads chapter information, and manages UI state
        when a new file is loaded.
        
        Args:
            event: File loaded event containing file path and analysis results
        """
        self.file_loaded.emit(event.file_path)
        
        # Update playlist widget selection if we're in playlist mode
        if (self.taf_player and hasattr(self.taf_player, 'playlist_manager') and 
            self.taf_player.playlist_manager and self.playlist_widget):
            
            current_index = self.taf_player.playlist_manager.playlist.current_index
            if current_index >= 0:
                # Determine current state from player
                state_str = "stopped"
                if self.taf_player.is_playing:
                    state_str = "playing" if not self.taf_player.is_paused else "paused"
                
                # Update highlighting with current track and state
                logger.debug(f"Updating playlist highlighting: track {current_index}, state {state_str}")
                if hasattr(self.playlist_widget, 'set_current_track'):
                    self.playlist_widget.set_current_track(current_index, state_str)
                elif hasattr(self.playlist_widget, 'set_current_selection'):
                    current_item = self.taf_player.playlist_manager.current_item
                    if current_item:
                        self.playlist_widget.set_current_selection(current_item)
            
            # Update playlist info panel to show current track
            self._update_playlist_info_panel()
            logger.debug("Updated playlist info panel after track change")
            
            # Update playlist controls status to show current track position
            self._update_playlist_controls_status()
        
        # Update chapter widget with chapter information from loaded file
        if self.chapter_widget and event.analysis_result and hasattr(self.chapter_widget, 'load_chapters'):
            # Convert domain objects to format expected by chapter widget
            chapters = [
                {
                    'index': i,
                    'title': chapter.title,
                    'duration': chapter.seconds,
                    'start': sum(c.seconds for c in event.analysis_result.tonie_header.chapters[:i])
                }
                for i, chapter in enumerate(event.analysis_result.tonie_header.chapters)
            ]
            self.chapter_widget.load_chapters(chapters)
            logger.debug(f"Loaded {len(chapters)} chapters into chapter widget")
            
            # Set initial chapter highlighting with current player state (only if chapters exist)
            if len(chapters) > 0 and self.taf_player and hasattr(self.chapter_widget, 'set_current_chapter'):
                state_str = "stopped"
                if self.taf_player.is_playing:
                    state_str = "playing" if not self.taf_player.is_paused else "paused"
                
                # Highlight first chapter (index 0) with current state
                self.chapter_widget.set_current_chapter(0, state_str)
                logger.debug(f"Set initial chapter highlighting: chapter 0, state {state_str}")
    
    def _on_position_changed(self, event: PlayerPositionChangedEvent) -> None:
        """Handle player position change events from the event bus.
        
        Updates UI with new position and manages chapter highlighting based on playback position.
        
        Args:
            event: Position change event containing new position in seconds
        """
        self.position_changed.emit(event.position)
        
        # Update chapter highlighting based on current position
        if self.chapter_widget and hasattr(self.chapter_widget, 'get_chapter_at_position'):
            current_chapter = self.chapter_widget.get_chapter_at_position(event.position)
            if current_chapter >= 0 and current_chapter != self.chapter_widget.get_current_chapter_index():
                # Get current player state
                player_state = "stopped"
                if self.taf_player and hasattr(self.taf_player, 'player_state'):
                    state_enum = self.taf_player.player_state
                    player_state = str(state_enum).split('.')[-1].lower()
                
                # Update chapter highlighting
                self.chapter_widget.set_current_chapter(current_chapter, player_state)
    
    def _on_volume_changed(self, event: PlayerVolumeChangedEvent) -> None:
        """Handle volume change events from the event bus.
        
        Emits Qt signals to update UI components with new volume and mute state.
        
        Args:
            event: Volume change event containing new volume level and mute state
        """
        self.volume_changed.emit(event.volume)
        self.mute_changed.emit(event.is_muted)
    
    def _on_duration_changed(self, event: PlayerDurationChangedEvent) -> None:
        """Handle duration change events from the event bus.
        
        Args:
            event: Duration change event containing new track duration
        """
        self.duration_changed.emit(event.duration)
    
    def _on_chapter_changed(self, event: PlayerChapterChangedEvent) -> None:
        """Handle chapter change events from the event bus.
        
        Args:
            event: Chapter change event containing new chapter index
        """
        self.chapter_changed.emit(event.chapter_index)
    
    def _on_error_occurred(self, event: PlayerErrorOccurredEvent) -> None:
        """Handle error events from the event bus.
        
        Args:
            event: Error event containing error message
        """
        self.error_occurred.emit(event.error_message)
    
    def _on_chapter_double_clicked(self, chapter_index: int):
        """Handle chapter double-click to seek to chapter start time."""
        if not self.chapter_widget or not hasattr(self.chapter_widget, 'chapters'):
            logger.warning("No chapter widget or chapter data available for seeking")
            return
            
        chapters = self.chapter_widget.chapters
        if not chapters or chapter_index < 0 or chapter_index >= len(chapters):
            logger.warning(f"Invalid chapter index {chapter_index}, available chapters: {len(chapters)}")
            return
            
        chapter = chapters[chapter_index]
        start_time = chapter.get('start', 0.0)
        title = chapter.get('title', f'Chapter {chapter_index + 1}')
        
        logger.info(f"Seeking to chapter '{title}' at {start_time:.2f} seconds")
        
        # Seek to chapter start time and start playing
        if self.taf_player:
            try:
                # Get current player state before seeking
                was_playing = hasattr(self.taf_player, 'is_playing') and self.taf_player.is_playing
                current_state_before = str(self.taf_player.player_state).split('.')[-1].lower() if hasattr(self.taf_player, 'player_state') else 'stopped'
                
                logger.debug(f"Before seek - was_playing: {was_playing}, state: {current_state_before}")
                
                if was_playing:
                    # If already playing, just seek to the new position
                    self.taf_player.seek(start_time)
                    logger.info(f"Seeked to chapter '{title}' at {start_time:.2f}s while playing")
                    target_state = "playing"
                else:
                    # If stopped or paused, we need to start playing from the specific position
                    # Use controller's play() method to properly update model state
                    self.play()  # Start playing (updates model state to PLAYING)
                    logger.debug(f"Started playback, now seeking to {start_time:.2f}s")
                    
                    # Small delay to let playback start
                    import time
                    time.sleep(0.2)
                    
                    # Now seek to the chapter position (this will restart from correct position)
                    self.taf_player.seek(start_time)
                    logger.info(f"Seeked to chapter '{title}' at {start_time:.2f}s")
                    target_state = "playing"
                
                # Verify the seek worked
                import time
                time.sleep(0.1)  # Small delay to let seek complete
                current_pos = self.taf_player.current_position if hasattr(self.taf_player, 'current_position') else 0
                logger.debug(f"After seek verification - target: {start_time:.2f}s, actual: {current_pos:.2f}s")
                
                # Update chapter highlighting with playing state after seeking
                if hasattr(self.chapter_widget, 'set_current_chapter'):
                    self.chapter_widget.set_current_chapter(chapter_index, target_state)
                    logger.debug(f"Updated chapter highlighting after seek: chapter {chapter_index}, state {target_state}")
                
            except Exception as e:
                logger.error(f"Failed to seek to chapter {chapter_index}: {e}")
        else:
            logger.warning("No TAF player available for seeking")
    
    def load_file(self, file_path, callback=None):
        """Load a TAF file."""
        try:
            # Stop any existing playback before loading new file
            if self.taf_player:
                self.taf_player.stop()
                logger.debug("Stopped existing playback before loading new file")
            
            self.model.state = PlayerState.LOADING
            
            self.taf_player = TAFPlayer()
            self.taf_player.load(str(file_path))
            
            # Get TAF analysis using domain objects
            from ...analysis import analyze_taf_file
            analysis_result = analyze_taf_file(Path(file_path))
            
            self.model.load_file(file_path, analysis_result)
            self.model.state = PlayerState.STOPPED
            
            logger.info(f"File loaded: {file_path}")
            
            # Call callback if provided
            if callback:
                callback(True, str(file_path))
            
        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            self.model.state = PlayerState.ERROR
            
            # Call callback with error if provided
            if callback:
                callback(False, str(file_path))
            self.model.state = PlayerState.ERROR
            self._publish_error(str(e))
    
    def load_playlist(self, input_path, callback=None):
        """Load a playlist from path (directory, pattern, or playlist file)."""
        try:
            # Stop any existing playback before loading new playlist
            if self.taf_player:
                self.taf_player.stop()
                logger.debug("Stopped existing playback before loading new playlist")
            
            self.model.state = PlayerState.LOADING
            
            self.taf_player = TAFPlayer()
            
            # Use the enhanced TAFPlayer playlist functionality
            success = self.taf_player.load_playlist_from_path(input_path)
            
            if success:
                # Get info about the current track and playlist
                playlist_info = self.taf_player.get_playlist_info()
                current_item = self.taf_player.playlist_manager.get_current_item()
                
                if current_item:
                    # Load the file into the TAF player engine
                    self.taf_player.load(str(current_item.file_path))
                    
                    # Get TAF analysis using domain objects
                    from ...analysis import analyze_taf_file
                    analysis_result = analyze_taf_file(current_item.file_path)
                    
                    # Update the model with file info
                    self.model.load_file(current_item.file_path, analysis_result)
                    self.model.state = PlayerState.STOPPED
                    
                    logger.info(f"Playlist loaded with {playlist_info['total_items']} tracks from: {input_path}")
                    
                    # Update playlist widget with loaded tracks
                    self._update_playlist_widget()
                    
                    # Update playlist info panel
                    self._update_playlist_info_panel()
                    
                    # Enable playlist controls
                    self._enable_playlist_controls()
                    
                    # Call callback if provided
                    if callback:
                        callback(True, input_path)
                else:
                    raise Exception("No tracks found in playlist")
            else:
                raise Exception("Failed to load playlist")
                
        except Exception as e:
            logger.error(f"Failed to load playlist: {e}")
            self.model.state = PlayerState.ERROR
            
            # Call callback with error if provided
            if callback:
                callback(False, input_path)
            self._publish_error(str(e))
    
    def toggle_playback(self):
        """Toggle play/pause."""
        if not self.taf_player:
            logger.warning("No TAF player available for toggle_playback")
            return
        
        try:
            if self.model.state == PlayerState.PLAYING:
                self.taf_player.pause()
                self.model.state = PlayerState.PAUSED
                if self._position_timer:
                    self._position_timer.stop()
            elif self.model.state == PlayerState.PAUSED:
                self.taf_player.resume()
                self.model.state = PlayerState.PLAYING
                if self._position_timer:
                    self._position_timer.start()
            else:
                self.taf_player.play()
                self.model.state = PlayerState.PLAYING
                if self._position_timer:
                    self._position_timer.start()
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self._publish_error(str(e))
    
    def play(self):
        """Start playback."""
        if not self.taf_player:
            logger.warning("Cannot play: No TAF player available")
            return
        
        try:
            self.taf_player.play()
            self.model.state = PlayerState.PLAYING
            if self._position_timer:
                self._position_timer.start()
                logger.debug("Position timer started")
            logger.info("Playback started")
        except Exception as e:
            logger.error(f"Play error: {e}")
            self._publish_error(str(e))
    
    def pause(self):
        """Pause playback."""
        if not self.taf_player:
            return
        
        try:
            self.taf_player.pause()
            self.model.state = PlayerState.PAUSED
            if self._position_timer:
                self._position_timer.stop()
            logger.info("Playback paused")
        except Exception as e:
            logger.error(f"Pause error: {e}")
            self._publish_error(str(e))
    
    def stop(self):
        """Stop playback."""
        if not self.taf_player:
            return
        
        try:
            self.taf_player.stop()
            self.model.state = PlayerState.STOPPED
            self.model.position = 0.0
            if self._position_timer:
                self._position_timer.stop()
        except Exception as e:
            logger.error(f"Stop error: {e}")
            self._publish_error(str(e))
    
    def seek(self, position):
        """Seek to position."""
        if not self.taf_player:
            return
        
        try:
            self.taf_player.seek(position)
            self.model.position = position
        except Exception as e:
            logger.error(f"Seek error: {e}")
            self._publish_error(str(e))
    
    def set_volume(self, volume):
        """Set volume."""
        volume = max(0.0, min(1.0, volume))
        logger.debug(f"Player controller set_volume called: {volume}")
        
        if self.taf_player:
            try:
                self.taf_player.set_volume(volume)
            except Exception as e:
                logger.error(f"Volume error: {e}")
        
        self.model.volume = volume
    
    def set_muted(self, is_muted):
        """Set mute state."""
        logger.debug(f"Player controller set_muted called: {is_muted}")
        
        if is_muted and not self.model.is_muted:
            # Store current volume before muting
            self._volume_before_mute = self.model.volume
        
        if self.taf_player:
            try:
                if is_muted:
                    self.taf_player.set_volume(0.0)
                else:
                    # Restore previous volume when unmuting
                    restore_volume = self._volume_before_mute if self._volume_before_mute > 0.0 else 0.5
                    self.taf_player.set_volume(restore_volume)
                    self.model.volume = restore_volume  # Update model volume when unmuting
            except Exception as e:
                logger.error(f"Mute error: {e}")
        
        self.model.is_muted = is_muted
    
    def next_chapter(self):
        """Go to next chapter."""
        pass
    
    def previous_chapter(self):
        """Go to previous chapter."""
        pass
    
    def next_track(self):
        """Go to next track in playlist."""
        logger.debug("next_track() called")
        if not self.taf_player or not hasattr(self.taf_player, 'next_track'):
            logger.warning("No playlist functionality available for next_track")
            return False
        
        try:
            logger.debug("Calling taf_player.next_track()")
            success = self.taf_player.next_track()
            logger.debug(f"next_track result: {success}")
            if success:
                self._update_playlist_info_panel()
                self._update_current_track_highlighting()
                self._update_playlist_controls_status()
            return success
        except Exception as e:
            logger.error(f"Failed to go to next track: {e}")
            self._publish_error(str(e))
            return False
    
    def previous_track(self):
        """Go to previous track in playlist."""
        logger.debug("previous_track() called")
        if not self.taf_player or not hasattr(self.taf_player, 'previous_track'):
            logger.warning("No playlist functionality available for previous_track")
            return False
        
        try:
            logger.debug("Calling taf_player.previous_track()")
            success = self.taf_player.previous_track()
            logger.debug(f"previous_track result: {success}")
            if success:
                self._update_playlist_info_panel()
                self._update_current_track_highlighting()
                self._update_playlist_controls_status()
            return success
        except Exception as e:
            logger.error(f"Failed to go to previous track: {e}")
            self._publish_error(str(e))
            return False
    
    def jump_to_track(self, index):
        """Jump to specific track in playlist."""
        if not self.taf_player or not hasattr(self.taf_player, 'jump_to_track'):
            logger.warning("No playlist functionality available for jump_to_track")
            return False
        
        try:
            success = self.taf_player.jump_to_track(index)
            if success:
                self._update_playlist_controls_status()
            return success
        except Exception as e:
            logger.error(f"Failed to jump to track {index}: {e}")
            self._publish_error(str(e))
            return False
    
    def get_playlist_info(self):
        """Get playlist information."""
        if not self.taf_player or not hasattr(self.taf_player, 'get_playlist_info'):
            return {'has_playlist': False}
        
        try:
            return self.taf_player.get_playlist_info()
        except Exception as e:
            logger.error(f"Failed to get playlist info: {e}")
            return {'has_playlist': False}
    
    def set_shuffle(self, enabled: bool):
        """Set shuffle mode for playlist."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist functionality available for shuffle")
            return False
        
        try:
            if hasattr(self.taf_player.playlist_manager, 'set_shuffle_mode'):
                self.taf_player.playlist_manager.set_shuffle_mode(enabled)
                logger.debug(f"Shuffle mode: {'enabled' if enabled else 'disabled'}")
                return True
        except Exception as e:
            logger.error(f"Failed to set shuffle mode: {e}")
            self._publish_error(str(e))
        return False
    
    def set_repeat_mode(self, mode: str):
        """Set repeat mode for playlist ('none', 'one', 'all')."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist functionality available for repeat mode")
            return False
        
        try:
            # Convert string to RepeatMode enum
            mode_map = {
                'none': RepeatMode.OFF,
                'one': RepeatMode.ONE,
                'all': RepeatMode.ALL
            }
            repeat_mode = mode_map.get(mode.lower(), RepeatMode.OFF)
            
            if hasattr(self.taf_player.playlist_manager, 'set_repeat_mode'):
                self.taf_player.playlist_manager.set_repeat_mode(repeat_mode)
                logger.debug(f"Repeat mode set to: {repeat_mode.value}")
                return True
        except Exception as e:
            logger.error(f"Failed to set repeat mode: {e}")
            self._publish_error(str(e))
        return False
    
    def set_auto_advance(self, enabled: bool):
        """Set auto-advance mode for playlist."""
        if not self.taf_player or not hasattr(self.taf_player, 'set_auto_advance'):
            logger.warning("No auto-advance functionality available")
            return False
        
        try:
            self.taf_player.set_auto_advance(enabled)
            logger.debug(f"Auto-advance: {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set auto-advance: {e}")
            self._publish_error(str(e))
        return False
    
    def select_track(self, index: int):
        """Select a track in the playlist (without playing)."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist functionality available for select_track")
            return False
        
        try:
            # Get the track information without changing playback
            playlist_manager = self.taf_player.playlist_manager
            all_items = playlist_manager.get_all_items()
            
            if 0 <= index < len(all_items):
                selected_item = all_items[index]
                
                # Update playlist info panel with selected track info
                if self.playlist_info_panel:
                    track_info = {
                        'file_path': str(selected_item.file_path),
                        'title': selected_item.title or selected_item.file_path.stem,
                        'duration': getattr(selected_item, 'duration', 0.0),
                        'metadata': getattr(selected_item, 'metadata', {}),
                        'index': index
                    }
                    
                    # Try to load detailed TAF info for the selected track
                    # Check cache first to avoid re-analyzing the file
                    try:
                        analysis_result = None
                        
                        # Try to get from cache
                        if (hasattr(playlist_manager, 'file_cache') and 
                            playlist_manager.file_cache):
                            analysis_result = playlist_manager.file_cache.get(selected_item.file_path)
                            if analysis_result:
                                logger.debug(f"Using cached analysis for track {index}")
                        
                        # Analyze if not cached
                        if not analysis_result:
                            from ...analysis import analyze_taf_file
                            analysis_result = analyze_taf_file(selected_item.file_path)
                            
                            # Cache the result
                            if (analysis_result and hasattr(playlist_manager, 'file_cache') and 
                                playlist_manager.file_cache):
                                playlist_manager.file_cache.put(selected_item.file_path, analysis_result)
                                logger.debug(f"Cached analysis for track {index}")
                        
                        if analysis_result:
                            # Convert domain object to dictionary for GUI compatibility
                            taf_info = {
                                'file_size': analysis_result.file_size,
                                'audio_size': analysis_result.audio_size,
                                'duration': analysis_result.audio_analysis.duration_seconds,
                                'total_time': analysis_result.audio_analysis.duration_formatted,
                                'bitrate': analysis_result.audio_analysis.bitrate_kbps,
                                'channels': analysis_result.opus_info.channels,
                                'sample_rate': analysis_result.opus_info.sample_rate,
                                'valid': analysis_result.valid,
                                'chapter_count': len(analysis_result.tonie_header.chapters)
                            }
                            track_info.update(taf_info)
                                
                            logger.debug(f"Loaded detailed TAF info for track {index}: {len(taf_info)} properties")
                    except Exception as e:
                        logger.debug(f"Could not analyze TAF file {selected_item.file_path}: {e}")
                    
                    self.playlist_info_panel.update_current_track_info(track_info)
                
                logger.debug(f"Selected track {index}: {selected_item.title or selected_item.file_path.stem}")
                return True
            else:
                logger.warning(f"Invalid track index: {index} (playlist has {len(all_items)} tracks)")
                return False
                
        except Exception as e:
            logger.error(f"Failed to select track {index}: {e}")
            self._publish_error(str(e))
            return False
    
    def play_track_at_index(self, index: int):
        """Play a specific track in the playlist."""
        if self.jump_to_track(index):
            return self.play()
        return False
    
    def remove_track(self, index: int):
        """Remove a track from the playlist."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist functionality available for remove_track")
            return False
        
        try:
            if hasattr(self.taf_player.playlist_manager, 'remove_item'):
                success = self.taf_player.playlist_manager.remove_item(index)
                if success:
                    logger.debug(f"Removed track at index: {index}")
                    # Update UI after removal
                    self._update_playlist_widget()
                    self._update_playlist_info_panel()
                    # Trigger auto-save
                    self._trigger_auto_save()
                    return True
        except Exception as e:
            logger.error(f"Failed to remove track: {e}")
            self._publish_error(str(e))
        return False
    
    def clear_playlist(self):
        """Clear the entire playlist."""
        logger.info("QtPlayerController.clear_playlist() called")
        
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist functionality available for clear_playlist")
            return False
        
        try:
            if hasattr(self.taf_player.playlist_manager, 'clear_playlist'):
                # Stop playback first
                self.stop()
                
                logger.info("Calling playlist_manager.clear_playlist()")
                self.taf_player.playlist_manager.clear_playlist()
                logger.info("Playlist cleared, updating UI")
                
                # Update UI after clearing
                self._update_playlist_widget()
                self._update_playlist_info_panel()
                
                # Clear chapter widget
                if self.chapter_widget and hasattr(self.chapter_widget, 'clear_chapters'):
                    self.chapter_widget.clear_chapters()
                    logger.debug("Cleared chapters from chapter widget")
                
                # Delete auto-save file since playlist is now empty
                self._delete_auto_save()
                
                return True
            else:
                logger.error("playlist_manager does not have clear_playlist method")
        except Exception as e:
            logger.error(f"Failed to clear playlist: {e}")
            self._publish_error(str(e))
        return False
    
    def move_playlist_item(self, from_index: int, to_index: int):
        """Move a playlist item from one position to another."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist functionality available for move_playlist_item")
            return False
        
        try:
            playlist_manager = self.taf_player.playlist_manager
            if hasattr(playlist_manager, 'move_item'):
                success = playlist_manager.move_item(from_index, to_index)
                if success:
                    logger.debug(f"Moved playlist item from {from_index} to {to_index}")
                    # Update the playlist widget to reflect the new order
                    self._update_playlist_widget()
                    return True
                else:
                    logger.warning(f"Failed to move playlist item from {from_index} to {to_index}")
            else:
                logger.warning("Playlist manager does not support item moving")
        except Exception as e:
            logger.error(f"Failed to move playlist item: {e}")
            self._publish_error(str(e))
        return False
    
    def add_files_to_playlist(self, file_paths: list):
        """Add files to the current playlist."""
        logger.debug(f"add_files_to_playlist called with {len(file_paths)} files")
        
        # If no player exists, create a playlist from the files
        if not self.taf_player:
            logger.info("No player exists, creating new playlist from files")
            result = self._create_playlist_from_files(file_paths)
            logger.debug(f"_create_playlist_from_files returned: {result}")
            return result
        
        logger.debug(f"Player exists: {self.taf_player is not None}")
        
        # If player exists but has no playlist manager, initialize it
        if not hasattr(self.taf_player, 'playlist_manager') or not self.taf_player.playlist_manager:
            logger.info("Player exists but has no playlist manager - initializing")
            self.taf_player._ensure_playlist_manager()
            logger.debug(f"After _ensure, playlist_manager is: {self.taf_player.playlist_manager is not None}")
        
        try:
            from pathlib import Path
            playlist_manager = self.taf_player.playlist_manager
            logger.debug(f"playlist_manager: {playlist_manager is not None}")
            
            # If no playlist exists yet, load as new playlist
            if not playlist_manager or not hasattr(playlist_manager, 'playlist') or not playlist_manager.playlist.items:
                logger.info("No existing playlist, creating new playlist from files")
                result = self._create_playlist_from_files(file_paths)
                logger.debug(f"_create_playlist_from_files returned: {result}")
                return result
            else:
                logger.debug("Adding to existing playlist")
                # Add to existing playlist
                added_count = 0
                for file_path in file_paths:
                    if hasattr(playlist_manager, 'add_file'):
                        if playlist_manager.add_file(Path(file_path)):
                            added_count += 1
                        
                if added_count > 0:
                    # Update the playlist widget
                    self._update_playlist_widget()
                    logger.info(f"Added {added_count} file(s) to existing playlist")
                    return True
                else:
                    logger.warning("No files were added to existing playlist")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to add files to playlist: {e}", exc_info=True)
            self._publish_error(str(e))
            return False
    
    def _create_playlist_from_files(self, file_paths: list):
        """Create a new playlist from a list of files.
        
        This method ensures the TAFPlayer has a properly initialized playlist manager,
        adds all valid TAF files to it, loads the first track, and updates the UI.
        
        Args:
            file_paths: List of file paths to create playlist from
            
        Returns:
            bool: True if playlist was created successfully
        """
        if not file_paths:
            logger.warning("No files provided to create playlist")
            return False
            
        try:
            from pathlib import Path
            
            # Step 1: Ensure player exists
            if not self.taf_player:
                from ...media.player.engine import TAFPlayer
                self.taf_player = TAFPlayer()
                logger.debug("Created new TAFPlayer instance")
            
            # Step 2: Ensure playlist manager exists (critical!)
            # This is the single source of truth for playlist state
            if not hasattr(self.taf_player, 'playlist_manager') or self.taf_player.playlist_manager is None:
                from ...media.playlist import PlaylistManager
                logger.info("Creating new PlaylistManager for TAFPlayer")
                
                self.taf_player.playlist_manager = PlaylistManager()
                
                # Verify it was created successfully
                if self.taf_player.playlist_manager is None:
                    logger.error("Failed to create PlaylistManager - constructor returned None")
                    return False
                
                # Add callback for playlist item changes
                self.taf_player.playlist_manager.add_current_item_changed_callback(
                    self.taf_player._on_playlist_item_changed
                )
                logger.debug(f"PlaylistManager initialized: {type(self.taf_player.playlist_manager)}")
            
            # Step 3: Clear any existing playlist items
            self.taf_player.playlist_manager.clear_playlist()
            logger.debug("Cleared existing playlist items")
            
            # Step 4: Add all valid TAF files to the playlist manager
            added_count = 0
            skipped_count = 0
            
            for file_path in file_paths:
                path_obj = Path(file_path)
                
                # Filter: Only add .taf files
                if path_obj.suffix.lower() != '.taf':
                    logger.warning(f"Skipping non-TAF file: {path_obj.name}")
                    skipped_count += 1
                    continue
                
                # Add file to playlist manager
                if self.taf_player.playlist_manager.add_file(path_obj):
                    added_count += 1
                    logger.debug(f"Added to playlist manager: {path_obj.name}")
                else:
                    logger.warning(f"Failed to add file to playlist: {path_obj.name}")
                    skipped_count += 1
            
            # Check if we added any files
            if added_count == 0:
                logger.error(f"No TAF files were added to playlist (skipped: {skipped_count})")
                return False
            
            logger.info(f"Created playlist with {added_count} file(s), skipped {skipped_count}")
            
            # Step 5: Set first track as current and load it into the player
            # CRITICAL: After adding files, we must explicitly jump to first track to set current_item
            first_item = self.taf_player.playlist_manager.jump_to_item(0)
            if first_item:
                logger.debug(f"Loading first track: {first_item.file_path}")
                from ...analysis import analyze_taf_file
                analysis_result = analyze_taf_file(first_item.file_path)
                self.model.load_file(first_item.file_path, analysis_result)
                self.model.state = PlayerState.STOPPED
            else:
                logger.error("Failed to jump to first item in playlist")
                return False
            
            # Step 6: Update UI to reflect the playlist state
            self._update_playlist_widget()
            self._update_playlist_info_panel()
            self._enable_playlist_controls()
            
            # Verify playlist manager is still accessible (sanity check)
            if self.taf_player.playlist_manager is None:
                logger.error("PlaylistManager became None after setup!")
                return False
            
            logger.info("Playlist creation completed successfully")
            return True
                
        except Exception as e:
            logger.error(f"Failed to create playlist from files: {e}", exc_info=True)
            self._publish_error(str(e))
            return False
    
    # Getters
    def get_state(self):
        return self.model.state
    
    def get_position(self):
        return self.model.position
    
    def get_duration(self):
        return self.model.duration
    
    def get_volume(self):
        return self.model.volume
    
    def get_muted(self):
        return self.model.is_muted
    
    def get_file_info(self):
        return self.model.file_info
    
    def get_chapters(self):
        return self.model.chapters
    
    def get_current_chapter(self):
        return self.model.current_chapter
    
    def _update_position(self):
        """Update position from TAF player."""
        if self.taf_player and self.model.state == PlayerState.PLAYING:
            try:
                position = self.taf_player.get_position()
                self.model.position = position
            except Exception as e:
                logger.error(f"Position update error: {e}")
    
    def _publish_error(self, error_message):
        """Publish error event."""
        error_event = PlayerErrorOccurredEvent(
            source="qt_player_controller",
            error_message=error_message
        )
        self.event_bus.publish(error_event)
    
    def _trigger_auto_save(self):
        """Trigger auto-save of the current playlist."""
        try:
            from pathlib import Path
            from TonieToolbox.core.config import get_config_manager
            config = get_config_manager()
            
            auto_save_enabled = config.get_setting("gui.behavior.auto_save_playlist")
            if not auto_save_enabled:
                return
            
            last_playlist_path = Path(config.get_setting("gui.behavior.last_playlist_path"))
            
            # Check if there's a playlist to save
            if (self.taf_player and 
                hasattr(self.taf_player, 'playlist_manager') and
                self.taf_player.playlist_manager and
                not self.taf_player.playlist_manager.is_empty()):
                
                # Ensure directory exists
                last_playlist_path.parent.mkdir(parents=True, exist_ok=True)
                
                logger.debug(f"Auto-saving playlist to: {last_playlist_path}")
                self.save_playlist(last_playlist_path)
            else:
                # If playlist is empty, delete the auto-save file
                self._delete_auto_save()
                
        except Exception as e:
            logger.error(f"Failed to auto-save playlist: {e}")
    
    def _delete_auto_save(self):
        """Delete the auto-save playlist file."""
        try:
            from pathlib import Path
            from TonieToolbox.core.config import get_config_manager
            config = get_config_manager()
            
            last_playlist_path = Path(config.get_setting("gui.behavior.last_playlist_path"))
            
            if last_playlist_path.exists():
                last_playlist_path.unlink()
                logger.info(f"Deleted auto-save playlist file: {last_playlist_path}")
            
        except Exception as e:
            logger.error(f"Failed to delete auto-save file: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        if self._position_timer and self._position_timer.isActive():
            self._position_timer.stop()
        
        if self.taf_player:
            try:
                self.taf_player.cleanup()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        logger.info("Qt player controller cleanup completed")
    
    def set_playlist_widget(self, playlist_widget):
        """Set reference to the playlist widget for updates."""
        self.playlist_widget = playlist_widget
    
    def set_chapter_widget(self, chapter_widget):
        """Set reference to the chapter widget for updates."""
        self.chapter_widget = chapter_widget
        
        # Connect chapter double-click signal for seeking
        if hasattr(chapter_widget, 'chapter_double_clicked'):
            chapter_widget.chapter_double_clicked.connect(self._on_chapter_double_clicked)
            logger.debug("Connected chapter double-click signal for seeking")
    
    def set_player_controls(self, player_controls):
        """Set reference to the player controls for updates."""
        self.player_controls = player_controls
    
    def set_playlist_controls(self, playlist_controls):
        """Set reference to the playlist controls for updates."""
        self.playlist_controls = playlist_controls
    
    def set_playlist_info_panel(self, playlist_info_panel):
        """Set reference to the playlist info panel for updates."""
        self.playlist_info_panel = playlist_info_panel
    
    def set_main_window(self, main_window):
        """Set reference to the main window for layout updates."""
        self.main_window = main_window
    
    def _update_playlist_widget(self):
        """Update the playlist widget with current playlist data."""
        logger.debug(f"_update_playlist_widget called, playlist_widget={self.playlist_widget is not None}, taf_player={self.taf_player is not None}")
        
        if not self.playlist_widget or not self.taf_player:
            logger.warning("Cannot update playlist widget - missing playlist_widget or taf_player")
            return
        
        if hasattr(self.taf_player, 'playlist_manager'):
            playlist_manager = self.taf_player.playlist_manager
            logger.debug(f"playlist_manager exists: {playlist_manager is not None}, type: {type(playlist_manager)}")
            
            if playlist_manager is not None:
                try:
                    # Get playlist items from the playlist manager
                    playlist_items = []
                    for item in playlist_manager.get_all_items():
                        playlist_items.append({
                            'file_path': str(item.file_path),
                            'title': item.title or item.file_path.stem,
                            'duration': getattr(item, 'duration', 0.0),
                            'metadata': getattr(item, 'metadata', {})
                        })
                    
                    # Update the playlist widget
                    logger.info(f"Calling playlist_widget.load_playlist() with {len(playlist_items)} items")
                    self.playlist_widget.load_playlist(playlist_items)
                    logger.debug(f"Updated playlist widget with {len(playlist_items)} tracks")
                    
                    # Update current track highlighting
                    self._update_current_track_highlighting()
                    
                except Exception as e:
                    logger.error(f"Failed to update playlist widget: {e}", exc_info=True)
            else:
                logger.warning("playlist_manager is None")
        else:
            logger.warning("No playlist_manager attribute on taf_player")
    
    def _update_current_track_highlighting(self):
        """Update the playlist widget to highlight the current track."""
        if not self.playlist_widget or not self.taf_player:
            return
        
        if hasattr(self.taf_player, 'playlist_manager') and self.taf_player.playlist_manager:
            try:
                # Get current track index
                current_index = self.taf_player.playlist_manager.playlist.current_index
                
                # Determine player state for visual indicator
                player_state = "stopped"
                if self.model.state == PlayerState.PLAYING:
                    player_state = "playing"
                elif self.model.state == PlayerState.PAUSED:
                    player_state = "paused"
                elif self.model.state == PlayerState.LOADING:
                    player_state = "loading"
                
                # Update highlighting in playlist widget
                self.playlist_widget.set_current_track(current_index, player_state)
                logger.debug(f"Updated playlist highlighting: track {current_index}, state {player_state}")
                
            except Exception as e:
                logger.error(f"Failed to update current track highlighting: {e}")
    
    def _update_playlist_info_panel(self):
        """Update the playlist info panel with current playlist information."""
        if not self.playlist_info_panel or not self.taf_player:
            return
        
        try:
            # Get playlist information
            playlist_info = self.taf_player.get_playlist_info()
            if playlist_info:
                self.playlist_info_panel.update_playlist_info(playlist_info)
                logger.debug(f"Updated playlist info panel with {playlist_info.get('total_items', 0)} tracks")
            
            # Only update current track if there are items in the playlist
            if playlist_info and playlist_info.get('total_items', 0) > 0:
                # Get current track information
                current_item = self.taf_player.playlist_manager.get_current_item()
                if current_item:
                    track_info = {
                        'file_path': str(current_item.file_path),
                        'title': current_item.title or current_item.file_path.stem,
                        'duration': getattr(current_item, 'duration', 0.0),
                        'metadata': getattr(current_item, 'metadata', {})
                    }
                    # Add TAF file info if available
                    if hasattr(self.taf_player, 'taf_info') and self.taf_player.taf_info:
                        track_info.update(self.taf_player.taf_info)
                    
                    self.playlist_info_panel.update_current_track_info(track_info)
                    logger.debug(f"Updated current track info for: {track_info.get('title', 'Unknown')}")
            else:
                # Clear track info when playlist is empty
                self.playlist_info_panel.update_current_track_info({})
                logger.debug("Cleared current track info (playlist empty)")
                
        except Exception as e:
            logger.error(f"Failed to update playlist info panel: {e}")
    
    def _enable_playlist_controls(self):
        """Enable playlist controls when a playlist is loaded."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            return
        
        playlist_manager = self.taf_player.playlist_manager
        if not playlist_manager:
            return
        
        all_items = playlist_manager.get_all_items()
        track_count = len(all_items)
        has_playlist = track_count > 0
        has_multiple_tracks = track_count > 1
        
        logger.debug(f"Enabling playlist controls: has_playlist={has_playlist}, tracks={track_count}")
        
        # Enable track navigation in PlayerControls
        if self.player_controls and hasattr(self.player_controls, 'set_playlist_mode'):
            self.player_controls.set_playlist_mode(has_playlist, has_multiple_tracks)
        
        # Enable playlist options in PlaylistControls
        if self.playlist_controls and hasattr(self.playlist_controls, 'set_playlist_mode'):
            self.playlist_controls.set_playlist_mode(has_playlist, has_multiple_tracks)
        
        # Update playlist controls status with current playlist state
        self._update_playlist_controls_status()
        
        # Set main window panel visibility
        if self.main_window and hasattr(self.main_window, 'set_playlist_mode'):
            self.main_window.set_playlist_mode(has_playlist)
    
    def _update_playlist_controls_status(self):
        """Update playlist controls to reflect current playlist state."""
        if not self.playlist_controls or not self.taf_player:
            return
        
        if not hasattr(self.taf_player, 'playlist_manager') or not self.taf_player.playlist_manager:
            return
        
        try:
            playlist = self.taf_player.playlist_manager.playlist
            current_index = playlist.current_index
            total_tracks = len(playlist.items)
            is_shuffled = playlist.shuffle_mode
            
            # Convert repeat mode enum to string
            repeat_mode_map = {
                RepeatMode.OFF: 'none',
                RepeatMode.ONE: 'one',
                RepeatMode.ALL: 'all'
            }
            repeat_mode = repeat_mode_map.get(playlist.repeat_mode, 'none')
            
            # Update the playlist controls UI
            if hasattr(self.playlist_controls, 'update_playlist_status'):
                self.playlist_controls.update_playlist_status(
                    current_index, total_tracks, is_shuffled, repeat_mode
                )
                logger.debug(f"Updated playlist controls: index={current_index}, "
                           f"shuffle={is_shuffled}, repeat={repeat_mode}")
        except Exception as e:
            logger.error(f"Failed to update playlist controls status: {e}")

    
    def save_playlist(self, file_path: Path, playlist_name: Optional[str] = None) -> bool:
        """
        Save current playlist to a .lst file.
        
        Args:
            file_path: Path where playlist will be saved
            playlist_name: Optional custom name for the playlist
            
        Returns:
            True if playlist was saved successfully
        """
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            logger.warning("No playlist manager available for saving playlist")
            return False
        
        try:
            # Get current playback state
            current_track = None
            seek_position = None
            
            if self.taf_player.playlist_manager:
                current_track = self.taf_player.playlist_manager.playlist.current_index
                
                # Get current playback position
                # Priority: current_position (if playing/paused) > pause_position (if stopped) > model.position (fallback)
                if self.taf_player:
                    if hasattr(self.taf_player, 'current_position') and self.taf_player.current_position > 0:
                        seek_position = self.taf_player.current_position
                    elif hasattr(self.taf_player, 'pause_position') and self.taf_player.pause_position > 0:
                        seek_position = self.taf_player.pause_position
                    elif self.model and self.model.position > 0:
                        seek_position = self.model.position
                    
                    if seek_position and seek_position > 0:
                        logger.debug(f"Saving playback state: track {current_track}, position {seek_position:.2f}s")
            
            success = self.taf_player.playlist_manager.save_to_file(
                file_path, playlist_name, current_track, seek_position
            )
            if success:
                logger.info(f"Saved playlist to: {file_path}")
            return success
        except Exception as e:
            logger.error(f"Failed to save playlist: {e}")
            return False
    
    def load_playlist_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Load a playlist from a .lst file.
        
        Args:
            file_path: Path to the .lst file
            
        Returns:
            Tuple of (success, error_message)
        """
        # Stop any existing playback before loading new playlist
        if self.taf_player:
            self.taf_player.stop()
            logger.debug("Stopped existing playback before loading playlist file")
        
        if not self.taf_player:
            self.taf_player = TAFPlayer()
        
        # Ensure playlist manager is initialized
        self.taf_player._ensure_playlist_manager()
        
        if self.taf_player.playlist_manager is None:
            logger.warning("No playlist manager available for loading playlist")
            return (False, "Playlist manager not available")
        
        try:
            success = self.taf_player.playlist_manager.load_from_file(file_path)
            if success:
                logger.info(f"Loaded playlist from: {file_path}")
                
                # Get saved seek position before loading track
                saved_seek_position = self.taf_player.playlist_manager.get_saved_seek_position()
                
                # Load the current track
                current_item = self.taf_player.playlist_manager.get_current_item()
                if current_item:
                    from ...analysis import analyze_taf_file
                    analysis_result = analyze_taf_file(current_item.file_path)
                    self.model.load_file(current_item.file_path, analysis_result)
                    self.model.state = PlayerState.STOPPED
                    
                    # Load the file into the TAF player engine
                    self.taf_player.load(str(current_item.file_path))
                    
                    # Restore seek position if available
                    if saved_seek_position is not None and saved_seek_position > 0:
                        logger.info(f"Restoring playback position: {saved_seek_position:.2f}s")
                        # Seek to saved position without starting playback
                        self.taf_player.pause_position = saved_seek_position
                        self.model.position = saved_seek_position
                        logger.debug(f"Set initial position to {saved_seek_position:.2f}s")
                        # Clear the saved position after using it
                        self.taf_player.playlist_manager.clear_saved_seek_position()
                
                # Update UI
                self._update_playlist_widget()
                self._update_playlist_info_panel()
                self._enable_playlist_controls()
                
                return (True, None)
            else:
                # Get error message from playlist manager (untranslated)
                error_key = self.taf_player.playlist_manager.get_last_error()
                return (False, error_key)
        except Exception as e:
            logger.error(f"Failed to load playlist file: {e}")
            return (False, str(e))
    
    def get_playlist_name(self) -> Optional[str]:
        """Get the current playlist name."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            return None
        return self.taf_player.playlist_manager.get_playlist_name()
    
    def set_playlist_name(self, name: str) -> None:
        """Set the playlist name."""
        if not self.taf_player or not hasattr(self.taf_player, 'playlist_manager'):
            return
        self.taf_player.playlist_manager.set_playlist_name(name)
