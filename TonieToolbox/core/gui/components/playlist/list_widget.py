#!/usr/bin/env python3
"""
Playlist list widget for displaying and managing playlist tracks.
"""

from typing import Optional, List, Callable
from pathlib import Path

try:
    from PyQt6.QtWidgets import (QListWidget, QListWidgetItem, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QFrame,
                                QAbstractItemView, QMenu, QSizePolicy)
    from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QMimeData, QModelIndex
    from PyQt6.QtGui import QFont, QDrag, QAction, QDropEvent, QColor
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
    QMimeData = object
    QDrag = object
    QAction = object
    QFont = object
    QModelIndex = object
    QDropEvent = object

from ..base.component import QtBaseFrame
from ....utils import get_logger

logger = get_logger(__name__)


class DragDropListWidget(QListWidget):
    """Custom list widget that properly handles drag-and-drop reordering."""
    
    # Signal emitted when items are reordered via drag-and-drop
    items_reordered = pyqtSignal(int, int)  # from_index, to_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._original_order = []
    
    def store_order(self):
        """Store the current order of items before drag operation."""
        if not PYQT6_AVAILABLE:
            return
            
        self._original_order = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    self._original_order.append(data.get('index', i))
        logger.debug(f"Stored original order: {self._original_order}")
    
    def check_reorder(self):
        """Check if items have been reordered and emit signal if so."""
        if not PYQT6_AVAILABLE:
            return
            
        new_order = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    new_order.append(data.get('index', i))
        
        logger.debug(f"New order: {new_order}")
        
        # Find what moved
        if len(new_order) == len(self._original_order) and new_order != self._original_order:
            # Find the item that moved the farthest distance - this is the dragged item
            max_distance = 0
            moved_item_original_idx = None
            moved_item_new_idx = None
            
            # Calculate the move distance for each item
            for original_pos, original_item in enumerate(self._original_order):
                current_pos = new_order.index(original_item) if original_item in new_order else -1
                if current_pos != -1:
                    distance = abs(current_pos - original_pos)
                    if distance > max_distance:
                        max_distance = distance
                        moved_item_original_idx = original_pos
                        moved_item_new_idx = current_pos
            
            if moved_item_original_idx is not None and moved_item_new_idx is not None:
                # For Qt drag-and-drop, the visual position in the list IS the correct target index
                # No adjustment needed - what we see is what we want
                actual_target_index = moved_item_new_idx
                
                logger.debug(f"Tracks reordered: {moved_item_original_idx} -> {actual_target_index}")
                self.items_reordered.emit(moved_item_original_idx, actual_target_index)
                logger.debug(f"Drag-drop reordered: {moved_item_original_idx} -> {actual_target_index}")
            else:
                logger.debug("Could not determine moved item")
    
    def mousePressEvent(self, event):
        """Store order when mouse press starts (potential drag start)."""
        self.store_order()
        super().mousePressEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events to track item reordering."""
        if not PYQT6_AVAILABLE:
            return
        
        # Let the default drop handling happen first
        super().dropEvent(event)
        
        # Check if order changed after drop
        self.check_reorder()


class PlaylistWidget(QtBaseFrame):
    """
    Widget for displaying and managing playlist tracks.
    Shows track list, current playing track, and provides drag-drop reordering.
    """
    
    # Signals
    track_selected = pyqtSignal(int)  # Track index selected
    track_moved = pyqtSignal(int)  # Track moved to new position
    track_double_clicked = pyqtSignal(int)  # Track double-clicked (play)
    remove_track_requested = pyqtSignal(int)  # Remove track at index
    remove_tracks_requested = pyqtSignal(list)  # Remove multiple tracks at indices
    move_track_requested = pyqtSignal(int, int)  # Move track from old_index to new_index
    clear_playlist_requested = pyqtSignal()
    add_files_requested = pyqtSignal()  # Add files/folders to playlist
    
    def __init__(self, parent=None, player_controller=None, **kwargs):
        """
        Initialize playlist widget.
        
        Args:
            parent: Parent widget
            player_controller: Reference to player controller for playlist operations
            **kwargs: Additional configuration
        """
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        theme_manager = kwargs.pop('theme_manager', None)
        
        super().__init__(parent, translation_manager=translation_manager, **kwargs)
        
        if not PYQT6_AVAILABLE:
            return
            
        self.player_controller = player_controller
        self.current_track_index = -1
        self.current_player_state = "stopped"
        
        # Set unique object name to avoid Qt auto-numbering
        self.setObjectName(f"playlist_widget_{id(self)}")
        
        logger.debug("Playlist widget initialized")
    
    def _connect_signals(self):
        """Connect signals and slots."""
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup the user interface."""
        if not PYQT6_AVAILABLE:
            return
        
        # Create content frame (similar to PlayerInfoPanel pattern)
        content_frame = QFrame()
        layout = QVBoxLayout(content_frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header with title and controls
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title label
        self.title_label = QLabel(self.tr("playlist", "title"))
        self.title_label.setObjectName(f"playlist_track_list_title_{id(self)}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Add Files button
        self.add_files_button = QPushButton(self.tr("playlist", "buttons", "add_files"))
        self.add_files_button.setMinimumHeight(30)
        self.add_files_button.setToolTip(self.tr("playlist", "buttons", "add_files_tooltip"))
        header_layout.addWidget(self.add_files_button)
        
        # Remove selected button
        self.remove_button = QPushButton(self.tr("playlist", "buttons", "remove"))
        self.remove_button.setMaximumWidth(70)
        self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_tooltip"))
        self.remove_button.setEnabled(False)  # Disabled until tracks are selected
        header_layout.addWidget(self.remove_button)
        
        # Clear playlist button
        self.clear_button = QPushButton(self.tr("playlist", "buttons", "clear"))
        self.clear_button.setMaximumWidth(60)
        self.clear_button.setToolTip(self.tr("playlist", "buttons", "clear_tooltip"))
        header_layout.addWidget(self.clear_button)
        
        layout.addWidget(header_frame)
        
        # Playlist list widget with drag-drop support
        self.track_list = DragDropListWidget()
        self.track_list.setAlternatingRowColors(True)
        self.track_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # Enable multi-select
        
        layout.addWidget(self.track_list)
        
        # Status label
        self.status_label = QLabel(self.tr("playlist", "status", "no_playlist"))
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Add content frame to main layout (from QtBaseFrame)
        self.main_layout.addWidget(content_frame)
    
    def _setup_connections(self):
        """Setup signal connections."""
        if not PYQT6_AVAILABLE:
            return
            
        # List widget signals
        self.track_list.itemClicked.connect(self._on_item_clicked)
        self.track_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.track_list.items_reordered.connect(self._on_items_reordered)
        
        # Button signals
        self.add_files_button.clicked.connect(self._on_add_files_requested)
        self.remove_button.clicked.connect(self._on_remove_selected_requested)
        self.clear_button.clicked.connect(self._on_clear_requested)
        
        # Selection change signal to enable/disable remove button
        self.track_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Context menu
        self.track_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_list.customContextMenuRequested.connect(self._show_context_menu)
    
    def set_player_controller(self, controller):
        """Set the player controller reference."""
        self.player_controller = controller
    
    def load_playlist(self, playlist_items: List[dict]):
        """
        Load playlist items into the widget.
        
        Args:
            playlist_items: List of playlist item dictionaries with 'file_path', 'title', etc.
        """
        if not PYQT6_AVAILABLE:
            return
        
        logger.info(f"PlaylistWidget.load_playlist called with {len(playlist_items)} items")
        logger.debug(f"Current track_list count before clear: {self.track_list.count()}")
        
        self.track_list.clear()
        
        logger.debug(f"Current track_list count after clear: {self.track_list.count()}")
        
        for i, item in enumerate(playlist_items):
            file_path = Path(item.get('file_path', ''))
            title = item.get('title', file_path.stem)
            
            # Create list item with only basic serializable data
            list_item = QListWidgetItem()
            list_item.setText(f"{i + 1:2d}. {title}")
            
            # Store only basic serializable data to avoid pickling issues
            basic_data = {
                'index': i,
                'file_path': str(file_path),
                'title': title,
                'duration': item.get('duration', 0.0),
                'file_size': item.get('file_size', 0),
            }
            list_item.setData(Qt.ItemDataRole.UserRole, basic_data)
            list_item.setToolTip(str(file_path))
            
            self.track_list.addItem(list_item)
        
        logger.debug(f"Current track_list count after adding items: {self.track_list.count()}")
        
        # Update status
        count = len(playlist_items)
        if count > 0:
            self.status_label.setText(f"{count} track{'s' if count != 1 else ''}")
            self.title_label.setText(f"Track List ({count})")
        else:
            self.status_label.setText(self.tr("playlist", "status", "no_tracks"))
            self.title_label.setText(self.tr("playlist", "title"))
        
        logger.debug(f"Loaded {count} tracks into playlist widget")
    
    def set_current_track(self, index: int, player_state: str = "stopped"):
        """
        Highlight the currently playing track with appropriate visual indicators.
        
        Args:
            index: Index of the currently playing track
            player_state: Current player state ("playing", "paused", "stopped", "loading")
        """
        if not PYQT6_AVAILABLE:
            return
            
        # Clear previous highlighting
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            if item:
                font = item.font()
                font.setBold(False)
                item.setFont(font)
                # Reset background color
                item.setBackground(self.palette().base())
        
        # Highlight current track
        if 0 <= index < self.track_list.count():
            item = self.track_list.item(index)
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
                
                # Scroll to current track
                self.track_list.scrollToItem(item)
                
                self.current_track_index = index
                logger.debug(f"Highlighted current track: {index} (state: {player_state})")
        
        # Update the current state for refresh
        self.current_player_state = player_state
    
    def update_player_state(self, player_state: str):
        """
        Update the visual state for the current track based on player state.
        
        Args:
            player_state: Current player state ("playing", "paused", "stopped", "loading")
        """
        if not PYQT6_AVAILABLE:
            return
            
        self.current_player_state = player_state
        # Refresh the highlighting with the new state
        if self.current_track_index >= 0:
            self.set_current_track(self.current_track_index, player_state)
            logger.debug(f"Updated player state visual indicator: {player_state}")
    
    def update_track_progress(self, index: int, position: float, duration: float):
        """
        Update progress indicator for a track (could show time remaining).
        
        Args:
            index: Track index
            position: Current position in seconds
            duration: Total duration in seconds
        """
        # This could be extended to show progress indicators
        pass
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle track item clicked."""
        if not PYQT6_AVAILABLE or not item:
            return
            
        index = self.track_list.row(item)
        self.track_selected.emit(index)
        logger.debug(f"Track selected: {index}")
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """Handle track item double-clicked (play)."""
        if not PYQT6_AVAILABLE or not item:
            return
            
        index = self.track_list.row(item)
        self.track_double_clicked.emit(index)
        logger.debug(f"Track double-clicked: {index}")
    
    def _on_items_reordered(self, from_index: int, to_index: int):
        """Handle tracks reordered via drag-drop."""
        if not PYQT6_AVAILABLE:
            return
        
        logger.debug(f"Tracks reordered: {from_index} -> {to_index}")
        
        # Update the underlying playlist order through the player controller
        if self.player_controller and hasattr(self.player_controller, 'move_playlist_item'):
            self.player_controller.move_playlist_item(from_index, to_index)
        
        # Emit signal for any other components that need to know about reordering
        if hasattr(self, 'track_moved'):
            self.track_moved.emit(to_index)
    
    def _on_clear_requested(self):
        """Handle clear playlist button clicked."""
        self.clear_playlist_requested.emit()
        logger.debug("Playlist clear requested")
    
    def _on_add_files_requested(self):
        """Handle add files button clicked."""
        self.add_files_requested.emit()
        logger.debug("Add files to playlist requested")
    
    def _on_remove_selected_requested(self):
        """Handle remove selected tracks button clicked."""
        selected_items = self.track_list.selectedItems()
        if not selected_items:
            return
        
        # Get indices of selected items (sorted in reverse order for proper removal)
        selected_indices = []
        for item in selected_items:
            index = self.track_list.row(item)
            selected_indices.append(index)
        
        # Sort in reverse order so removal doesn't affect subsequent indices
        selected_indices.sort(reverse=True)
        
        self.remove_tracks_requested.emit(selected_indices)
        logger.debug(f"Remove tracks requested: {selected_indices}")
    
    def _on_selection_changed(self):
        """Handle selection change to enable/disable remove button."""
        if not PYQT6_AVAILABLE:
            return
        
        selected_items = self.track_list.selectedItems()
        has_selection = len(selected_items) > 0
        self.remove_button.setEnabled(has_selection)
        
        # Update tooltip based on selection
        if has_selection:
            count = len(selected_items)
            if count == 1:
                self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_selected", count=count))
            else:
                self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_selected_plural", count=count))
        else:
            self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_tooltip"))
    
    def _show_context_menu(self, position):
        """Show context menu for track operations."""
        if not PYQT6_AVAILABLE:
            return
            
        item = self.track_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        # Play track action
        play_action = QAction(self.tr("playlist", "context_menu", "play_track"), self)
        play_action.triggered.connect(lambda: self._on_item_double_clicked(item))
        menu.addAction(play_action)
        
        menu.addSeparator()
        
        # Remove track action
        remove_action = QAction(self.tr("playlist", "context_menu", "remove_from_playlist"), self)
        remove_action.triggered.connect(lambda: self._remove_track(item))
        menu.addAction(remove_action)
        
        # Show menu
        menu.exec(self.track_list.mapToGlobal(position))
    
    def _remove_track(self, item: QListWidgetItem):
        """Remove a track from the playlist."""
        if not PYQT6_AVAILABLE or not item:
            return
            
        index = self.track_list.row(item)
        self.remove_track_requested.emit(index)
        logger.debug(f"Track removal requested: {index}")
    
    def clear_tracks(self):
        """Clear all tracks from the widget."""
        if not PYQT6_AVAILABLE:
            return
            
        self.track_list.clear()
        self.current_track_index = -1
        self.status_label.setText(self.tr("playlist", "status", "no_playlist"))
        self.title_label.setText(self.tr("playlist", "playlist_label"))
        logger.debug("Playlist widget cleared")
    
    def retranslate_ui(self):
        """Retranslate all UI elements."""
        if not PYQT6_AVAILABLE:
            return
        
        # Update title label
        if self.title_label:
            # Keep current title if we have tracks, otherwise use default
            if self.track_list.count() == 0:
                self.title_label.setText(self.tr("playlist", "title"))
        
        # Update button labels and tooltips
        if self.add_files_button:
            self.add_files_button.setText(self.tr("playlist", "buttons", "add_files"))
            self.add_files_button.setToolTip(self.tr("playlist", "buttons", "add_files_tooltip"))
        
        if self.remove_button:
            self.remove_button.setText(self.tr("playlist", "buttons", "remove"))
            selected = len(self.track_list.selectedItems())
            if selected > 0:
                if selected == 1:
                    self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_selected", count=selected))
                else:
                    self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_selected_plural", count=selected))
            else:
                self.remove_button.setToolTip(self.tr("playlist", "buttons", "remove_tooltip"))
        
        if self.clear_button:
            self.clear_button.setText(self.tr("playlist", "buttons", "clear"))
            self.clear_button.setToolTip(self.tr("playlist", "buttons", "clear_tooltip"))
        
        # Update status label
        if self.status_label and self.track_list.count() == 0:
            self.status_label.setText(self.tr("playlist", "status", "no_playlist"))
        
        logger.debug("Playlist widget retranslated")