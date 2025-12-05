#!/usr/bin/env python3
"""
Main window for TonieToolbox PyQt6 GUI.
Contains the primary user interface layout and coordinates components.
"""
from typing import Optional
import locale
from pathlib import Path

from TonieToolbox.core.gui.i18n.manager import TranslationManager
from TonieToolbox.core.config.manager import ConfigManager

try:
    from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QMenuBar, QStatusBar, QSplitter, QFrame, QFileDialog,
                                 QMessageBox, QProgressBar, QLabel, QPushButton, QTabWidget)
    from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QByteArray, QTimer
    from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QActionGroup
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QMainWindow = object
    QWidget = object
    QVBoxLayout = object
    QHBoxLayout = object
    QMenuBar = object
    QStatusBar = object
    QSplitter = object
    QFrame = object
    QFileDialog = object
    QMessageBox = object
    QProgressBar = object
    QLabel = object
    QPushButton = object
    QTabWidget = object
    Qt = object
    pyqtSignal = lambda: None
    pyqtSlot = lambda: None
    QThread = object
    QAction = object
    QKeySequence = object
    QByteArray = object
    QIcon = object
    QPixmap = object
    QActionGroup = object

from ..components.player.controls import PlayerControls
from ..components.player.progress import PlayerProgress
from ..components.player.info_panel import PlayerInfoPanel
from ..components.playlist.list_widget import PlaylistWidget
from ..components.playlist.controls import PlaylistControls
from ..components.playlist.info import PlaylistInfoPanel
from ..components.chapter.list_widget import ChapterWidget
from ..components.about.dialog import AboutDialog
from ..controllers.player_controller import QtPlayerController
from ..models.player_state import PlayerModel
from TonieToolbox.core.utils import get_logger
from TonieToolbox.core.config.application_constants import ICON_PNG_BASE64
from TonieToolbox.core.events import get_event_bus, LanguageChangedEvent
import base64

logger = get_logger(__name__)

# UI Layout Constants
LEFT_PANEL_MIN_WIDTH = 280
LEFT_PANEL_MAX_WIDTH = 350
MIDDLE_PANEL_MIN_WIDTH = 300
RIGHT_PANEL_MIN_WIDTH = 300

# Initial splitter sizes for three-panel layout
LEFT_PANEL_INITIAL_WIDTH = 280
MIDDLE_PANEL_INITIAL_WIDTH = 350
RIGHT_PANEL_INITIAL_WIDTH = 370


