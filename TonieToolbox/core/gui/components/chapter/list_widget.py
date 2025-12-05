#!/usr/bin/env python3
"""
Chapter list widget for displaying and managing audio file chapters.
"""

from typing import Optional, List, Callable, Dict, Any
from pathlib import Path

try:
    from PyQt6.QtWidgets import (QListWidget, QListWidgetItem, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QFrame,
                                QAbstractItemView, QMenu, QSizePolicy)
    from PyQt6.QtCore import pyqtSignal, Qt, QTimer
    from PyQt6.QtGui import QFont, QAction, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    # Mock classes for when PyQt6 is not available
    QListWidget = object
    QListWidgetItem = object
    QVBoxLayout = object
    QHBoxLayout = object
    QLabel = object 
    QPushButton = object
    QFrame = object
    QAbstractItemView = object
    QMenu = object
    QSizePolicy = object
    pyqtSignal = lambda: None
    Qt = object
    QTimer = object
    QAction = object
    QFont = object

from ..base.component import QtBaseFrame
from ....utils import get_logger

logger = get_logger(__name__)


class ChapterWidget(QtBaseFrame):
    """Widget for displaying and navigating audio file chapters."""
    
    # Signals
    chapter_selected = pyqtSignal(int)  # chapter_index
    chapter_double_clicked = pyqtSignal(int)  # chapter_index
    
    def __init__(self, player_controller=None, **kwargs):
        """Initialize chapter widget."""
        self.player_controller = player_controller
        self.chapter_list = None
        self.header_label = None
        
        # Chapter data
        self.chapters: List[Dict[str, Any]] = []
        self.current_chapter_index: int = -1
        self.current_player_state: str = "stopped"
        
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        theme_manager = kwargs.pop('theme_manager', None)
        
        super().__init__(translation_manager=translation_manager, **kwargs)
    
    def _create_layout(self):
        """Create the main layout for the chapter widget."""
        if not PYQT6_AVAILABLE:
            return
        # Call parent to create the layout first
        super()._create_layout()
        # Then customize the layout
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        
    def _setup_ui(self):
        """Create the chapter widget UI."""
        if not PYQT6_AVAILABLE:
            return
        
        # Header label
        self.header_label = QLabel(self.tr("chapters", "title"))
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self.header_label.setFont(font)
        self.main_layout.addWidget(self.header_label)
        
        # Chapter list
        self.chapter_list = QListWidget()
        self.chapter_list.setAlternatingRowColors(True)
        self.chapter_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.main_layout.addWidget(self.chapter_list)
        
        # Connect signals
        self.chapter_list.itemClicked.connect(self._on_item_clicked)
        self.chapter_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Set initial state
        self._update_header()
        
        logger.debug("Chapter widget UI created")
    
    def set_player_controller(self, controller):
        """Set the player controller reference."""
        self.player_controller = controller
        logger.debug(f"Chapter widget: player controller set to {type(controller)}")
        
    def load_chapters(self, chapters: List[Dict[str, Any]]):
        """
        Load chapters into the widget.
        
        Args:
            chapters: List of chapter dictionaries with keys: index, title, start, duration
        """
        if not PYQT6_AVAILABLE:
            return
            
        self.chapters = chapters or []
        self.current_chapter_index = -1
        
        # Clear existing items
        self.chapter_list.clear()
        
        # Add chapters to list
        for chapter in self.chapters:
            item = self._create_chapter_item(chapter)
            self.chapter_list.addItem(item)
        
        self._update_header()
        logger.debug(f"Loaded {len(self.chapters)} chapters into chapter widget")
    
    def _create_chapter_item(self, chapter: Dict[str, Any]) -> QListWidgetItem:
        """Create a list widget item for a chapter."""
        if not PYQT6_AVAILABLE:
            return None
            
        # Format chapter info
        index = chapter.get('index', 0)
        title = chapter.get('title', f'Chapter {index + 1}')
        start_time = chapter.get('start', 0.0)
        duration = chapter.get('duration', 0.0)
        
        # Calculate end time
        end_time = start_time + duration
        
        # Format times in HH:MM:SS format
        start_str = self._format_time(start_time)
        end_str = self._format_time(end_time)
        duration_str = self._format_time(duration)
        
        # Create item text with start - end time and duration in brackets
        item_text = f"{index + 1:2}. {title} ({start_str} - {end_str}) [{duration_str}]"
        
        # Create list item
        item = QListWidgetItem(item_text)
        
        # Store chapter data
        item.setData(Qt.ItemDataRole.UserRole, {
            'chapter_index': index,
            'chapter_data': chapter
        })
        
        return item
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to HH:MM:SS format."""
        if seconds < 0:
            seconds = 0
            
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def _update_header(self):
        """Update the header label with chapter count."""
        if not PYQT6_AVAILABLE or not self.header_label:
            return
            
        count = len(self.chapters)
        if count == 0:
            self.header_label.setText(self.tr("chapters", "title"))
        elif count == 1:
            self.header_label.setText(self.tr("chapters", "single_chapter"))
        else:
            self.header_label.setText(f"{self.tr('chapters', 'title')} ({count} chapters)")
    
    def set_current_chapter(self, chapter_index: int, player_state: str = "stopped"):
        """
        Highlight the currently playing chapter with appropriate visual indicators.
        
        Args:
            chapter_index: Index of the currently playing chapter
            player_state: Current player state ("playing", "paused", "stopped", "loading")
        """
        if not PYQT6_AVAILABLE:
            return
            
        # Clear previous highlighting
        for i in range(self.chapter_list.count()):
            item = self.chapter_list.item(i)
            if item:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
                # Reset background color
                item.setBackground(self.palette().base())
        
        # Highlight current chapter
        if 0 <= chapter_index < self.chapter_list.count():
            item = self.chapter_list.item(chapter_index)
            if item:
                # Set bold font
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
                # Set background color based on player state
                if player_state == "playing":
                    # Green tint for playing
                    item.setBackground(QColor(144, 238, 144, 80))  # Light green with alpha
                elif player_state == "paused":
                    # Yellow tint for paused
                    item.setBackground(QColor(255, 255, 144, 80))  # Light yellow with alpha
                elif player_state == "loading":
                    # Blue tint for loading
                    item.setBackground(QColor(173, 216, 230, 80))  # Light blue with alpha
                else:  # stopped
                    # Gray tint for stopped/loaded
                    item.setBackground(QColor(211, 211, 211, 80))  # Light gray with alpha
                
                # Scroll to current chapter
                self.chapter_list.scrollToItem(item)
                
                self.current_chapter_index = chapter_index
                logger.debug(f"Highlighted current chapter: {chapter_index} (state: {player_state})")
        
        # Update the current state for refresh
        self.current_player_state = player_state
    
    def update_player_state(self, player_state: str):
        """
        Update the visual state for the current chapter based on player state.
        
        Args:
            player_state: Current player state ("playing", "paused", "stopped", "loading")
        """
        if not PYQT6_AVAILABLE:
            return
            
        self.current_player_state = player_state
        # Refresh the highlighting with the new state
        if self.current_chapter_index >= 0:
            self.set_current_chapter(self.current_chapter_index, player_state)
            logger.debug(f"Updated chapter player state visual indicator: {player_state}")
    
    def clear_chapters(self):
        """Clear all chapters from the widget."""
        if not PYQT6_AVAILABLE:
            return
            
        self.chapters = []
        self.current_chapter_index = -1
        self.chapter_list.clear()
        self._update_header()
        logger.debug("Cleared all chapters from chapter widget")
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle chapter item clicked."""
        if not PYQT6_AVAILABLE or not item:
            return
            
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and 'chapter_index' in data:
            chapter_index = data['chapter_index']
            self.chapter_selected.emit(chapter_index)
            logger.debug(f"Chapter selected: {chapter_index}")
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle chapter item double-clicked."""
        if not PYQT6_AVAILABLE or not item:
            return
            
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and 'chapter_index' in data:
            chapter_index = data['chapter_index']
            self.chapter_double_clicked.emit(chapter_index)
            logger.debug(f"Chapter double-clicked: {chapter_index}")
    
    def get_chapter_count(self) -> int:
        """Get the number of chapters."""
        return len(self.chapters)
    
    def get_current_chapter_index(self) -> int:
        """Get the current chapter index."""
        return self.current_chapter_index
    
    def get_chapter_at_position(self, position: float) -> int:
        """
        Get the chapter index for a given playback position.
        
        Args:
            position: Current playback position in seconds
            
        Returns:
            Chapter index, or -1 if no chapter found
        """
        if not self.chapters:
            return -1
            
        # Find the chapter that contains this position
        for i, chapter in enumerate(self.chapters):
            start_time = chapter.get('start', 0.0)
            duration = chapter.get('duration', 0.0)
            end_time = start_time + duration
            
            # Check if position is within this chapter
            if start_time <= position < end_time:
                return i
                
        # If position is beyond all chapters, return the last chapter
        if position >= 0 and self.chapters:
            return len(self.chapters) - 1
            
        return -1
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        if not PYQT6_AVAILABLE:
            return
        
        # Update header based on current chapter count
        count = self.chapter_list.count()
        if count == 0:
            self.header_label.setText(self.tr("chapters", "title"))
        elif count == 1:
            self.header_label.setText(self.tr("chapters", "single_chapter"))
        else:
            self.header_label.setText(f"{self.tr('chapters', 'title')} ({count} chapters)")
        
        logger.debug("Chapter list retranslated")