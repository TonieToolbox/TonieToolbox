#!/usr/bin/env python3
"""
Playlist models for TonieToolbox media player.
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from ...utils import get_logger

logger = get_logger(__name__)


class RepeatMode(Enum):
    """Playlist repeat modes."""
    OFF = "off"
    ALL = "all" 
    ONE = "one"


@dataclass
class PlaylistItem:
    """Represents a single item in a playlist."""
    file_path: Path
    title: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.title is None:
            self.title = self.file_path.stem
        if self.file_size == 0 and self.file_path.exists():
            self.file_size = self.file_path.stat().st_size
        if self.metadata is None:
            self.metadata = {}


class Playlist:
    """
    Manages a playlist of TAF files.
    
    Provides functionality for managing playback order, including support for
    shuffle and repeat modes while maintaining the original order.
    """
    
    def __init__(self):
        """Initialize empty playlist."""
        self.items: List[PlaylistItem] = []
        self.current_index: int = -1
        self.shuffle_mode: bool = False
        self.repeat_mode: RepeatMode = RepeatMode.OFF
        self.shuffle_history: List[int] = []
        self._original_order: List[int] = []
    
    def add_item(self, item: PlaylistItem) -> None:
        """Add an item to the playlist."""
        self.items.append(item)
        self._update_original_order()
        logger.debug(f"Added playlist item: {item.title}")
    
    def add_file(self, file_path: Path) -> PlaylistItem:
        """Add a TAF file to the playlist."""
        item = PlaylistItem(file_path=file_path)
        self.add_item(item)
        return item
    
    def remove_item(self, index: int) -> bool:
        """Remove an item from the playlist by index."""
        if 0 <= index < len(self.items):
            removed_item = self.items.pop(index)
            self._update_original_order()
            # Adjust current index if necessary
            if self.current_index >= index:
                self.current_index = max(-1, self.current_index - 1)
            logger.debug(f"Removed playlist item: {removed_item.title}")
            return True
        return False
    
    def move_item(self, from_index: int, to_index: int) -> bool:
        """Move an item from one position to another."""
        logger.debug(f"move_item called: from_index={from_index}, to_index={to_index}")
        logger.debug(f"Playlist items before move: {[item.title for item in self.items]}")
        logger.debug(f"Current index before move: {self.current_index}")
        
        if (0 <= from_index < len(self.items) and 
            0 <= to_index < len(self.items) and 
            from_index != to_index):
            
            # Move the item
            item = self.items.pop(from_index)
            logger.debug(f"Popped item '{item.title}' from index {from_index}")
            self.items.insert(to_index, item)
            logger.debug(f"Inserted item '{item.title}' at index {to_index}")
            logger.debug(f"Playlist items after move: {[item.title for item in self.items]}")
            
            # Update current index if necessary
            old_current_index = self.current_index
            if self.current_index == from_index:
                self.current_index = to_index
            elif from_index < self.current_index <= to_index:
                self.current_index -= 1
            elif to_index <= self.current_index < from_index:
                self.current_index += 1
            
            if old_current_index != self.current_index:
                logger.debug(f"Updated current_index from {old_current_index} to {self.current_index}")
            
            self._update_original_order()
            logger.debug(f"Moved playlist item from {from_index} to {to_index}: {item.title}")
            return True
        else:
            logger.debug(f"Move rejected - invalid indices or same position")
            return False
    
    def clear(self) -> None:
        """Clear all items from the playlist."""
        self.items.clear()
        self.current_index = -1
        self.shuffle_history.clear()
        self._original_order.clear()
        logger.debug("Playlist cleared")
    
    def get_current_item(self) -> Optional[PlaylistItem]:
        """Get the currently selected playlist item."""
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None
    
    def get_next_item(self) -> Optional[PlaylistItem]:
        """Get the next item to play based on current mode."""
        if not self.items:
            return None
        
        if self.shuffle_mode:
            return self._get_next_shuffled_item()
        else:
            return self._get_next_sequential_item()
    
    def get_previous_item(self) -> Optional[PlaylistItem]:
        """Get the previous item based on current mode."""
        if not self.items:
            return None
            
        if self.shuffle_mode:
            return self._get_previous_shuffled_item()
        else:
            return self._get_previous_sequential_item()
    
    def jump_to_item(self, index: int) -> Optional[PlaylistItem]:
        """Jump to a specific item in the playlist."""
        if 0 <= index < len(self.items):
            self.current_index = index
            if self.shuffle_mode:
                # Add to shuffle history if jumping manually
                if index not in self.shuffle_history:
                    self.shuffle_history.append(index)
            return self.items[index]
        return None
    
    def set_shuffle_mode(self, enabled: bool) -> None:
        """Enable or disable shuffle mode."""
        if self.shuffle_mode != enabled:
            self.shuffle_mode = enabled
            if enabled:
                self.shuffle_history.clear()
                if self.current_index >= 0:
                    self.shuffle_history.append(self.current_index)
            logger.debug(f"Shuffle mode: {'enabled' if enabled else 'disabled'}")
    
    def set_repeat_mode(self, mode: RepeatMode) -> None:
        """Set the repeat mode."""
        self.repeat_mode = mode
        logger.debug(f"Repeat mode set to: {mode.value}")
    
    def has_next(self) -> bool:
        """Check if there's a next item available."""
        if not self.items:
            return False
            
        if self.repeat_mode == RepeatMode.ONE:
            return True
        elif self.repeat_mode == RepeatMode.ALL:
            return True
        else:
            # RepeatMode.OFF
            if self.shuffle_mode:
                return len(self.shuffle_history) < len(self.items)
            else:
                return self.current_index < len(self.items) - 1
    
    def has_previous(self) -> bool:
        """Check if there's a previous item available."""
        if not self.items:
            return False
            
        if self.repeat_mode == RepeatMode.ONE:
            return True
        elif self.repeat_mode == RepeatMode.ALL:
            return True
        else:
            # RepeatMode.OFF
            if self.shuffle_mode:
                return len(self.shuffle_history) > 1
            else:
                return self.current_index > 0
    
    def is_empty(self) -> bool:
        """Check if playlist is empty."""
        return len(self.items) == 0
    
    def size(self) -> int:
        """Get the number of items in the playlist."""
        return len(self.items)
    
    def get_total_duration(self) -> float:
        """Get the total duration of all items in the playlist."""
        return sum(item.duration for item in self.items)
    
    def _update_original_order(self) -> None:
        """Update the original order tracking."""
        self._original_order = list(range(len(self.items)))
    
    def _get_next_sequential_item(self) -> Optional[PlaylistItem]:
        """Get next item in sequential order."""
        if self.repeat_mode == RepeatMode.ONE:
            return self.get_current_item()
        
        next_index = self.current_index + 1
        
        if next_index >= len(self.items):
            if self.repeat_mode == RepeatMode.ALL:
                next_index = 0
            else:
                return None  # End of playlist
        
        self.current_index = next_index
        return self.items[self.current_index]
    
    def _get_previous_sequential_item(self) -> Optional[PlaylistItem]:
        """Get previous item in sequential order."""
        if self.repeat_mode == RepeatMode.ONE:
            return self.get_current_item()
        
        prev_index = self.current_index - 1
        
        if prev_index < 0:
            if self.repeat_mode == RepeatMode.ALL:
                prev_index = len(self.items) - 1
            else:
                return None  # Beginning of playlist
        
        self.current_index = prev_index
        return self.items[self.current_index]
    
    def _get_next_shuffled_item(self) -> Optional[PlaylistItem]:
        """Get next item in shuffle mode."""
        import random
        
        if self.repeat_mode == RepeatMode.ONE:
            return self.get_current_item()
        
        # If we've played all tracks
        if len(self.shuffle_history) >= len(self.items):
            if self.repeat_mode == RepeatMode.ALL:
                # Restart shuffle with new random order
                self.shuffle_history.clear()
                if self.current_index >= 0:
                    self.shuffle_history.append(self.current_index)
            else:
                return None  # End of playlist
        
        # Get unplayed indices
        unplayed = [i for i in range(len(self.items)) if i not in self.shuffle_history]
        
        if not unplayed:
            return None
        
        # Pick random unplayed track
        next_index = random.choice(unplayed)
        self.current_index = next_index
        self.shuffle_history.append(next_index)
        
        return self.items[self.current_index]
    
    def _get_previous_shuffled_item(self) -> Optional[PlaylistItem]:
        """Get previous item in shuffle mode."""
        if self.repeat_mode == RepeatMode.ONE:
            return self.get_current_item()
        
        if len(self.shuffle_history) <= 1:
            if self.repeat_mode == RepeatMode.ALL:
                # Go to random track at end
                import random
                self.current_index = random.randint(0, len(self.items) - 1)
                self.shuffle_history = [self.current_index]
            else:
                return None  # Beginning of playlist
        else:
            # Remove current track and go to previous in history
            if self.shuffle_history:
                self.shuffle_history.pop()
            if self.shuffle_history:
                self.current_index = self.shuffle_history[-1]
            else:
                self.current_index = -1
                return None
        
        return self.items[self.current_index] if self.current_index >= 0 else None
    
    def __len__(self) -> int:
        """Get the number of items in the playlist."""
        return len(self.items)
    
    def __bool__(self) -> bool:
        """Check if playlist has items."""
        return len(self.items) > 0
    
    def __iter__(self):
        """Iterate over playlist items."""
        return iter(self.items)
    
    def __getitem__(self, index) -> PlaylistItem:
        """Get item by index."""
        return self.items[index]