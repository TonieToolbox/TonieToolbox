#!/usr/bin/env python3
"""
About dialog for TonieToolbox PyQt6 GUI.
"""
try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QPushButton, QTextEdit, QFrame, QSizePolicy)
    from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
    from PyQt6.QtGui import QFont, QPixmap, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object
    QVBoxLayout = object
    QHBoxLayout = object
    QLabel = object
    QPushButton = object
    QTextEdit = object
    QFrame = object
    QSizePolicy = object
    Qt = object
    pyqtSignal = lambda: None
    QFont = object
    QPixmap = object

from ..... import __version__
from TonieToolbox.core.utils import get_logger
from TonieToolbox.core.config.application_constants import ICON_PNG_BASE64
import base64

logger = get_logger(__name__)


class AboutDialog(QDialog):
    """
    About dialog showing application information.
    """
    
    def __init__(self, parent=None, translation_manager=None):
        """
        Initialize the about dialog.
        
        Args:
            parent: Parent widget
            translation_manager: Translation manager for i18n
        """
        super().__init__(parent)
        
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not available")
        
        self.translation_manager = translation_manager
        
        self._setup_dialog()
        self._create_ui()
        self._connect_signals()
        
        logger.debug("About dialog initialized")
    
    def tr(self, *keys, **kwargs) -> str:
        """
        Translate text using the translation manager.
        
        Args:
            *keys: Translation key path
            **kwargs: Format parameters
            
        Returns:
            Translated text
        """
        if self.translation_manager:
            return self.translation_manager.translate(*keys, **kwargs)
        else:
            # Fallback to English
            fallback_translations = {
                ('about', 'title'): 'About TonieToolbox',
                ('about', 'description'): 'A tool for converting audio files to Toniebox compatible format and interacting with TeddyCloud.',
                ('about', 'version'): 'Version: {version}',
                ('about', 'author'): 'Author: Quentendo64',
                ('about', 'license'): 'License: GPL-3.0',
                ('about', 'website'): 'Website: https://github.com/TonieToolbox/TonieToolbox',
                ('about', 'close'): 'Close'
            }
            key_tuple = tuple(keys)
            text = fallback_translations.get(key_tuple, '.'.join(keys))
            if kwargs:
                try:
                    text = text.format(**kwargs)
                except (KeyError, ValueError):
                    pass
            return text
    
    def _setup_dialog(self):
        """Setup dialog properties."""
        self.setWindowTitle(self.tr("about", "title"))
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self.resize(600, 500)
        
        # Center on parent if available
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
    
    def _create_ui(self):
        """Create the dialog UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header section
        header_frame = self._create_header()
        main_layout.addWidget(header_frame)
        
        # Description section
        description_frame = self._create_description()
        main_layout.addWidget(description_frame)
        
        # Information section
        info_frame = self._create_info()
        main_layout.addWidget(info_frame)
        
        # Spacer
        main_layout.addStretch()
        
        # Button section
        button_frame = self._create_buttons()
        main_layout.addWidget(button_frame)
    
    def _create_header(self) -> QFrame:
        """Create the header section with title, icon, and version."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Application logo
        logo_label = QLabel()
        try:
            # Decode base64 logo
            logo_data = base64.b64decode(ICON_PNG_BASE64)
            pixmap = QPixmap()
            pixmap.loadFromData(logo_data)
            # Scale to 64x64 for about dialog
            scaled_pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception as e:
            logger.warning(f"Could not load application logo: {e}")
            # If logo fails to load, just continue without it
            logo_label.hide()
        
        # Text content container
        text_container = QFrame()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(10, 0, 0, 0)
        text_layout.setSpacing(5)
        
        # Application name
        title_label = QLabel("TonieToolbox")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setProperty("class", "title")
        
        # Version
        version_label = QLabel(self.tr("about", "version", version=__version__))
        version_font = QFont()
        version_font.setPointSize(12)
        version_label.setFont(version_font)
        version_label.setProperty("class", "subtitle")
        
        # Logo attribution
        attribution_label = QLabel('<a href="https://www.flaticon.com/free-animated-icons/parrot" title="parrot animated icons">Parrot animated icons created by Freepik - Flaticon</a>')
        attribution_label.setOpenExternalLinks(True)
        attribution_font = QFont()
        attribution_font.setPointSize(8)
        attribution_label.setFont(attribution_font)
        attribution_label.setProperty("class", "attribution")
        attribution_label.setWordWrap(True)
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(version_label)
        text_layout.addWidget(attribution_label)
        
        # Add logo and text to main layout
        layout.addWidget(logo_label)
        layout.addWidget(text_container)
        layout.addStretch()
        
        return frame
    
    def _create_description(self) -> QFrame:
        """Create the description section."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Description text
        desc_label = QLabel(self.tr("about", "description"))
        desc_label.setWordWrap(True)
        desc_font = QFont()
        desc_font.setPointSize(11)
        desc_label.setFont(desc_font)
        
        layout.addWidget(desc_label)
        
        return frame
    
    def _create_info(self) -> QFrame:
        """Create the information section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Information items
        info_items = [
            self.tr("about", "author"),
            self.tr("about", "license"),
            self.tr("about", "website")
        ]
        
        for item in info_items:
            label = QLabel(item)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            if "github.com" in item:
                label.setOpenExternalLinks(True)
                # Make it look like a link
                label.setText(f'<a href="https://github.com/TonieToolbox/TonieToolbox" style="color: #3daee9; text-decoration: none;">{item}</a>')
            
            layout.addWidget(label)
        
        return frame
    
    def _create_buttons(self) -> QFrame:
        """Create the button section."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addStretch()
        
        # Close button
        close_button = QPushButton(self.tr("about", "close"))
        close_button.setMinimumSize(100, 32)
        close_button.setProperty("primary", True)
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        
        layout.addWidget(close_button)
        
        return frame
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # ESC key to close
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)