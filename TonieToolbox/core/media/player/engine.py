#!/usr/bin/env python3
"""
TAF Player Engine Module for TonieToolbox
Core audio playback engine for TAF (Tonie Audio Format) files.
"""
import os
import sys
import time
import tempfile
import threading
import subprocess
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from ...utils import get_logger
# Imports moved to function level to avoid circular dependencies
from ...dependencies import get_ffplay_binary
from ...config.application_constants import SAMPLE_RATE_KHZ
logger = get_logger(__name__)


class TAFPlayerError(Exception):
    """Custom exception for TAF player errors.
    
    Raised when TAF player operations fail, including file loading errors,
    playback initialization failures, or audio decoding issues.
    
    Example:
        Invalid TAF file::
        
            if not is_valid_taf_file(file_path):
                raise TAFPlayerError(
                    f"Cannot load invalid TAF file: {file_path}"
                )
        
        FFmpeg not available::
        
            if not ffmpeg_binary:
                raise TAFPlayerError(
                    "FFmpeg binary not found - required for audio playback"
                )
        
        Playback initialization failed::
        
            try:
                player.load(taf_file_path)
                player.play()
            except TAFPlayerError as e:
                logger.error(f"Playback failed: {e}")
                show_error_dialog("Cannot play TAF file", str(e))
    """
    pass