class MainWindow(QMainWindow):
    """
    Main application window for TonieToolbox Qt GUI.
    Coordinates all UI components and provides the main interface.
    """
    
    # Signals
    closing = pyqtSignal()
    
    def __init__(self, theme_manager=None, translation_manager=None, 
                 thread_manager=None, plugin_manager=None):
        """
        Initialize the main window.
        
        Args:
            theme_manager: Theme management system
            translation_manager: Translation management system
            thread_manager: Thread management system
            plugin_manager: Plugin management system
        """
        super().__init__()
        
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not available")
        
        # Dependency injection
        self.theme_manager = theme_manager
        self.translation_manager = translation_manager
        self.thread_manager = thread_manager
        self.plugin_manager = plugin_manager
        self._event_bus = get_event_bus()
        
        # Subscribe to language change events
        self._event_bus.subscribe(LanguageChangedEvent, self._on_language_changed)
        
        # Subscribe to plugin lifecycle events for dynamic GUI updates
        if plugin_manager:
            from ...plugins.events import (
                PluginLoadedEvent,
                PluginUnloadedEvent,
                PluginEnabledEvent,
                PluginDisabledEvent,
                PluginGuiComponentsChangedEvent
            )
            self._event_bus.subscribe(PluginLoadedEvent, self._on_plugin_loaded)
            self._event_bus.subscribe(PluginUnloadedEvent, self._on_plugin_unloaded)
            self._event_bus.subscribe(PluginEnabledEvent, self._on_plugin_enabled)
            self._event_bus.subscribe(PluginDisabledEvent, self._on_plugin_disabled)
            self._event_bus.subscribe(PluginGuiComponentsChangedEvent, self._on_plugin_gui_components_changed)
        
        # Plugin support
        self._gui_registry = None
        if plugin_manager:
            from ...plugins.registry import ComponentRegistry
            self._gui_registry = ComponentRegistry()
        
        # Models and controllers - Create BEFORE UI components
        self.player_model = PlayerModel()
        self.player_controller = QtPlayerController(
            player_model=self.player_model,
            thread_manager=self.thread_manager
        )
        
        # UI components
        self.central_widget: Optional[QWidget] = None
        self.tab_widget: Optional[QTabWidget] = None
        self.player_tab_widget: Optional[QWidget] = None
        self.player_controls: Optional[PlayerControls] = None
        self.player_progress: Optional[PlayerProgress] = None
        self.playlist_widget: Optional[PlaylistWidget] = None
        self.playlist_controls: Optional[PlaylistControls] = None
        self.playlist_info: Optional[PlaylistInfoPanel] = None
        self.chapter_widget: Optional[ChapterWidget] = None
        self.about_dialog: Optional[AboutDialog] = None
        
        # Status bar components
        self.status_bar: Optional[QStatusBar] = None
        self.status_player_state: Optional[QLabel] = None
        self.status_track_info: Optional[QLabel] = None
        self.status_progress: Optional[QLabel] = None
        
        # Status bar state tracking
        self._current_position = 0.0
        self._current_duration = 0.0
        
        # Title bar actions
        self._title_bar_actions = []
        
        # Initialize UI
        self._setup_ui()
        self._create_menus()
        self._create_status_bar()
        self._create_title_bar_actions()
        self._initialize_components()
        self._connect_signals()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        self.setWindowTitle(self.translation_manager.translate("app.title"))
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Set application icon
        self._setup_icon()

        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Create tab widget for main content
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create player tab as the default/first tab
        self.player_tab_widget = QWidget()
        player_tab_layout = QVBoxLayout(self.player_tab_widget)
        player_tab_layout.setContentsMargins(0, 0, 0, 0)
        player_tab_layout.setSpacing(0)
        
        # Create splitter for resizable panels in player tab
        splitter = QSplitter(Qt.Orientation.Horizontal)
        player_tab_layout.addWidget(splitter)

        # Left panel - Player controls and progress
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        left_panel.setMinimumWidth(LEFT_PANEL_MIN_WIDTH)
        left_panel.setMaximumWidth(LEFT_PANEL_MAX_WIDTH)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # Instantiate player controls and progress (real components)
        self.player_controls = PlayerControls(
            player_controller=None,  # Will be set later in _initialize_components
            translation_manager=self.translation_manager,
            theme_manager=self.theme_manager
        )
        left_layout.addWidget(self.player_controls)

        self.player_progress = PlayerProgress(
            player_controller=None,  # Will be set later in _initialize_components
            translation_manager=self.translation_manager,
            theme_manager=self.theme_manager
        )
        left_layout.addWidget(self.player_progress)

        # Add playlist controls
        self.playlist_controls = PlaylistControls(
            player_controller=None,  # Will be set later in _initialize_components
            translation_manager=self.translation_manager,
            theme_manager=self.theme_manager
        )
        left_layout.addWidget(self.playlist_controls)

        # Add chapter widget
        self.chapter_widget = ChapterWidget(
            player_controller=None,  # Will be set later in _initialize_components
            translation_manager=self.translation_manager,
            theme_manager=self.theme_manager
        )
        left_layout.addWidget(self.chapter_widget)

        left_layout.addStretch()

        # Middle panel - Playlist
        middle_panel = QFrame()
        middle_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        middle_panel.setMinimumWidth(MIDDLE_PANEL_MIN_WIDTH)

        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(5, 5, 5, 5)

        # Instantiate playlist widget
        self.playlist_widget = PlaylistWidget(
            player_controller=None,  # Will be set later in _initialize_components
            translation_manager=self.translation_manager,
            theme_manager=self.theme_manager
        )
        middle_layout.addWidget(self.playlist_widget)

        # Right panel - File and playlist information
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        right_panel.setMinimumWidth(RIGHT_PANEL_MIN_WIDTH)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Add playlist info panel
        self.playlist_info = PlaylistInfoPanel(
            player_controller=None,  # Will be set later in _initialize_components
            translation_manager=self.translation_manager,
            theme_manager=self.theme_manager
        )
        right_layout.addWidget(self.playlist_info)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(middle_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([LEFT_PANEL_INITIAL_WIDTH, MIDDLE_PANEL_INITIAL_WIDTH, RIGHT_PANEL_INITIAL_WIDTH])
        
        # Add player tab to tab widget
        self.tab_widget.addTab(self.player_tab_widget, self._translate("tabs", "player"))

        logger.debug("Main UI layout created")
    
    def _setup_icon(self):
        """Set up the application window icon."""
        if not PYQT6_AVAILABLE:
            return
            
        try:
            # Decode the base64 logo
            logo_data = base64.b64decode(ICON_PNG_BASE64)
            
            # Create QByteArray and QPixmap
            byte_array = QByteArray(logo_data)
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array, "PNG")
            
            # Set window icon
            icon = QIcon(pixmap)
            self.setWindowIcon(icon)
            
            logger.debug("Application icon set successfully")
        except Exception as e:
            logger.error(f"Failed to set application icon: {e}")
    
    def _translate(self, category: str, key: str, fallback: str = None) -> str:
        """Helper method to translate text with fallback."""
        if not self.translation_manager:
            return fallback or f"{category}.{key}"
        
        return self.translation_manager.translate(category, key) or fallback or f"{category}.{key}"
    
    def _create_menus(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # Store menu references for language updates
        self._menus = {}
        self._actions = {}
        
        # File menu
        self._menus['file'] = menubar.addMenu(self._translate("menu", "file"))
        
        self._actions['file_open'] = QAction(self._translate("menu", "file_open"), self)
        self._actions['file_open'].setShortcut(QKeySequence.StandardKey.Open)
        self._actions['file_open'].triggered.connect(self._open_file)
        self._menus['file'].addAction(self._actions['file_open'])
        
        self._menus['file'].addSeparator()
        
        # Playlist menu items
        self._actions['playlist_save'] = QAction(self._translate("menu", "playlist_save"), self)
        self._actions['playlist_save'].setShortcut("Ctrl+S")
        self._actions['playlist_save'].triggered.connect(self._save_playlist)
        self._menus['file'].addAction(self._actions['playlist_save'])
        
        self._actions['playlist_load'] = QAction(self._translate("menu", "playlist_load"), self)
        self._actions['playlist_load'].setShortcut("Ctrl+L")
        self._actions['playlist_load'].triggered.connect(self._load_playlist)
        self._menus['file'].addAction(self._actions['playlist_load'])
        
        self._menus['file'].addSeparator()
        
        self._actions['file_exit'] = QAction(self._translate("menu", "file_exit"), self)
        self._actions['file_exit'].setShortcut(QKeySequence.StandardKey.Quit)
        self._actions['file_exit'].triggered.connect(self.close)
        self._menus['file'].addAction(self._actions['file_exit'])
        
        # Tools menu
        self._menus['tools'] = menubar.addMenu(self._translate("menu", "tools"))
        
        # Conversion submenu
        convert_menu = self._menus['tools'].addMenu(self._translate("menu", "tools_convert"))
        
        convert_to_opus_action = QAction(self._translate("menu", "tools_convert_opus"), self)
        convert_to_opus_action.triggered.connect(self._convert_to_opus)
        convert_menu.addAction(convert_to_opus_action)
        
        convert_to_mp3_action = QAction(self._translate("menu", "tools_convert_mp3"), self)
        convert_to_mp3_action.triggered.connect(self._convert_to_mp3)
        convert_menu.addAction(convert_to_mp3_action)
        
        convert_to_single_mp3_action = QAction(self._translate("menu", "tools_convert_single_mp3"), self)
        convert_to_single_mp3_action.triggered.connect(self._convert_to_single_mp3)
        convert_menu.addAction(convert_to_single_mp3_action)
        
        self._menus['tools'].addSeparator()
        
        analyze_action = QAction(self._translate("menu", "tools_analyze"), self)
        analyze_action.triggered.connect(self._analyze_file)
        self._menus['tools'].addAction(analyze_action)
        
        # Plugin Manager
        if self.plugin_manager:
            self._menus['tools'].addSeparator()
            plugin_manager_action = QAction(self._translate("menu", "tools_plugin_manager"), self)
            plugin_manager_action.triggered.connect(self._open_plugin_manager)
            self._menus['tools'].addAction(plugin_manager_action)
        
        # View menu
        self._menus['view'] = menubar.addMenu(self._translate("menu", "view"))
        
        # Themes submenu (will be populated if multiple themes available)
        self._menus['view_themes'] = self._menus['view'].addMenu(self._translate("menu", "view_themes"))
        self._themes_menu = self._menus['view_themes']
        # Hide by default - will be shown only if multiple themes available
        self._menus['view_themes'].menuAction().setVisible(False)
        
        # Language submenu (will be populated by translation manager)
        self._menus['view_language'] = self._menus['view'].addMenu(self._translate("menu", "view_language"))
        self._language_menu = self._menus['view_language']
        
        # Help menu
        self._menus['help'] = menubar.addMenu(self._translate("menu", "help"))
        
        self._actions['help_about'] = QAction(self._translate("menu", "help_about"), self)
        self._actions['help_about'].triggered.connect(self._show_about)
        self._menus['help'].addAction(self._actions['help_about'])
        
        logger.debug("Menu bar created")
    
    def _create_status_bar(self):
        """Create the status bar with player state and track information."""
        if not PYQT6_AVAILABLE:
            return
            
        self.status_bar = self.statusBar()
        
        # Create status bar widgets
        self.status_player_state = QLabel(self.translation_manager.translate("status.ready"))
        self.status_track_info = QLabel("")
        self.status_progress = QLabel("")
        
        # Style the labels
        self.status_player_state.setMinimumWidth(80)
        self.status_track_info.setMinimumWidth(200)
        self.status_progress.setMinimumWidth(100)
        
        # Add widgets to status bar
        self.status_bar.addWidget(self.status_player_state)
        self.status_bar.addPermanentWidget(self.status_track_info)
        self.status_bar.addPermanentWidget(self.status_progress)
        
        logger.debug("Enhanced status bar created")
    
    def _create_title_bar_actions(self):
        """Create title bar action buttons (for plugin actions)."""
        if not PYQT6_AVAILABLE:
            return
        
        # Title bar actions will be added to menu bar as toolbar-style buttons
        # This creates a container for them on the right side of the menu bar
        menubar = self.menuBar()
        
        # Create a corner widget container for title bar actions
        self._title_bar_container = QWidget()
        title_bar_layout = QHBoxLayout(self._title_bar_container)
        title_bar_layout.setContentsMargins(5, 0, 5, 0)
        title_bar_layout.setSpacing(5)
        
        # Set as menu bar corner widget (right side)
        menubar.setCornerWidget(self._title_bar_container, Qt.Corner.TopRightCorner)
        
        logger.debug("Title bar actions container created")
    
    def update_title_bar_actions(self):
        """Update title bar with plugin-registered actions."""
        if not self._gui_registry or not PYQT6_AVAILABLE:
            return
        
        try:
            # Get registered title bar actions
            title_bar_actions = self._gui_registry.get_all("title_bar_actions")
            
            if not title_bar_actions:
                logger.debug("No title bar actions to register")
                return
            
            # Clear existing actions
            for action_widget in self._title_bar_actions:
                action_widget.deleteLater()
            self._title_bar_actions.clear()
            
            # Get layout
            layout = self._title_bar_container.layout()
            
            # Add each registered action
            for action_id, action_config in title_bar_actions.items():
                icon_text = action_config.get("icon", "⚙")
                tooltip = action_config.get("tooltip", action_id)
                callback = action_config.get("callback")
                checkable = action_config.get("checkable", False)
                
                # Create button
                button = QPushButton(icon_text)
                button.setToolTip(tooltip)
                button.setCheckable(checkable)
                button.setFixedSize(32, 24)
                button.setFlat(True)
                
                if callback:
                    button.clicked.connect(callback)
                
                # Add to layout
                layout.addWidget(button)
                self._title_bar_actions.append(button)
                
                logger.debug(f"Added title bar action: {action_id}")
            
        except Exception as e:
            logger.error(f"Failed to update title bar actions: {e}")
    
    def _populate_language_menu(self):
        """Populate the language menu with available languages."""
        if not PYQT6_AVAILABLE or not self.translation_manager or not self._language_menu:
            return
            
        try:
            # Clear existing menu items
            self._language_menu.clear()
            
            # Get available languages
            available_languages = self.translation_manager.get_available_languages()
            current_language = self.translation_manager.get_current_language()
            
            # Create action group for exclusive selection
            self._language_action_group = QActionGroup(self)
            
            # Add language options
            for lang_code, display_name in available_languages.items():
                action = QAction(display_name, self)
                action.setCheckable(True)
                action.setData(lang_code)  # Store language code
                
                # Check current language
                if lang_code == current_language:
                    action.setChecked(True)
                
                # Connect to language change handler
                action.triggered.connect(self._on_language_menu_triggered)
                
                # Add to group and menu
                self._language_action_group.addAction(action)
                self._language_menu.addAction(action)
            
            logger.debug(f"Populated language menu with {len(available_languages)} languages")
            
        except Exception as e:
            logger.error(f"Failed to populate language menu: {e}")
    
    def _populate_themes_menu(self):
        """Populate the themes menu with available themes."""
        if not PYQT6_AVAILABLE or not self.theme_manager or not self._themes_menu:
            return
            
        try:
            # Clear existing menu items
            self._themes_menu.clear()
            
            # Get available themes
            available_themes = self.theme_manager.get_available_themes()
            
            # Only show themes menu if there are multiple themes
            if len(available_themes) <= 1:
                self._menus['view_themes'].menuAction().setVisible(False)
                logger.debug("Only one theme available, hiding themes menu")
                return
            
            # Show themes menu since we have multiple themes
            self._menus['view_themes'].menuAction().setVisible(True)
            
            # Get current theme
            current_theme = self.theme_manager.get_current_theme_name()
            
            # Create action group for exclusive selection
            self._theme_action_group = QActionGroup(self)
            
            # Add theme options
            for theme_name, display_name in available_themes.items():
                action = QAction(display_name, self)
                action.setCheckable(True)
                action.setData(theme_name)  # Store theme name
                
                # Check current theme
                if theme_name == current_theme:
                    action.setChecked(True)
                
                # Connect to theme change handler
                action.triggered.connect(self._on_theme_changed)
                
                # Add to group and menu
                self._theme_action_group.addAction(action)
                self._themes_menu.addAction(action)
            
            logger.debug(f"Populated themes menu with {len(available_themes)} themes")
            
        except Exception as e:
            logger.error(f"Failed to populate themes menu: {e}")
    
    def _on_theme_changed(self):
        """Handle theme selection change."""
        if not PYQT6_AVAILABLE:
            return
            
        try:
            # Get the action that was triggered
            action = self.sender()
            if not action:
                return
                
            theme_name = action.data()
            if not theme_name:
                return
            
            logger.info(f"Theme change requested: {theme_name}")
            
            # Apply theme
            if self.theme_manager and self.theme_manager.apply_theme(theme_name):
                # Save to configuration
                self._save_theme_setting(theme_name)
                
                logger.info(f"Theme changed to: {theme_name}")
            else:
                logger.error(f"Failed to change theme to: {theme_name}")
                
        except Exception as e:
            logger.error(f"Error handling theme change: {e}")
    
    def _save_theme_setting(self, theme_name: str):
        """Save theme setting to configuration."""
        try:
            from TonieToolbox.core.config import get_config_manager
            
            config_manager = get_config_manager()
            gui_config = config_manager.gui
            
            # Update GUI config theme setting
            gui_config.theme = theme_name
            
            # Save configuration
            config_manager.save_config()
            
            logger.debug(f"Theme setting saved: {theme_name}")
            
        except Exception as e:
            logger.error(f"Failed to save theme setting: {e}")
    
    def _on_language_menu_triggered(self):
        """Handle language menu selection."""
        if not PYQT6_AVAILABLE:
            return
            
        try:
            # Get the action that was triggered
            action = self.sender()
            if not action:
                return
                
            language_code = action.data()
            if not language_code:
                return
            
            logger.info(f"Language change requested: {language_code}")
            
            # Update translation manager (event bus will notify all components)
            if self.translation_manager and self.translation_manager.set_language(language_code):
                # Save to configuration
                self._save_language_setting(language_code)
                
                logger.info(f"Language changed to: {language_code}")
            else:
                logger.error(f"Failed to change language to: {language_code}")
                
        except Exception as e:
            logger.error(f"Error handling language menu selection: {e}")
    
    def _save_language_setting(self, language_code: str):
        """Save language setting to configuration."""
        try:
            from TonieToolbox.core.config import get_config_manager
            
            config_manager = get_config_manager()
            gui_config = config_manager.gui
            
            # Update GUI config language setting
            gui_config.language = language_code
            
            # Disable auto-detection when manually changing language
            # This ensures the user's choice persists across restarts
            gui_config.auto_detect_language = False
            
            # Save configuration
            config_manager.save_config()
            
            logger.debug(f"Saved language setting: {language_code}, disabled auto-detection")
            
        except Exception as e:
            logger.error(f"Failed to save language setting: {e}")
    
    def _on_language_changed(self, event: LanguageChangedEvent):
        """Handle language changed event from event bus.
        
        Args:
            event: Language changed event
        """
        if not PYQT6_AVAILABLE or not self.translation_manager:
            return
            
        try:
            logger.debug(f"Language changed in MainWindow: {event.old_language} -> {event.new_language}")
            
            # Update window title
            self.setWindowTitle(self.translation_manager.translate("app", "title"))
            
            # Update menu titles
            if hasattr(self, '_menus'):
                self._menus['file'].setTitle(self._translate("menu", "file"))
                self._menus['tools'].setTitle(self._translate("menu", "tools"))
                self._menus['view'].setTitle(self._translate("menu", "view"))
                self._menus['view_themes'].setTitle(self._translate("menu", "view_themes"))
                self._menus['view_language'].setTitle(self._translate("menu", "view_language"))
                self._menus['help'].setTitle(self._translate("menu", "help"))
            
            # Update menu actions
            if hasattr(self, '_actions'):
                self._actions['file_open'].setText(self._translate("menu", "file_open"))
                self._actions['file_exit'].setText(self._translate("menu", "file_exit"))
                self._actions['help_about'].setText(self._translate("menu", "help_about"))
            
            # Update language menu to reflect current selection
            self._populate_language_menu()
            
            # Note: Individual components automatically subscribe to LanguageChangedEvent
            # and retranslate their UI via the event bus
            
        except Exception as e:
            logger.error(f"Failed to update UI language: {e}")
    
    def _initialize_components(self):
        """Initialize UI components."""
        try:
            # Initialize player controller
            self.player_controller = QtPlayerController(
                player_model=self.player_model,
                thread_manager=self.thread_manager
            )

            # If UI is already set up, update player components with controller
            if self.player_controls:
                self.player_controls.set_player_controller(self.player_controller)
                # Also set the player controls reference in the controller
                self.player_controller.set_player_controls(self.player_controls)
                # Set references for playlist highlighting
                if self.playlist_widget:
                    self.player_controls.set_playlist_widget(self.playlist_widget)
                # Set TAF player reference - will be None initially but updated when file is loaded
                self.player_controls.set_taf_player(self.player_controller)
            if self.player_progress:
                self.player_progress.set_player_controller(self.player_controller)
            
            # Update playlist components with controller
            if self.playlist_widget:
                self.playlist_widget.set_player_controller(self.player_controller)
                # Also set the playlist widget reference in the controller
                self.player_controller.set_playlist_widget(self.playlist_widget)
            if self.playlist_controls:
                self.playlist_controls.set_player_controller(self.player_controller)
                # Also set the playlist controls reference in the controller
                self.player_controller.set_playlist_controls(self.playlist_controls)
            if self.playlist_info:
                self.playlist_info.set_player_controller(self.player_controller)
                # Also set the playlist info panel reference in the controller
                self.player_controller.set_playlist_info_panel(self.playlist_info)
                # Connect playlist name editing signal
                self.playlist_info.playlist_name_changed.connect(self._on_playlist_name_changed)
            
            # Update chapter widget with controller
            if self.chapter_widget:
                self.chapter_widget.set_player_controller(self.player_controller)
                # Also set the chapter widget reference in the controller
                self.player_controller.set_chapter_widget(self.chapter_widget)
            
            # Set main window reference for layout management
            self.player_controller.set_main_window(self)

            # Initialize menus after components are ready
            self._populate_language_menu()
            self._populate_themes_menu()
            
            # Auto-load last playlist if enabled
            self._auto_load_last_playlist()
            
            logger.debug("Components initialized")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _auto_load_last_playlist(self):
        """Auto-load last playlist if enabled in config."""
        try:
            from TonieToolbox.core.config import get_config_manager
            config = get_config_manager()
            
            auto_load_enabled = config.get_setting("gui.behavior.auto_load_last_playlist")
            if not auto_load_enabled:
                logger.debug("Auto-load last playlist is disabled")
                return
            
            last_playlist_path = Path(config.get_setting("gui.behavior.last_playlist_path"))
            
            if not last_playlist_path.exists():
                logger.debug(f"No last playlist found at: {last_playlist_path}")
                return
            
            logger.info(f"Auto-loading last playlist from: {last_playlist_path}")
            
            # Use QTimer to load playlist after UI is fully initialized
            QTimer.singleShot(100, lambda: self._load_last_playlist_delayed(last_playlist_path))
            
        except Exception as e:
            logger.error(f"Failed to auto-load last playlist: {e}")
    
    def _load_last_playlist_delayed(self, playlist_path: Path):
        """Load last playlist with a delay to ensure UI is ready."""
        try:
            if self.player_controller and hasattr(self.player_controller, 'load_playlist_file'):
                success, error_msg = self.player_controller.load_playlist_file(playlist_path)
                if success:
                    logger.info(f"Successfully auto-loaded last playlist")
                else:
                    logger.warning(f"Failed to auto-load last playlist: {error_msg}")
        except Exception as e:
            logger.error(f"Error loading last playlist: {e}")
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Window signals
        self.closing.connect(self._on_closing)
        
        # Connect player components to controller and vice-versa
        try:
            if not self.player_controller:
                logger.debug("Player controller not initialized yet; attempting to initialize components")
                self._initialize_components()

            pc = self.player_controller

            # Controls -> Controller
            if self.player_controls and pc:
                try:
                    # Basic playback controls
                    self.player_controls.play_toggle_clicked.connect(pc.toggle_playback)
                    self.player_controls.stop_clicked.connect(pc.stop)
                    
                    # Chapter navigation (within current track)
                    self.player_controls.prev_chapter_clicked.connect(pc.previous_chapter)
                    self.player_controls.next_chapter_clicked.connect(pc.next_chapter)
                    
                    # Track navigation (playlist)
                    self.player_controls.prev_track_clicked.connect(pc.previous_track)
                    self.player_controls.next_track_clicked.connect(pc.next_track)
                    
                    # Volume controls
                    self.player_controls.volume_changed.connect(pc.set_volume)
                    self.player_controls.mute_toggled.connect(pc.set_muted)
                    
                    logger.debug("Connected PlayerControls signals to QtPlayerController")
                except Exception as e:
                    logger.error(f"Failed to connect PlayerControls -> controller: {e}")

            # Progress -> Controller (seeking)
            if self.player_progress and pc:
                try:
                    self.player_progress.seek_requested.connect(pc.seek)
                    logger.debug("Connected PlayerProgress.seek_requested -> controller.seek")
                except Exception as e:
                    logger.error(f"Failed to connect PlayerProgress -> controller: {e}")

            # Playlist Controls -> Controller (playlist settings only)
            if self.playlist_controls and pc:
                try:
                    # Playlist settings
                    self.playlist_controls.shuffle_toggled.connect(pc.set_shuffle)
                    self.playlist_controls.repeat_mode_changed.connect(pc.set_repeat_mode)
                    self.playlist_controls.auto_advance_toggled.connect(pc.set_auto_advance)
                    
                    logger.debug("Connected PlaylistControls signals to QtPlayerController")
                except Exception as e:
                    logger.error(f"Failed to connect PlaylistControls -> controller: {e}")

            # Playlist Widget -> Controller
            if self.playlist_widget and pc:
                try:
                    self.playlist_widget.track_selected.connect(pc.select_track)
                    self.playlist_widget.track_double_clicked.connect(pc.play_track_at_index)
                    self.playlist_widget.remove_track_requested.connect(pc.remove_track)
                    self.playlist_widget.remove_tracks_requested.connect(self._remove_multiple_tracks)
                    self.playlist_widget.clear_playlist_requested.connect(pc.clear_playlist)
                    self.playlist_widget.add_files_requested.connect(self._add_files_to_playlist)
                    logger.debug("Connected PlaylistWidget signals to QtPlayerController")
                except Exception as e:
                    logger.error(f"Failed to connect PlaylistWidget -> controller: {e}")

            # Controller -> UI status updates
            try:
                # Show status messages on file load and state changes
                pc.file_loaded.connect(self._on_file_loaded)
                pc.state_changed.connect(self._on_state_changed)
                
                # Progress tracking for status bar
                pc.position_changed.connect(self._on_position_changed)
                pc.duration_changed.connect(self._on_duration_changed)

                # Chapter changed -> could be used to highlight current chapter in info panel
                pc.chapter_changed.connect(lambda idx: logger.debug(f"Chapter changed: {idx}"))

                # Errors -> status bar log
                pc.error_occurred.connect(self._on_error_occurred)

                logger.debug("Connected QtPlayerController signals to UI components")
            except Exception as e:
                logger.error(f"Failed to connect controller -> UI: {e}")

        except Exception as e:
            logger.error(f"Error during signal connections: {e}")

        logger.debug("Signals connected")
    
    def _open_file(self):
        """Open TAF file(s) or folder using a file dialog."""
        logger.info("Open file requested")
        try:
            # Create a custom dialog for multiple file selection or folder selection
            dialog = QFileDialog(self)
            dialog.setWindowTitle(self.translation_manager.translate("dialogs.open_file.title"))
            dialog.setNameFilter("TAF Files (*.taf);;All Files (*)")
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)  # Allow multiple files
            
            # Add option for folder selection
            folder_action = dialog.addAction(self.translation_manager.translate("dialogs.open_file.select_folder"))
            folder_action.triggered.connect(lambda: self._open_folder_dialog())
            
            if dialog.exec() == QFileDialog.DialogCode.Accepted:
                file_paths = dialog.selectedFiles()
                if file_paths:
                    logger.info(f"Selected {len(file_paths)} file(s) to open: {file_paths}")
                    
                    if len(file_paths) == 1:
                        # Single file - load directly
                        if self.player_controller:
                            try:
                                self.player_controller.load_file(Path(file_paths[0]))
                            except Exception as e:
                                logger.error(f"Failed to load single file: {e}")
                                self._show_error_message("Error", f"Failed to load file: {e}")
                    else:
                        # Multiple files - create temporary playlist
                        if self.player_controller:
                            try:
                                self._load_multiple_files(file_paths)
                            except Exception as e:
                                logger.error(f"Failed to load multiple files: {e}")
                                self._show_error_message("Error", f"Failed to load files: {e}")
                else:
                    logger.warning("Player controller not available when opening files")

        except Exception as e:
            logger.error(f"Error showing open file dialog: {e}")

    def _open_folder_dialog(self):
        """Open folder dialog to select a folder containing TAF files."""
        try:
            import os

            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Folder Containing TAF Files"
            )
            
            if folder_path:
                logger.info(f"Selected folder: {folder_path}")
                
                # Find all TAF files in the folder and subfolders
                taf_files = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith('.taf'):
                            taf_files.append(os.path.join(root, file))
                
                if taf_files:
                    logger.info(f"Found {len(taf_files)} TAF files in folder")
                    # Sort files naturally
                    taf_files.sort()
                    
                    if len(taf_files) == 1:
                        # Single file - load directly
                        if self.player_controller:
                            self.player_controller.load_file(Path(taf_files[0]))
                    else:
                        # Multiple files - create playlist
                        if self.player_controller:
                            self._load_multiple_files(taf_files)
                else:
                    self._show_error_message("No TAF Files", "No TAF files found in the selected folder.")
                    
        except Exception as e:
            logger.error(f"Error in folder selection: {e}")
            self._show_error_message("Error", f"Error selecting folder: {e}")

    def _load_multiple_files(self, file_paths):
        """Load multiple TAF files as a playlist.
        
        This method delegates to the player controller to ensure proper
        playlist manager initialization and backend/UI synchronization.
        """
        try:
            if not file_paths:
                logger.warning("No files provided to load")
                return
            
            # Delegate to player controller - single source of truth
            if self.player_controller and hasattr(self.player_controller, 'add_files_to_playlist'):
                success = self.player_controller.add_files_to_playlist(file_paths)
                
                if success:
                    if self.status_bar:
                        self.status_bar.showMessage(f"Loaded {len(file_paths)} TAF files", 3000)
                    logger.info(f"Successfully loaded {len(file_paths)} files as playlist")
                else:
                    logger.error("Failed to create playlist via player controller")
                    self._show_error_message("Error", "Failed to load files as playlist")
            else:
                logger.error("Player controller not available or missing add_files_to_playlist method")
                self._show_error_message("Error", "Playlist functionality not available")
                
        except Exception as e:
            logger.error(f"Error loading multiple files: {e}", exc_info=True)
            self._show_error_message("Error", f"Failed to load files: {e}")

    def _show_error_message(self, title, message):
        """Show an error message dialog."""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.exec()
        except Exception as e:
            logger.error(f"Error showing message box: {e}")
    
    def _show_about(self):
        """Show the about dialog."""
        if not self.about_dialog:
            self.about_dialog = AboutDialog(
                parent=self,
                translation_manager=self.translation_manager
            )
        
        self.about_dialog.exec()
    
    def _save_playlist(self):
        """Save current playlist to a .lst file."""
        logger.info("Save playlist requested")
        try:
            if not self.player_controller:
                logger.warning("No player controller available for saving playlist")
                return
            
            # Check if there's a playlist to save
            if (not self.player_controller.taf_player or 
                not hasattr(self.player_controller.taf_player, 'playlist_manager') or
                not self.player_controller.taf_player.playlist_manager or
                self.player_controller.taf_player.playlist_manager.is_empty()):
                self._show_error_message(
                    self.translation_manager.translate("dialogs.error.no_playlist"),
                    self.translation_manager.translate("dialogs.error.no_playlist_to_save")
                )
                return
            
            # Get current playlist name
            current_name = self.player_controller.get_playlist_name() or "playlist"
            
            # Show save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.translation_manager.translate("dialogs.save_playlist.title"),
                str(Path.home() / f"{current_name}.lst"),
                "Playlist Files (*.lst);;M3U Files (*.m3u);;All Files (*)"
            )
            
            if file_path:
                # Get playlist name (optionally prompt user)
                playlist_name = Path(file_path).stem
                
                # Save playlist
                success = self.player_controller.save_playlist(Path(file_path), playlist_name)
                if success:
                    # Update last playlist path in config
                    try:
                        from TonieToolbox.core.config import get_config_manager
                        config = get_config_manager()
                        config.set_setting("gui.behavior.last_playlist_path", file_path)
                    except Exception as config_error:
                        logger.warning(f"Could not save last playlist path to config: {config_error}")
                    
                    logger.info(f"Playlist saved to: {file_path}")
                    if self.status_bar:
                        self.status_bar.showMessage(f"Playlist saved: {file_path}", 3000)
                else:
                    self._show_error_message(
                        self.translation_manager.translate("dialogs.error.playlist_save_failed"),
                        self.translation_manager.translate("dialogs.error.playlist_save_failed_msg")
                    )
        except Exception as e:
            logger.error(f"Error saving playlist: {e}")
            self._show_error_message(
                self.translation_manager.translate("dialogs.error.title"),
                f"Error saving playlist: {e}"
            )
    
    def _load_playlist(self):
        """Load a playlist from a .lst file."""
        logger.info("Load playlist requested")
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.translation_manager.translate("dialogs.load_playlist.title"),
                str(Path.home()),
                "Playlist Files (*.lst);;M3U Files (*.m3u *.m3u8);;All Files (*)"
            )
            
            if file_path:
                logger.info(f"Loading playlist from: {file_path}")
                
                if self.player_controller:
                    success, error_msg = self.player_controller.load_playlist_file(Path(file_path))
                    if success:
                        # Update last playlist path in config
                        try:
                            from TonieToolbox.core.config import get_config_manager
                            config = get_config_manager()
                            config.set_setting("gui.behavior.last_playlist_path", file_path)
                        except Exception as config_error:
                            logger.warning(f"Could not save last playlist path to config: {config_error}")
                        
                        logger.info(f"Playlist loaded successfully")
                        if self.status_bar:
                            playlist_name = self.player_controller.get_playlist_name() or Path(file_path).stem
                            self.status_bar.showMessage(f"Playlist loaded: {playlist_name}", 3000)
                    else:
                        # Use detailed error message if available
                        error_title = self.translation_manager.translate("dialogs.error.playlist_load_failed")
                        if error_msg:
                            # Check if error_msg is a tuple (translation_key, params) or a string
                            if isinstance(error_msg, tuple) and len(error_msg) == 2:
                                error_key, params = error_msg
                                translated_msg = self.translation_manager.translate(f"dialogs.error.{error_key}", **params)
                            else:
                                # Use the error message as-is (for exceptions)
                                translated_msg = str(error_msg)
                            self._show_error_message(error_title, translated_msg)
                        else:
                            self._show_error_message(
                                error_title,
                                self.translation_manager.translate("dialogs.error.playlist_load_failed_msg")
                            )
                else:
                    logger.warning("No player controller available for loading playlist")
        except Exception as e:
            logger.error(f"Error loading playlist: {e}")
            self._show_error_message(
                self.translation_manager.translate("dialogs.error.title"),
                f"Error loading playlist: {e}"
            )
    
    def _convert_to_opus(self):
        """Convert TAF file to separate Opus files."""
        try:
            # Open file dialog to select TAF file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select TAF File to Convert",
                "",
                "TAF Files (*.taf);;All Files (*)"
            )
            
            if not file_path:
                return
                
            # Select output directory
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory"
            )
            
            if not output_dir:
                return
            
            self._perform_conversion(file_path, output_dir, "opus")
            
        except Exception as e:
            logger.error(f"Error in Opus conversion: {e}")
            QMessageBox.critical(
                self,
                self.translation_manager.translate("dialogs.error.conversion_error"),
                self.translation_manager.translate("dialogs.error.conversion_failed", error=str(e))
            )
    
    def _convert_to_mp3(self):
        """Convert TAF file to separate MP3 files."""
        try:
            # Open file dialog to select TAF file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select TAF File to Convert",
                "",
                "TAF Files (*.taf);;All Files (*)"
            )
            
            if not file_path:
                return
                
            # Select output directory
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory"
            )
            
            if not output_dir:
                return
            
            self._perform_conversion(file_path, output_dir, "mp3_separate")
            
        except Exception as e:
            logger.error(f"Error in MP3 conversion: {e}")
            QMessageBox.critical(
                self,
                self.translation_manager.translate("dialogs.error.conversion_error"),
                self.translation_manager.translate("dialogs.error.conversion_failed", error=str(e))
            )
    
    def _convert_to_single_mp3(self):
        """Convert TAF file to a single MP3 file."""
        try:
            # Open file dialog to select TAF file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select TAF File to Convert",
                "",
                "TAF Files (*.taf);;All Files (*)"
            )
            
            if not file_path:
                return
                
            # Select output file
            output_file, _ = QFileDialog.getSaveFileName(
                self,
                "Save MP3 As",
                "",
                "MP3 Files (*.mp3);;All Files (*)"
            )
            
            if not output_file:
                return
            
            self._perform_single_conversion(file_path, output_file, "mp3_single")
            
        except Exception as e:
            logger.error(f"Error in single MP3 conversion: {e}")
            QMessageBox.critical(self, "Conversion Error", f"Failed to convert file: {str(e)}")
    
    def _analyze_file(self):
        """Analyze a TAF file and show detailed information."""
        try:
            # Open file dialog to select TAF file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select TAF File to Analyze",
                "",
                "TAF Files (*.taf);;All Files (*)"
            )
            
            if not file_path:
                return
            
            self._perform_analysis(file_path)
            
        except Exception as e:
            logger.error(f"Error in file analysis: {e}")
            QMessageBox.critical(self, "Analysis Error", f"Failed to analyze file: {str(e)}")
    
    def _open_plugin_manager(self):
        """Open the Plugin Manager GUI."""
        try:
            if not self.plugin_manager:
                QMessageBox.warning(
                    self,
                    "Plugin Manager Unavailable",
                    "Plugin system is not enabled or initialized."
                )
                return
            
            # Get the Plugin Manager GUI plugin
            plugin = self.plugin_manager.get_plugin("com.tonietoolbox.plugin_manager")
            
            if not plugin:
                QMessageBox.warning(
                    self,
                    "Plugin Manager Not Found",
                    "The Plugin Manager GUI plugin is not installed."
                )
                return
            
            # Check if plugin is enabled
            if not plugin.is_enabled:
                # Try to enable it
                if not self.plugin_manager.enable_plugin("com.tonietoolbox.plugin_manager"):
                    QMessageBox.warning(
                        self,
                        "Plugin Manager Unavailable",
                        "Failed to enable the Plugin Manager GUI plugin."
                    )
                    return
            
            # Show the plugin manager window
            plugin.show_manager_window()
            
        except Exception as e:
            logger.error(f"Error opening Plugin Manager: {e}")
            QMessageBox.critical(
                self,
                "Plugin Manager Error",
                f"Failed to open Plugin Manager: {str(e)}"
            )
    
    def _perform_conversion(self, input_file, output_dir, conversion_type):
        """Perform the actual conversion operation."""
        try:
            from TonieToolbox.core.media.conversion.taf import convert_taf_to_chapter_files
            from pathlib import Path
            
            # Show progress dialog
            progress = QProgressBar()
            progress.setRange(0, 0)  # Indeterminate progress
            progress.show()
            
            logger.info(f"Starting {conversion_type} conversion: {input_file} -> {output_dir}")
            
            if conversion_type == "opus":
                # Convert to Opus files
                convert_taf_to_chapter_files(
                    filename=input_file,
                    output=output_dir,
                    format="opus"
                )
            elif conversion_type == "mp3_separate":
                # Convert to separate MP3 files
                convert_taf_to_chapter_files(
                    filename=input_file,
                    output=output_dir,
                    format="mp3",
                    codec_options={'bitrate': 128}
                )
            
            progress.close()
            QMessageBox.information(
                self,
                self.translation_manager.translate("dialogs.info.conversion_complete"),
                self.translation_manager.translate("dialogs.info.conversion_success_dir", output_dir=output_dir)
            )
            if self.status_bar:
                self.status_bar.showMessage(f"Conversion completed: {Path(input_file).name}", 5000)
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            QMessageBox.critical(
                self,
                self.translation_manager.translate("dialogs.error.conversion_error"),
                self.translation_manager.translate("dialogs.error.conversion_failed_generic", error=str(e))
            )
    
    def _perform_single_conversion(self, input_file, output_file, conversion_type):
        """Perform single file conversion operation."""
        try:
            from TonieToolbox.core.media.conversion.taf import convert_taf_to_single_file
            from pathlib import Path
            
            # Show progress dialog
            progress = QProgressBar()
            progress.setRange(0, 0)  # Indeterminate progress
            progress.show()
            
            logger.info(f"Starting {conversion_type} conversion: {input_file} -> {output_file}")
            
            if conversion_type == "mp3_single":
                # Convert to single MP3 file
                convert_taf_to_single_file(
                    filename=input_file,
                    output=output_file,
                    format="mp3",
                    codec_options={'bitrate': 128}
                )
            
            progress.close()
            QMessageBox.information(self, "Conversion Complete", f"Successfully converted to {output_file}")
            if self.status_bar:
                self.status_bar.showMessage(f"Conversion completed: {Path(output_file).name}", 5000)
            
        except Exception as e:
            logger.error(f"Single conversion failed: {e}")
            QMessageBox.critical(self, "Conversion Error", f"Conversion failed: {str(e)}")
    
    def _perform_analysis(self, input_file):
        """Perform TAF file analysis."""
        try:
            from TonieToolbox.core.analysis import get_header_info_cli
            from TonieToolbox.core.gui.components.tools import TafAnalysisDialog
            from pathlib import Path
            
            # Perform analysis - open file in binary mode
            with open(input_file, 'rb') as f:
                header_info = get_header_info_cli(f)
            
            # Show analysis dialog
            dialog = TafAnalysisDialog(
                file_path=input_file,
                header_info=header_info,
                parent=self,
                translation_manager=self.translation_manager
            )
            dialog.exec()
            
            if self.status_bar:
                self.status_bar.showMessage(f"Analysis completed: {Path(input_file).name}", 5000)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            QMessageBox.critical(self, "Analysis Error", f"Analysis failed: {str(e)}")
    
    def _on_closing(self):
        """Handle window closing."""
        logger.info("Main window closing")
    
    def get_player_controller(self):
        """Get the player controller instance."""
        return self.player_controller
    
    def closeEvent(self, event):
        """Handle close event."""
        self.closing.emit()
        
        # Auto-save playlist if enabled
        try:
            from pathlib import Path
            from TonieToolbox.core.config import get_config_manager
            config = get_config_manager()
            
            auto_save_enabled = config.get_setting("gui.behavior.auto_save_playlist")
            if auto_save_enabled:
                last_playlist_path = Path(config.get_setting("gui.behavior.last_playlist_path"))
                if self.player_controller and hasattr(self.player_controller, 'save_playlist'):
                    # Check if there's a playlist to save
                    if (self.player_controller.taf_player and 
                        hasattr(self.player_controller.taf_player, 'playlist_manager') and
                        self.player_controller.taf_player.playlist_manager and
                        not self.player_controller.taf_player.playlist_manager.is_empty()):
                        
                        # Ensure directory exists
                        last_playlist_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        logger.info(f"Auto-saving playlist to: {last_playlist_path}")
                        self.player_controller.save_playlist(last_playlist_path)
                    else:
                        logger.debug("No playlist to auto-save")
        except Exception as e:
            logger.error(f"Failed to auto-save playlist: {e}")
        
        # Unsubscribe from events
        try:
            self._event_bus.unsubscribe(LanguageChangedEvent, self._on_language_changed)
        except Exception as e:
            logger.error(f"Error unsubscribing from events: {e}")
        
        # Cleanup components
        if self.player_controller:
            self.player_controller.cleanup()
        
        event.accept()
    
    def set_playlist_mode(self, is_playlist_mode: bool):
        """Set the display mode for playlist."""
        if not PYQT6_AVAILABLE:
            return
        
        # Show playlist info panel when playlist is loaded
        if self.playlist_info:
            self.playlist_info.setVisible(is_playlist_mode)
        
        logger.debug(f"Playlist mode: {is_playlist_mode}")
    
    def _update_status_bar_state(self, player_state: str):
        """Update the player state in the status bar."""
        if not PYQT6_AVAILABLE or not self.status_player_state:
            return
            
        # Map internal states to translation keys
        state_key = player_state.lower()
        
        # Get translated text
        display_state = self.translation_manager.translate(f"status.{state_key}")
        
        # Fallback to capitalized state if translation not found
        if display_state.startswith("status."):
            display_state = player_state.title()
        
        self.status_player_state.setText(display_state)
        logger.debug(f"Status bar state updated: {display_state}")
    
    def _update_status_bar_track_info(self, track_name: str = ""):
        """Update the track information in the status bar."""
        if not PYQT6_AVAILABLE or not self.status_track_info:
            return
            
        if track_name:
            self.status_track_info.setText(f"♪ {track_name}")
        else:
            self.status_track_info.setText("")
        logger.debug(f"Status bar track info updated: {track_name}")
    
    def _update_status_bar_progress(self, current_time: float = 0.0, total_time: float = 0.0):
        """Update the time progress in the status bar."""
        if not PYQT6_AVAILABLE or not self.status_progress:
            return
            
        if total_time > 0:
            current_str = self._format_time(current_time)
            total_str = self._format_time(total_time)
            self.status_progress.setText(f"{current_str} / {total_str}")
        else:
            self.status_progress.setText("")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to HH:MM:SS or MM:SS format."""
        if seconds < 0:
            seconds = 0
            
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _on_file_loaded(self, file_path: str):
        """Handle file loaded event - update status bar."""
        try:
            track_name = Path(file_path).stem
            self._update_status_bar_track_info(track_name)
            # Don't set state to "stopped" here - let actual player state events drive status updates
            # The player might auto-resume playback after loading
        except Exception as e:
            logger.error(f"Error updating status bar on file load: {e}")
    
    def _on_state_changed(self, state: str):
        """Handle player state change - update status bar."""
        try:
            logger.debug(f"_on_state_changed called with state: {state}")
            self._update_status_bar_state(state)
        except Exception as e:
            logger.error(f"Error updating status bar on state change: {e}")
    
    def _on_error_occurred(self, error_msg: str):
        """Handle player error - update status bar."""
        try:
            self._update_status_bar_state("error")
            if self.status_bar:
                self.status_bar.showMessage(f"Error: {error_msg}", 5000)
        except Exception as e:
            logger.error(f"Error updating status bar on error: {e}")
    
    def _on_position_changed(self, position: float):
        """Handle position change - update status bar progress."""
        try:
            self._current_position = position
            self._update_status_bar_progress(self._current_position, self._current_duration)
        except Exception as e:
            logger.error(f"Error updating status bar on position change: {e}")
    
    def _on_duration_changed(self, duration: float):
        """Handle duration change - update status bar progress."""
        try:
            self._current_duration = duration
            self._update_status_bar_progress(self._current_position, self._current_duration)
        except Exception as e:
            logger.error(f"Error updating status bar on duration change: {e}")
    
    def _add_files_to_playlist(self):
        """Handle add files to playlist request."""
        logger.info("Add files to playlist requested")
        try:
            # Create dialog for multiple file/folder selection
            dialog = QFileDialog(self)
            dialog.setWindowTitle(self.translation_manager.translate("dialogs.add_to_playlist.title"))
            dialog.setNameFilter("TAF Files (*.taf);;All Files (*)")
            dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            
            # Add folder selection option
            folder_button = dialog.addAction(self.translation_manager.translate("dialogs.open_file.select_folder"))
            folder_button.triggered.connect(lambda: self._add_folder_to_playlist())
            
            if dialog.exec() == QFileDialog.DialogCode.Accepted:
                file_paths = dialog.selectedFiles()
                if file_paths:
                    logger.info(f"Adding {len(file_paths)} file(s) to playlist: {file_paths}")
                    
                    # Always use player controller for playlist operations
                    if self.player_controller and hasattr(self.player_controller, 'add_files_to_playlist'):
                        success = self.player_controller.add_files_to_playlist(file_paths)
                        if not success:
                            logger.error("Failed to add files via player controller")
                            self._show_error_message("Error", "Failed to add files to playlist")
                    else:
                        logger.error("Player controller not available")
                        self._show_error_message("Error", "Player not initialized")
                        
        except Exception as e:
            logger.error(f"Error in add files dialog: {e}", exc_info=True)
            self._show_error_message("Error", f"Error adding files: {e}")
    
    def _add_folder_to_playlist(self):
        """Handle add folder to playlist request."""
        try:
            import os

            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Folder to Add to Playlist"
            )

            if folder_path:
                logger.info(f"Adding folder to playlist: {folder_path}")
                
                # Find TAF files in folder
                taf_files = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith('.taf'):
                            taf_files.append(os.path.join(root, file))

                if taf_files:
                    if self.player_controller and hasattr(self.player_controller, 'add_files_to_playlist'):
                        try:
                            self.player_controller.add_files_to_playlist(taf_files)
                        except Exception as e:
                            logger.error(f"Failed to add folder to playlist: {e}")
                            self._show_error_message("Error", f"Failed to add folder: {e}")
                    else:
                        # Fallback: load as new playlist
                        self._load_multiple_files(taf_files)
                else:
                    self._show_error_message("No TAF Files", "No TAF files found in the selected folder.")
                    
        except Exception as e:
            logger.error(f"Error in add folder to playlist: {e}")
            self._show_error_message("Error", f"Error adding folder: {e}")
    
    def _remove_multiple_tracks(self, indices: list):
        """Handle removal of multiple tracks from playlist."""
        logger.info(f"Removing {len(indices)} track(s) from playlist: {indices}")
        
        if not self.player_controller:
            logger.warning("No player controller available for track removal")
            return
        
        try:
            # Remove tracks in reverse order to maintain correct indices
            for index in sorted(indices, reverse=True):
                if hasattr(self.player_controller, 'remove_track'):
                    self.player_controller.remove_track(index)
                else:
                    logger.warning(f"Player controller does not support remove_track for index {index}")
                    
        except Exception as e:
            logger.error(f"Failed to remove multiple tracks: {e}")
            self._show_error_message("Error", f"Failed to remove tracks: {e}")
    
    def _on_playlist_name_changed(self, new_name: str):
        """Handle playlist name change from the info panel."""
        logger.info(f"Playlist name changed to: {new_name}")
        
        # Update the playlist manager with the new name
        if self.player_controller and hasattr(self.player_controller, 'taf_player'):
            if (self.player_controller.taf_player and 
                hasattr(self.player_controller.taf_player, 'playlist_manager') and
                self.player_controller.taf_player.playlist_manager):
                
                self.player_controller.taf_player.playlist_manager._playlist_name = new_name
                logger.debug(f"Updated playlist manager with new name: {new_name}")
    
    def get_gui_registry(self):
        """Get the GUI component registry for plugins."""
        return self._gui_registry
    
    def update_plugin_menus(self):
        """Update menus with plugin-registered items."""
        if not self._gui_registry:
            return
        
        try:
            # Get registered menu items
            menu_items = self._gui_registry.get_all("menu_items")
            
            for item_id, item_config in menu_items.items():
                menu_name = item_config.get("menu", "Tools")
                label = item_config.get("label", item_id)
                callback = item_config.get("callback")
                shortcut = item_config.get("shortcut")
                tooltip = item_config.get("tooltip")
                
                # Find menu by key (case-insensitive)
                target_menu = None
                menu_key = menu_name.lower()
                if menu_key in self._menus:
                    target_menu = self._menus[menu_key]
                
                if not target_menu:
                    logger.warning(f"Menu '{menu_name}' not found for plugin item '{item_id}'. Available menus: {list(self._menus.keys())}")
                    continue
                
                # Create action
                action = QAction(label, self)
                if callback:
                    action.triggered.connect(callback)
                if shortcut:
                    action.setShortcut(shortcut)
                if tooltip:
                    action.setToolTip(tooltip)
                
                # Add to menu
                target_menu.addAction(action)
                logger.debug(f"Added plugin menu item: {label} to {menu_name}")
            
        except Exception as e:
            logger.error(f"Failed to update plugin menus: {e}")
    
    def update_plugin_tabs(self):
        """Update tab widget with plugin-registered tabs."""
        if not self._gui_registry or not self.tab_widget:
            return
        
        try:
            # Get registered tabs
            tabs = self._gui_registry.get_all("tabs")
            
            for tab_id, tab_config in tabs.items():
                label = tab_config.get("label", tab_id)
                widget = tab_config.get("widget")
                tooltip = tab_config.get("tooltip")
                icon = tab_config.get("icon")
                
                if not widget:
                    logger.warning(f"Tab '{tab_id}' has no widget specified")
                    continue
                
                # Add tab to tab widget
                index = self.tab_widget.addTab(widget, label)
                
                if tooltip:
                    self.tab_widget.setTabToolTip(index, tooltip)
                
                if icon:
                    self.tab_widget.setTabIcon(index, icon)
                
                logger.debug(f"Added plugin tab: {label}")
            
        except Exception as e:
            logger.error(f"Failed to update plugin tabs: {e}")
    
    def _on_plugin_loaded(self, event) -> None:
        """
        Handle plugin loaded event - refresh GUI if GUI plugin.
        
        Args:
            event: PluginLoadedEvent
        """
        try:
            logger.debug(f"Plugin loaded event received: {event.plugin_id}")
            # Plugin components will be registered when enabled
        except Exception as e:
            logger.error(f"Error handling plugin loaded event: {e}")
    
    def _on_plugin_unloaded(self, event) -> None:
        """
        Handle plugin unloaded event - remove GUI components.
        
        Args:
            event: PluginUnloadedEvent
        """
        try:
            logger.debug(f"Plugin unloaded event received: {event.plugin_id}")
            # Components are automatically removed by ComponentRegistry.unregister_all_for_plugin
            # But we may need to refresh menus if they were affected
            self._refresh_plugin_menus_if_needed()
        except Exception as e:
            logger.error(f"Error handling plugin unloaded event: {e}")
    
    def _on_plugin_enabled(self, event) -> None:
        """
        Handle plugin enabled event - add GUI components.
        
        Args:
            event: PluginEnabledEvent
        """
        try:
            logger.info(f"Plugin enabled: {event.plugin_id} - refreshing GUI")
            self._refresh_plugin_menus_if_needed()
        except Exception as e:
            logger.error(f"Error handling plugin enabled event: {e}")
    
    def _on_plugin_disabled(self, event) -> None:
        """
        Handle plugin disabled event - remove GUI components.
        
        Args:
            event: PluginDisabledEvent
        """
        try:
            logger.info(f"Plugin disabled: {event.plugin_id} - refreshing GUI")
            self._refresh_plugin_menus_if_needed()
        except Exception as e:
            logger.error(f"Error handling plugin disabled event: {e}")
    
    def _on_plugin_gui_components_changed(self, event) -> None:
        """
        Handle plugin GUI components changed event - refresh affected components.
        
        Args:
            event: PluginGuiComponentsChangedEvent
        """
        try:
            logger.info(f"Plugin GUI components changed: {event.plugin_id}, type: {event.change_type}")
            
            # Refresh menus if menu_items affected
            if 'menu_items' in event.component_categories:
                self._refresh_plugin_menus()
            
            # Refresh tabs if tabs affected
            if 'tabs' in event.component_categories:
                self._refresh_plugin_tabs()
            
            # Refresh toolbars if toolbar_buttons affected
            if 'toolbar_buttons' in event.component_categories:
                self._refresh_plugin_toolbars()
                
        except Exception as e:
            logger.error(f"Error handling plugin GUI components changed event: {e}")
    
    def _refresh_plugin_menus_if_needed(self) -> None:
        """Refresh plugin menus if plugin manager is available."""
        if self.plugin_manager and self._gui_registry:
            self._refresh_plugin_menus()
    
    def _refresh_plugin_menus(self) -> None:
        """Refresh all plugin menu items."""
        try:
            logger.debug("Refreshing plugin menus")
            
            # Remove all plugin menu items from Plugins menu
            if 'plugins' in self._menus:
                plugins_menu = self._menus['plugins']
                plugins_menu.clear()
                
                # Re-add standard items
                plugins_menu.addAction(self._actions.get('plugins_manage', 
                    self._create_manage_plugins_action()))
                plugins_menu.addSeparator()
            
            # Re-add plugin menu items
            self.update_plugin_menus()
            
            logger.debug("Plugin menus refreshed")
        except Exception as e:
            logger.error(f"Error refreshing plugin menus: {e}")
    
    def _refresh_plugin_tabs(self) -> None:
        """Refresh all plugin tabs."""
        try:
            logger.debug("Refreshing plugin tabs")
            # For now, we'll need app restart for tab changes
            # Future enhancement: dynamic tab add/remove
            logger.warning("Dynamic plugin tab refresh not yet implemented - restart required")
        except Exception as e:
            logger.error(f"Error refreshing plugin tabs: {e}")
    
    def _refresh_plugin_toolbars(self) -> None:
        """Refresh all plugin toolbar buttons."""
        try:
            logger.debug("Refreshing plugin toolbars")
            # For now, we'll need app restart for toolbar changes
            # Future enhancement: dynamic toolbar button add/remove
            logger.warning("Dynamic plugin toolbar refresh not yet implemented - restart required")
        except Exception as e:
            logger.error(f"Error refreshing plugin toolbars: {e}")
    
    def _create_manage_plugins_action(self) -> QAction:
        """Create the manage plugins menu action."""
        action = QAction(self._translate("menu", "plugins_manage"), self)
        action.triggered.connect(self.open_plugin_manager)
        return action
    
    def cleanup(self):
        """Cleanup resources."""
        logger.debug("Cleaning up main window resources...")
        
        if self.about_dialog:
            self.about_dialog.close()
        
        if self.player_controller:
            self.player_controller.cleanup()