class TAFPlayer:
    """
    A simple TAF file player using FFmpeg for audio playback.
    This player can load TAF files, extract audio data, and play it using FFmpeg.
    It supports basic playback controls like play, pause, resume, stop, and seek.
    """
    
    def __init__(self, ffmpeg_binary: str = None):
        """Initialize the TAF player."""
        self.taf_file: Optional[Path] = None
        self.taf_info: Optional[Dict[str, Any]] = None
        self.temp_audio_file: Optional[Path] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.current_position: float = 0.0
        self.total_duration: float = 0.0
        self.pause_position: float = 0.0
        self.playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.header_size: int = 0
        
        # Volume control state
        self._volume: float = 1.0  # Volume level (0.0 to 1.0)
        self._is_muted: bool = False  # Mute state
        self._volume_before_mute: float = 1.0  # Volume before muting
        self._volume_update_timer: Optional[threading.Timer] = None  # Debounce volume updates
        
        # Playlist functionality (optional)
        self.playlist_manager: Optional[object] = None  # Lazy initialized when needed
        self._auto_advance: bool = True
        self._track_end_callbacks: List[Callable] = []
        self._track_changed_callbacks: List[Callable] = []
        self._playback_monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        
        # Resolve FFmpeg binary if not provided
        if ffmpeg_binary is None:
            try:
                from ...dependencies import get_ffmpeg_binary
                ffmpeg_binary = get_ffmpeg_binary(auto_download=False)
                if not ffmpeg_binary:
                    raise TAFPlayerError("FFmpeg not found. Please install FFmpeg or provide ffmpeg_binary parameter.")
            except Exception as e:
                raise TAFPlayerError(f"Failed to resolve FFmpeg binary: {e}")
        
        self.ffmpeg_binary: str = ffmpeg_binary
    
    def load(self, taf_file_path: str) -> None:
        """
        Load a TAF file for playback.
        
        Args:
            taf_file_path: Path to the TAF file to load
            
        Raises:
            TAFPlayerError: If the file cannot be loaded or parsed
        """
        taf_path = Path(taf_file_path)
        if not taf_path.exists():
            raise TAFPlayerError(f"TAF file not found: {taf_file_path}")
        if not taf_path.suffix.lower() == '.taf':
            raise TAFPlayerError(f"File is not a TAF file: {taf_file_path}")
        
        logger.info(f"Loading TAF file: {taf_path}")
        
        try:
            with open(taf_path, 'rb') as taf_file:
                # Local imports to avoid circular dependencies
                from ...analysis.header import get_header_info_cli
                from ...analysis import get_audio_info
                
                header_size, tonie_header, file_size, audio_size, sha1sum, \
                opus_head_found, opus_version, channel_count, sample_rate, \
                bitstream_serial_no, opus_comments, valid = get_header_info_cli(taf_file)
                
                if not valid:
                    raise TAFPlayerError("Invalid or corrupted TAF file")
                    
                page_count, alignment_okay, page_size_okay, total_time, \
                chapter_times, ffprobe_bitrate = get_audio_info(taf_file, sample_rate // 1000, tonie_header, header_size, self.ffmpeg_binary)
                
                self.header_size = 4 + header_size
                self.taf_info = {
                    'file_size': file_size,
                    'audio_size': audio_size,
                    'sha1_hash': sha1sum.hexdigest() if sha1sum else None,
                    'sample_rate': sample_rate,
                    'channels': channel_count,
                    'bitstream_serial': bitstream_serial_no,
                    'opus_version': opus_version,
                    'page_count': page_count,
                    'total_time': total_time,
                    'opus_comments': opus_comments,
                    'chapters': [],
                    # Additional comprehensive information for GUI compatibility with --info
                    'header_size': header_size,
                    'tonie_header': tonie_header,
                    'opus_head_found': opus_head_found,
                    'valid': valid,
                    'alignment_okay': alignment_okay,
                    'page_size_okay': page_size_okay,
                    'chapter_times': chapter_times
                }
                
                # Process chapters if available
                if hasattr(tonie_header, 'chapterPages') and len(tonie_header.chapterPages) > 0:
                    chapter_start_time = 0.0
                    for i, chapter_time in enumerate(chapter_times):
                        duration_seconds = self._parse_time_string(chapter_time)
                        self.taf_info['chapters'].append({
                            'index': i,  # Use 0-based index for consistent array access
                            'title': f'Chapter {i + 1}',
                            'duration': duration_seconds,
                            'start': chapter_start_time
                        })
                        chapter_start_time += duration_seconds
                
                # Use accurate bitrate from ffprobe, fallback to opus comments
                if ffprobe_bitrate > 0:
                    self.taf_info['bitrate'] = ffprobe_bitrate
                elif opus_comments and 'encoder_options' in opus_comments:
                    import re
                    match = re.search(r'bitrate=(\d+)', opus_comments['encoder_options'])
                    if match:
                        self.taf_info['bitrate'] = int(match.group(1))
                
                self.taf_file = taf_path
                self.total_duration = self._parse_time_string(total_time)
                
                # Clean up old temporary audio file when loading new track
                if self.temp_audio_file and self.temp_audio_file.exists():
                    try:
                        self.temp_audio_file.unlink()
                        logger.debug(f"Cleaned up old temporary file: {self.temp_audio_file}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up old temporary file: {e}")
                self.temp_audio_file = None
                
                # Reset position and playback state when loading new file
                self.current_position = 0.0
                self.is_playing = False
                self.is_paused = False
                
                logger.info(f"Successfully loaded TAF file: {taf_path.name}")
                logger.debug(f"File info: {self.taf_info}")

                # Publish file loaded and duration events to notify GUI
                from ...events.player_events import PlayerFileLoadedEvent, PlayerDurationChangedEvent
                # Note: PlayerFileLoadedEvent is now published by the player controller
                # with proper domain objects. Duration event is still needed for player state.
                from ...events import get_event_bus
                event_bus = get_event_bus()
                
                logger.debug(f"Publishing PlayerDurationChangedEvent with duration: {self.total_duration}")
                event_bus.publish(PlayerDurationChangedEvent(
                    source="TAFPlayer.load_file",
                    duration=self.total_duration
                ))
                
        except Exception as e:
            raise TAFPlayerError(f"Failed to load TAF file: {e}")
    
    def _parse_time_string(self, time_str: str) -> float:
        """Parse a time string (HH:MM:SS.FF or MM:SS.CC) to seconds."""

        try:
            parts = time_str.split(':')
            if len(parts) == 2:
                # MM:SS.CC format
                minutes = int(parts[0])
                seconds_parts = parts[1].split('.')
                seconds = int(seconds_parts[0])
                centiseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                total_seconds = minutes * 60 + seconds + centiseconds / 100.0
            elif len(parts) == 3:
                # HH:MM:SS.FF format
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds_parts = parts[2].split('.')
                seconds = int(seconds_parts[0])
                centiseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
            else:
                return 0.0
            
            return total_seconds
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse time string '{time_str}': {e}")
            return 0.0
    
    def _extract_audio_data(self) -> Path:
        """Extract audio data from TAF file to a temporary file."""
        if not self.taf_file:
            raise TAFPlayerError("No TAF file loaded")
        
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False)
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            with open(self.taf_file, 'rb') as taf_file:
                # Skip header and read audio data
                taf_file.seek(self.header_size)
                audio_data = taf_file.read()
                
            with open(temp_path, 'wb') as audio_file:
                audio_file.write(audio_data)
            
            logger.debug(f"Extracted audio data to: {temp_path}")
            return temp_path
            
        except Exception as e:
            raise TAFPlayerError(f"Failed to extract audio data: {e}")
    
    def play(self) -> None:
        """Start playing the loaded TAF file."""
        if not self.taf_file:
            raise TAFPlayerError("No TAF file loaded")
        
        if self.is_playing:
            logger.warning("Already playing")
            return
        
        try:
            # Extract audio data if not already done
            if not self.temp_audio_file:
                self.temp_audio_file = self._extract_audio_data()
            
            # Get FFplay binary
            ffplay_binary = get_ffplay_binary()
            
            # Check if we should start from a saved position
            start_position = 0.0
            if hasattr(self, 'pause_position') and self.pause_position > 0:
                start_position = self.pause_position
                logger.debug(f"Starting playback from saved position: {start_position:.2f}s")
                # Clear pause_position after using it so subsequent plays start from beginning
                self.pause_position = 0.0
            
            # Start FFplay process with volume control
            ffplay_cmd = [
                ffplay_binary,
            ]
            
            # Add start position if needed
            if start_position > 0:
                ffplay_cmd.extend(['-ss', str(start_position)])
            
            ffplay_cmd.extend([
                '-autoexit',  # Exit when playback finishes
                '-nodisp',    # No video display window
                '-loglevel', 'quiet',  # Quiet output
            ])
            
            # Add volume filter if needed
            effective_volume = 0.0 if self._is_muted else self._volume
            if effective_volume != 1.0:
                # Use audio filter to control volume
                ffplay_cmd.extend(['-af', f'volume={effective_volume}'])
            
            ffplay_cmd.append(str(self.temp_audio_file))
            
            logger.debug(f"Starting FFplay: {' '.join(ffplay_cmd)}")
            
            self.ffmpeg_process = subprocess.Popen(
                ffplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.is_playing = True
            self.is_paused = False
            self._stop_event.clear()
            
            # Set initial position if we started from a saved position
            if start_position > 0:
                self.current_position = start_position
            
            # Start position tracking thread
            self.playback_thread = threading.Thread(target=self._track_position)
            self.playback_thread.start()
            
            # Start playlist monitoring if needed
            has_playlist = self.has_playlist()
            auto_advance_enabled = self._auto_advance
            logger.debug(f"Checking playlist monitor conditions - has_playlist: {has_playlist}, auto_advance: {auto_advance_enabled}")
            
            if has_playlist and auto_advance_enabled:
                self._start_playlist_monitor()
            else:
                logger.debug(f"Playlist monitor not started - conditions not met")
            
            logger.info("Playback started")
            
        except Exception as e:
            raise TAFPlayerError(f"Failed to start playback: {e}")
    
    def _track_position(self) -> None:
        """Track playback position in a separate thread."""
        start_time = time.time()
        # Account for starting position (when resuming from saved position)
        start_position = self.current_position
        
        while self.is_playing and not self._stop_event.is_set():
            if not self.is_paused and self.ffmpeg_process:
                # Check if process is still running
                if self.ffmpeg_process.poll() is not None:
                    # Process finished
                    self.is_playing = False
                    break
                
                # Update position based on elapsed time + start position
                elapsed = time.time() - start_time
                self.current_position = min(start_position + elapsed, self.total_duration)
                
                # Publish position update event
                try:
                    from ...events.player_events import PlayerPositionChangedEvent
                    from ...events import get_event_bus
                    get_event_bus().publish(PlayerPositionChangedEvent(
                        source="TAFPlayer._track_position",
                        position=self.current_position
                    ))
                except Exception:
                    pass  # Don't break playback if event system fails
                
                # Check if we've reached the end
                if self.current_position >= self.total_duration:
                    # Only stop if we don't have a playlist (let playlist monitor handle it)
                    if not self.has_playlist():
                        self.is_playing = False
                        break
            
            time.sleep(0.1)  # Update every 100ms
        
        logger.debug("Position tracking stopped")
    
    def _track_position_from_seek(self, start_position: float) -> None:
        """Track playback position starting from a seek position."""
        start_time = time.time()
        
        while self.is_playing and not self._stop_event.is_set():
            if not self.is_paused and self.ffmpeg_process:
                # Check if process is still running
                if self.ffmpeg_process.poll() is not None:
                    # Process finished
                    self.is_playing = False
                    break
                
                # Update position based on elapsed time plus start position
                elapsed = time.time() - start_time
                self.current_position = min(start_position + elapsed, self.total_duration)
                
                # Publish position update event
                try:
                    from ...events.player_events import PlayerPositionChangedEvent
                    from ...events import get_event_bus
                    get_event_bus().publish(PlayerPositionChangedEvent(
                        source="TAFPlayer._track_position_from_seek",
                        position=self.current_position
                    ))
                except Exception:
                    pass  # Don't break playback if event system fails
                
                # Check if we've reached the end
                if self.current_position >= self.total_duration:
                    # Only stop if we don't have a playlist (let playlist monitor handle it)
                    if not self.has_playlist():
                        self.is_playing = False
                        break
            
            time.sleep(0.1)  # Update every 100ms
        
        logger.debug("Position tracking from seek stopped")
    
    def pause(self) -> None:
        """Pause playback by stopping FFplay and storing position."""
        if not self.is_playing or self.is_paused:
            return
        
        try:
            # Store current position when pausing
            self.pause_position = self.current_position
            
            # Stop the FFplay process
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
                    self.ffmpeg_process.wait()
                self.ffmpeg_process = None
            
            # Stop the tracking thread
            if self.playback_thread and self.playback_thread.is_alive():
                self._stop_event.set()
                self.playback_thread.join(timeout=1)
                self._stop_event.clear()
            
            self.is_paused = True
            logger.info(f"Playback paused at position: {self.current_position:.2f}s")
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
    
    def resume(self) -> None:
        """Resume playback by restarting FFplay from pause position."""
        if not self.is_playing or not self.is_paused:
            return
        
        try:
            # Resume from stored pause position
            if hasattr(self, 'pause_position') and self.pause_position > 0:
                resume_position = self.pause_position
            else:
                resume_position = self.current_position
            
            # Start FFplay from pause position
            if not self.temp_audio_file:
                self.temp_audio_file = self._extract_audio_data()
            
            ffplay_binary = get_ffplay_binary()
            
            ffplay_cmd = [
                ffplay_binary,
                '-ss', str(resume_position),  # Start from pause position
                '-autoexit',
                '-nodisp',
                '-loglevel', 'quiet',
                str(self.temp_audio_file)
            ]
            
            logger.debug(f"Resuming FFplay: {' '.join(ffplay_cmd)}")
            
            self.ffmpeg_process = subprocess.Popen(
                ffplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.current_position = resume_position
            self.is_paused = False
            
            # Start position tracking thread from resume position
            self.playback_thread = threading.Thread(target=self._track_position_from_seek, args=(resume_position,))
            self.playback_thread.start()
            
            logger.info(f"Playback resumed from position: {resume_position:.2f}s")
        except Exception as e:
            logger.error(f"Failed to resume: {e}")
            self.is_paused = False  # Reset state on error
    
    def stop(self) -> None:
        """Stop playback forcefully - can always stop any playback."""
        logger.debug("Stop method called")
        
        # Always set these flags first to signal stopping
        was_playing = self.is_playing
        self.is_playing = False
        self.is_paused = False
        self._stop_event.set()
        
        # Cancel any pending volume updates
        if self._volume_update_timer:
            self._volume_update_timer.cancel()
            self._volume_update_timer = None
        
        # Force terminate any FFmpeg process
        if self.ffmpeg_process:
            try:
                logger.debug("Terminating FFmpeg process")
                self.ffmpeg_process.terminate()
                
                # Give it a moment to terminate gracefully
                try:
                    self.ffmpeg_process.wait(timeout=1.0)
                    logger.debug("FFmpeg process terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.debug("FFmpeg process didn't terminate gracefully, killing...")
                    self.ffmpeg_process.kill()
                    try:
                        self.ffmpeg_process.wait(timeout=1.0)
                        logger.debug("FFmpeg process killed")
                    except subprocess.TimeoutExpired:
                        logger.warning("FFmpeg process couldn't be killed")
                        # Force None anyway to prevent state inconsistency
                        
            except Exception as e:
                logger.error(f"Error terminating FFmpeg process: {e}")
            finally:
                # Always clear the process reference
                self.ffmpeg_process = None
        
        # Stop tracking thread
        if self.playback_thread and self.playback_thread.is_alive():
            try:
                logger.debug("Stopping playback thread")
                # Give thread time to see the stop event
                self.playback_thread.join(timeout=1.0)
                if self.playback_thread.is_alive():
                    logger.warning("Playbook thread didn't stop in time")
            except Exception as e:
                logger.error(f"Error stopping playbook thread: {e}")
        
        # Stop playlist monitoring
        self._stop_playlist_monitor()
        
        # Reset position
        self.current_position = 0.0
        
        # Small delay to ensure cleanup is complete before returning
        if was_playing:
            time.sleep(0.05)
        
        logger.info("Playback stopped")
    
    def _stop_playback_only(self) -> None:
        """Stop playback but keep playlist monitor alive for auto-advance."""
        logger.debug("Stopping playback only (keeping monitor alive)")
        
        # Set stopping flags
        self.is_playing = False
        self.is_paused = False
        self._stop_event.set()
        
        # Cancel any pending volume updates
        if self._volume_update_timer:
            self._volume_update_timer.cancel()
            self._volume_update_timer = None
        
        # Terminate FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
                    try:
                        self.ffmpeg_process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        pass
            except Exception as e:
                logger.error(f"Error terminating FFmpeg process: {e}")
            finally:
                self.ffmpeg_process = None
        
        # Stop tracking thread
        if self.playback_thread and self.playback_thread.is_alive():
            try:
                self.playback_thread.join(timeout=1.0)
            except Exception as e:
                logger.error(f"Error stopping playback thread: {e}")
        
        # Reset position
        self.current_position = 0.0
        
        logger.debug("Playback stopped (monitor still alive)")
    
    def _restart_playback_with_volume(self) -> None:
        """Restart playback with current volume settings."""
        if not self.is_playing:
            return
            
        try:
            # Store current state
            current_pos = self.current_position
            was_paused = self.is_paused
            
            logger.debug(f"Restarting playback with volume={self._volume}, muted={self._is_muted}")
            
            # Stop current playback
            self.stop()
            
            # Small delay to ensure cleanup
            time.sleep(0.1)
            
            # Restart playback
            self.play()
            
            # Seek back to the position if we were playing from a specific point
            if current_pos > 0.1:  # Only seek if we were significantly into the track
                self.seek(current_pos)
            
            # Restore pause state if needed
            if was_paused:
                self.pause()
                
        except Exception as e:
            logger.error(f"Failed to restart playback with volume: {e}")
    
    def _schedule_volume_update(self) -> None:
        """Schedule a debounced volume update to avoid frequent restarts."""
        # Cancel any existing timer
        if self._volume_update_timer:
            self._volume_update_timer.cancel()
        
        # Schedule new update after a short delay
        self._volume_update_timer = threading.Timer(0.3, self._apply_volume_update)
        self._volume_update_timer.start()
    
    def _apply_volume_update(self) -> None:
        """Apply the volume update by restarting playback."""
        try:
            logger.debug(f"Applying volume update: {self._volume}, muted: {self._is_muted}")
            self._restart_playback_with_volume()
        except Exception as e:
            logger.error(f"Failed to apply volume update: {e}")
        finally:
            self._volume_update_timer = None
    
    def seek(self, position: float) -> None:
        """
        Seek to a specific position in the audio.
        
        Args:
            position: Position in seconds to seek to
        """
        if position < 0 or position > self.total_duration:
            raise TAFPlayerError(f"Invalid seek position: {position}")
        
        was_playing = self.is_playing
        was_paused = self.is_paused
        
        # Always stop first to ensure clean state
        if was_playing:
            self.stop()
            # Give a moment for cleanup to complete
            time.sleep(0.1)
        
        # Update current position
        self.current_position = position
        
        # If stopped, save position for next play
        if not was_playing:
            self.pause_position = position
            logger.debug(f"Saved seek position for next play: {position:.2f}s")
        
        # If it was playing before, restart with new position
        if was_playing:
            # If it was paused, just update position and stay paused
            if was_paused:
                self.pause_position = position
                self.is_playing = True
                self.is_paused = True
                logger.info(f"Seeked to position while paused: {position:.2f}s")
            else:
                # Start new FFplay process with seek offset for active playback
                try:
                    if not self.temp_audio_file:
                        self.temp_audio_file = self._extract_audio_data()
                    
                    ffplay_binary = get_ffplay_binary()
                    
                    ffplay_cmd = [
                        ffplay_binary,
                        '-ss', str(position),  # Start from specific position
                        '-autoexit',
                        '-nodisp',
                        '-loglevel', 'quiet',
                    ]
                    
                    # Add volume filter if needed
                    effective_volume = 0.0 if self._is_muted else self._volume
                    if effective_volume != 1.0:
                        # Use audio filter to control volume
                        ffplay_cmd.extend(['-af', f'volume={effective_volume}'])
                    
                    ffplay_cmd.append(str(self.temp_audio_file))
                    
                    logger.debug(f"Seeking FFplay: {' '.join(ffplay_cmd)}")
                    
                    self.ffmpeg_process = subprocess.Popen(
                        ffplay_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    self.is_playing = True
                    self.is_paused = False
                    self._stop_event.clear()
                    
                    # Start position tracking thread
                    self.playback_thread = threading.Thread(target=self._track_position_from_seek, args=(position,))
                    self.playback_thread.start()
                    
                    # Restart playlist monitoring if needed
                    if self.has_playlist() and self._auto_advance:
                        self._start_playlist_monitor()
                    
                except Exception as e:
                    raise TAFPlayerError(f"Failed to seek: {e}")
        
        logger.info(f"Seeked to position: {position:.2f}s")
    
    def get_current_chapter(self) -> Optional[Dict[str, Any]]:
        """Get the current chapter based on playback position."""
        if not self.taf_info or not self.taf_info.get('chapters'):
            return None
        
        chapters = self.taf_info['chapters']
        
        for i, chapter in enumerate(chapters):
            chapter_start = chapter['start']
            
            # Check if this is the last chapter or if position is before next chapter
            if i == len(chapters) - 1:
                # Last chapter
                if self.current_position >= chapter_start:
                    return {'index': i, **chapter}
            else:
                next_chapter_start = chapters[i + 1]['start']
                if chapter_start <= self.current_position < next_chapter_start:
                    return {'index': i, **chapter}
        
        return None
    
    def previous_chapter(self) -> None:
        """Jump to the previous chapter."""
        if not self.taf_info or not self.taf_info.get('chapters'):
            logger.warning("No chapters available")
            return
        
        # Only allow chapter navigation if file is loaded
        if not self.is_loaded():
            logger.warning("No TAF file loaded")
            return
        
        current_chapter = self.get_current_chapter()
        if not current_chapter:
            # If no current chapter, go to first chapter or beginning
            if self.taf_info.get('chapters'):
                target_position = self.taf_info['chapters'][0]['start']
            else:
                target_position = 0.0
        else:
            current_index = current_chapter['index']
            
            # If we're more than 3 seconds into the current chapter, go to its start
            # Otherwise, go to the previous chapter
            chapter_start = current_chapter['start']
            if self.current_position - chapter_start > 3.0 and current_index >= 0:
                # Go to current chapter start
                target_position = chapter_start
            elif current_index > 0:
                # Go to previous chapter (current_index is already 0-based)
                prev_chapter = self.taf_info['chapters'][current_index - 1]
                target_position = prev_chapter['start']
            else:
                # Go to beginning of file
                target_position = 0.0
        
        # Only seek if we were playing, otherwise just update position
        if self.is_playing:
            self.seek(target_position)
        else:
            self.current_position = target_position
        
        logger.info(f"Jumped to previous chapter at position: {target_position:.2f}s")
    
    def next_chapter(self) -> None:
        """Jump to the next chapter."""
        if not self.taf_info or not self.taf_info.get('chapters'):
            logger.warning("No chapters available")
            return
        
        # Only allow chapter navigation if file is loaded
        if not self.is_loaded():
            logger.warning("No TAF file loaded")
            return
        
        chapters = self.taf_info['chapters']
        current_chapter = self.get_current_chapter()
        
        if not current_chapter:
            # If no current chapter, go to first chapter
            if self.taf_info.get('chapters'):
                target_position = self.taf_info['chapters'][0]['start']
            else:
                return
        else:
            current_index = current_chapter['index']
            
            if current_index < len(chapters) - 1:
                # Go to next chapter (current_index is already 0-based)
                next_chapter_info = chapters[current_index + 1]
                target_position = next_chapter_info['start']
            else:
                # Already at last chapter, do nothing
                logger.info(f"Already at last chapter ({current_index + 1} of {len(chapters)})")
                return
        
        # Only seek if we were playing, otherwise just update position
        if self.is_playing:
            self.seek(target_position)
        else:
            self.current_position = target_position
        
        logger.info(f"Jumped to next chapter at position: {target_position:.2f}s")
    
    def get_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the loaded TAF file."""
        return self.taf_info.copy() if self.taf_info else None
    
    def get_position(self) -> float:
        """Get current playback position in seconds."""
        return self.current_position
    
    def get_duration(self) -> float:
        """Get total duration in seconds."""
        return self.total_duration
    
    def is_loaded(self) -> bool:
        """Check if a TAF file is loaded."""
        return self.taf_file is not None
    
    def set_volume(self, volume: float) -> None:
        """
        Set playback volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        # Clamp volume to valid range
        volume = max(0.0, min(1.0, volume))
        old_volume = self._volume
        self._volume = volume
        
        # Automatically unmute if volume is set above 0
        if volume > 0.0 and self._is_muted:
            self._is_muted = False
            logger.debug(f"Auto-unmuted due to volume change: {volume}")
        
        logger.debug(f"TAF Player volume set to: {volume}")
        
        # If currently playing, restart playback with new volume (debounced)
        if self.is_playing and old_volume != volume:
            self._schedule_volume_update()
    
    def get_volume(self) -> float:
        """
        Get current playback volume.
        
        Returns:
            Current volume level (0.0 to 1.0)
        """
        return self._volume
    
    def set_muted(self, muted: bool) -> None:
        """
        Set mute state.
        
        Args:
            muted: Whether to mute audio
        """
        if muted == self._is_muted:
            return  # No change needed
            
        old_muted = self._is_muted
        self._is_muted = muted
        
        if muted:
            # Store current volume before muting
            if self._volume > 0.0:
                self._volume_before_mute = self._volume
            logger.debug(f"TAF Player muted - stored volume: {self._volume_before_mute}")
        else:
            # Restore volume when unmuting
            if self._volume_before_mute > 0.0:
                self._volume = self._volume_before_mute
            logger.debug(f"TAF Player unmuted - restored volume: {self._volume}")
        
        # If currently playing, restart playback with new mute state (debounced)
        if self.is_playing and old_muted != muted:
            self._schedule_volume_update()
    
    def is_muted(self) -> bool:
        """
        Get current mute state.
        
        Returns:
            Whether audio is muted
        """
        return self._is_muted
    
    # ========== Playlist Functionality ==========
    
    def load_playlist_from_path(self, input_path: str, recursive: bool = False) -> bool:
        """
        Load playlist from path (file, directory, or pattern).
        
        Args:
            input_path: Path to load playlist from
            recursive: Whether to search recursively
            
        Returns:
            True if playlist was loaded successfully
        """
        self._ensure_playlist_manager()
        success = self.playlist_manager.load_from_path(input_path, recursive)
        if success:
            self._load_current_track_from_playlist()
        return success
    
    def load_playlist_from_multiple_paths(self, input_paths: List[str]) -> bool:
        """
        Load playlist from multiple paths.
        
        Args:
            input_paths: List of paths to load from
            
        Returns:
            True if playlist was loaded successfully
        """
        self._ensure_playlist_manager()
        success = self.playlist_manager.load_from_multiple_paths(input_paths)
        if success:
            self._load_current_track_from_playlist()
        return success
    
    def next_track(self) -> bool:
        """
        Move to next track in playlist and start playing if currently playing.
        
        Returns:
            True if advanced to next track, False if no next track available
        """
        logger.debug(f"next_track called, playlist_manager exists: {self.playlist_manager is not None}")
        if not self.playlist_manager:
            logger.debug("No playlist manager available")
            return False
            
        was_playing = self.is_playing
        logger.debug(f"Was playing: {was_playing}")
        
        if was_playing:
            logger.debug("Stopping current track")
            self._stop_playback_only()  # Stop playback but keep monitor alive
        
        logger.debug("Calling playlist_manager.next_item()")
        next_item = self.playlist_manager.next_item()
        logger.debug(f"Next item: {next_item}")
        if next_item:
            logger.debug(f"Loading next track: {next_item.file_path}")
            self._load_current_track_from_playlist()
            if was_playing:
                logger.debug("Resuming playback")
                self.play()
            
            # Publish file loaded event after play() so is_playing state is correct for GUI
            try:
                from ...analysis import analyze_taf_file
                from ...events.player_events import PlayerFileLoadedEvent
                from ...events import get_event_bus
                
                analysis_result = analyze_taf_file(next_item.file_path)
                if analysis_result:
                    event_bus = get_event_bus()
                    event_bus.publish(PlayerFileLoadedEvent(
                        source="TAFPlayer.next_track",
                        file_path=str(next_item.file_path),
                        analysis_result=analysis_result
                    ))
                    logger.debug(f"Published PlayerFileLoadedEvent for {next_item.file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to publish file loaded event: {e}")
            
            self._notify_track_changed(next_item)
            logger.debug("Successfully moved to next track")
            return True
        
        logger.debug("No next track available")
        return False
    
    def previous_track(self) -> bool:
        """
        Move to previous track in playlist and start playing if currently playing.
        
        Returns:
            True if moved to previous track, False if no previous track available
        """
        if not self.playlist_manager:
            return False
            
        was_playing = self.is_playing
        
        if was_playing:
            self._stop_playback_only()  # Stop playback but keep monitor alive
        
        prev_item = self.playlist_manager.previous_item()
        if prev_item:
            self._load_current_track_from_playlist()
            if was_playing:
                self.play()
            
            # Publish file loaded event after play() so is_playing state is correct for GUI
            try:
                from ...analysis import analyze_taf_file
                from ...events.player_events import PlayerFileLoadedEvent
                from ...events import get_event_bus
                
                analysis_result = analyze_taf_file(prev_item.file_path)
                if analysis_result:
                    event_bus = get_event_bus()
                    event_bus.publish(PlayerFileLoadedEvent(
                        source="TAFPlayer.previous_track",
                        file_path=str(prev_item.file_path),
                        analysis_result=analysis_result
                    ))
                    logger.debug(f"Published PlayerFileLoadedEvent for {prev_item.file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to publish file loaded event: {e}")
            
            self._notify_track_changed(prev_item)
            return True
        
        logger.debug("No previous track available")
        return False
    
    def jump_to_track(self, index: int) -> bool:
        """
        Jump to specific track in playlist.
        
        Args:
            index: Index of track to jump to
            
        Returns:
            True if jumped successfully, False otherwise
        """
        if not self.playlist_manager:
            return False
            
        was_playing = self.is_playing
        
        if was_playing:
            self.stop()
        
        item = self.playlist_manager.jump_to_item(index)
        if item:
            self._load_current_track_from_playlist()
            if was_playing:
                self.play()
            self._notify_track_changed(item)
            return True
        
        return False
    
    def has_playlist(self) -> bool:
        """Check if player has a playlist loaded."""
        return self.playlist_manager is not None and not self.playlist_manager.is_empty()
    
    def is_single_file_mode(self) -> bool:
        """Check if player is in single file mode (no playlist or playlist with one item)."""
        return not self.has_playlist() or self.playlist_manager.is_single_file_mode()

    def get_status(self) -> Dict[str, Any]:
        """Get current player status information."""
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'volume': self.get_volume(),
            'position': self.current_position,
            'duration': self.total_duration,
            'current_file': str(self.taf_file) if self.taf_file else None,
            'file_loaded': self.taf_file is not None
        }

    def get_playlist_info(self) -> Dict[str, Any]:
        """Get information about the current playlist."""
        if not self.playlist_manager:
            return {
                'has_playlist': False,
                'current_file': str(self.taf_file) if self.taf_file else None
            }
        
        playlist_info = self.playlist_manager.get_playlist_info()
        player_status = self.get_status()
        
        return {
            **playlist_info,
            'has_playlist': True,
            'player_status': player_status,
            'auto_advance': self._auto_advance
        }
    
    def set_auto_advance(self, enabled: bool) -> None:
        """Enable or disable automatic advancement to next track."""
        self._auto_advance = enabled
        logger.debug(f"Auto-advance: {'enabled' if enabled else 'disabled'}")
    
    def is_auto_advance_enabled(self) -> bool:
        """Check if auto-advance is enabled."""
        return self._auto_advance
    
    def add_track_end_callback(self, callback: Callable) -> None:
        """Add callback to be called when a track ends."""
        self._track_end_callbacks.append(callback)
    
    def add_track_changed_callback(self, callback: Callable) -> None:
        """Add callback to be called when track changes."""
        self._track_changed_callbacks.append(callback)
    
    def _ensure_playlist_manager(self) -> None:
        """Ensure playlist manager is initialized."""
        if self.playlist_manager is None:
            from ..playlist import PlaylistManager
            logger.debug(f"Creating PlaylistManager in _ensure_playlist_manager")
            self.playlist_manager = PlaylistManager()
            logger.debug(f"PlaylistManager created: {self.playlist_manager is not None}, type: {type(self.playlist_manager)}")
            self.playlist_manager.add_current_item_changed_callback(self._on_playlist_item_changed)
            logger.debug(f"Callback added to PlaylistManager")
        else:
            logger.debug(f"PlaylistManager already exists: {type(self.playlist_manager)}")
    
    def _load_current_track_from_playlist(self) -> None:
        """Load the current playlist item into the player."""
        if not self.playlist_manager:
            return
            
        current_item = self.playlist_manager.get_current_item()
        if not current_item:
            return
        
        try:
            self.load(str(current_item.file_path))
            
            # Update playlist item with extracted metadata
            if self.taf_info:
                current_item.duration = self.total_duration
                if not current_item.title or current_item.title == current_item.file_path.stem:
                    current_item.title = current_item.file_path.stem
                current_item.metadata = self.taf_info.copy()
            
            logger.debug(f"Loaded playlist track: {current_item.title}")
            
        except Exception as e:
            logger.error(f"Failed to load playlist track: {e}")
            raise TAFPlayerError(f"Failed to load playlist track: {e}")
    
    def _on_playlist_item_changed(self) -> None:
        """Handle playlist item change from playlist manager."""
        # This is called when playlist manager changes current item
        # The actual loading is handled by the navigation methods
        pass
    
    def _notify_track_changed(self, item) -> None:
        """Notify callbacks that the current track has changed."""
        for callback in self._track_changed_callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"Error in track changed callback: {e}")
    
    def _start_playlist_monitor(self) -> None:
        """Start monitoring playback for playlist auto-advance."""
        if self._playback_monitor_thread and self._playback_monitor_thread.is_alive():
            return
        
        self._stop_monitor.clear()
        self._playback_monitor_thread = threading.Thread(
            target=self._playlist_monitor_worker,
            daemon=True
        )
        self._playback_monitor_thread.start()
        logger.debug("Started playlist monitor")
    
    def _stop_playlist_monitor(self) -> None:
        """Stop the playlist monitor."""
        self._stop_monitor.set()
        # Only join if not called from within the monitor thread itself
        if (self._playback_monitor_thread and self._playback_monitor_thread.is_alive() and 
            threading.current_thread() != self._playback_monitor_thread):
            self._playback_monitor_thread.join(timeout=2)
        logger.debug("Stopped playlist monitor")
    
    def _playlist_monitor_worker(self) -> None:
        """Monitor playback and handle auto-advance to next track."""
        while not self._stop_monitor.is_set():
            try:
                if self.is_playing and not self.is_paused:
                    # Check if track has finished (with small buffer for timing issues)
                    if (self.total_duration > 0 and 
                        self.current_position >= self.total_duration - 0.5):
                        
                        logger.info(f"AUTO-ADVANCE: Track finished - Position: {self.current_position:.2f}/{self.total_duration:.2f}")
                        self._handle_track_end()
                        # Continue monitoring for the next track instead of breaking
                        # Reset position check to avoid immediate re-trigger
                        self._stop_monitor.wait(1.0)
                        continue
                
                # Check every 0.5 seconds
                self._stop_monitor.wait(0.5)
                
            except Exception as e:
                logger.error(f"Error in playlist monitor: {e}")
                break
    
    def _handle_track_end(self) -> None:
        """Handle end of current track in playlist."""
        if not self.playlist_manager:
            return
            
        current_item = self.playlist_manager.get_current_item()
        if current_item:
            self._notify_track_end(current_item)
        
        if self._auto_advance and self.playlist_manager.has_next():
            logger.info("AUTO-ADVANCE: Moving to next track")
            self.next_track()
        else:
            logger.info("AUTO-ADVANCE: Playlist finished - no auto-advance or no next track")
            self.stop()
    
    def _notify_track_end(self, item) -> None:
        """Notify callbacks that a track has ended."""
        for callback in self._track_end_callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"Error in track end callback: {e}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop()
        
        # Cancel any pending volume updates
        if self._volume_update_timer:
            self._volume_update_timer.cancel()
            self._volume_update_timer = None
        
        if self.temp_audio_file and self.temp_audio_file.exists():
            try:
                self.temp_audio_file.unlink()
                logger.debug(f"Cleaned up temporary file: {self.temp_audio_file}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary file: {e}")
        
        self.temp_audio_file = None
        self.taf_file = None
        self.taf_info = None
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()