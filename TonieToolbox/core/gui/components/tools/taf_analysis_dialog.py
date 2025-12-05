#!/usr/bin/env python3
"""
TAF Analysis Dialog for TonieToolbox PyQt6 GUI.
Displays detailed analysis results of TAF files.
"""
try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QGroupBox, QGridLayout, QTabWidget, QWidget, QSizePolicy
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QDialog = object
    
from pathlib import Path
from typing import Dict, Any, Optional
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class TafAnalysisDialog(QDialog):
    """
    Dialog for displaying TAF file analysis results.
    
    Emitted Signals:
        None
    """
    
    def __init__(
        self,
        file_path: str,
        header_info: tuple,
        parent: Optional[QWidget] = None,
        translation_manager=None
    ):
        """
        Initialize the TAF analysis dialog.
        
        Args:
            file_path: Path to the analyzed TAF file
            header_info: Tuple containing header information from get_header_info_cli
            parent: Parent widget
            translation_manager: Translation manager for i18n
        """
        super().__init__(parent)
        
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not available")
        
        self.file_path = Path(file_path)
        self.header_info = header_info
        self.translation_manager = translation_manager
        
        # Unpack header info
        (self.header_size, self.tonie_header, self.file_size, self.audio_size,
         self.sha1sum, self.opus_head_found, self.opus_version, self.channel_count,
         self.sample_rate, self.bitstream_serial_no, self.opus_comments, self.valid) = header_info
        
        self._setup_dialog()
        self._create_ui()
        
        logger.debug(f"TAF Analysis dialog initialized for {self.file_path.name}")
    
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
            fallback = {
                ('taf_analysis', 'title'): 'TAF File Analysis',
                ('taf_analysis', 'file_info'): 'File Information',
                ('taf_analysis', 'header_info'): 'Header Information',
                ('taf_analysis', 'audio_info'): 'Audio Information',
                ('taf_analysis', 'opus_comments'): 'Opus Comments',
                ('taf_analysis', 'chapters'): 'Chapters',
                ('taf_analysis', 'file_name'): 'File Name:',
                ('taf_analysis', 'file_size'): 'File Size:',
                ('taf_analysis', 'header_size'): 'Header Size:',
                ('taf_analysis', 'audio_size'): 'Audio Size:',
                ('taf_analysis', 'sha1'): 'SHA1 Hash:',
                ('taf_analysis', 'opus_version'): 'Opus Version:',
                ('taf_analysis', 'channels'): 'Channels:',
                ('taf_analysis', 'sample_rate'): 'Sample Rate:',
                ('taf_analysis', 'serial_number'): 'Bitstream Serial:',
                ('taf_analysis', 'chapter_count'): 'Chapter Count:',
                ('taf_analysis', 'close'): 'Close',
                ('taf_analysis', 'bytes'): '{size} bytes',
                ('taf_analysis', 'mb'): '{size:.2f} MB',
                ('taf_analysis', 'hz'): '{rate} Hz',
                ('taf_analysis', 'mono'): 'Mono',
                ('taf_analysis', 'stereo'): 'Stereo',
                ('taf_analysis', 'invalid_file'): 'Invalid TAF File',
                ('taf_analysis', 'error_message'): 'The file could not be analyzed. It may not be a valid TAF file.',
            }
            key_tuple = tuple(keys)
            text = fallback.get(key_tuple, '.'.join(keys))
            if kwargs:
                try:
                    text = text.format(**kwargs)
                except (KeyError, ValueError):
                    pass
            return text
    
    def _setup_dialog(self):
        """Setup dialog properties."""
        self.setWindowTitle(f"{self.tr('taf_analysis', 'title')} - {self.file_path.name}")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        # Set window flags
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
    
    def _create_ui(self):
        """Create the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Check if file was valid
        if not self.valid:
            self._create_error_ui(main_layout)
            return
        
        # Create tab widget for different sections
        tab_widget = QTabWidget()
        
        # File & Header Info Tab
        tab_widget.addTab(self._create_file_info_tab(), self.tr('taf_analysis', 'file_info'))
        
        # Audio Info Tab
        tab_widget.addTab(self._create_audio_info_tab(), self.tr('taf_analysis', 'audio_info'))
        
        # Opus Comments Tab
        if self.opus_comments:
            tab_widget.addTab(self._create_opus_comments_tab(), self.tr('taf_analysis', 'opus_comments'))
        
        # Chapters Tab
        if self.tonie_header and len(self.tonie_header.chapterPages) > 0:
            tab_widget.addTab(self._create_chapters_tab(), self.tr('taf_analysis', 'chapters'))
        
        main_layout.addWidget(tab_widget)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton(self.tr('taf_analysis', 'close'))
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_error_ui(self, layout: QVBoxLayout):
        """Create error UI when file is invalid."""
        error_label = QLabel(self.tr('taf_analysis', 'invalid_file'))
        error_label.setStyleSheet("color: red; font-weight: bold; font-size: 14pt;")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(error_label)
        
        message_label = QLabel(self.tr('taf_analysis', 'error_message'))
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton(self.tr('taf_analysis', 'close'))
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def _create_file_info_tab(self) -> QWidget:
        """Create the file information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # File info group
        file_group = QGroupBox(self.tr('taf_analysis', 'file_info'))
        file_layout = QGridLayout()
        
        row = 0
        
        # File name
        file_layout.addWidget(QLabel(self.tr('taf_analysis', 'file_name')), row, 0)
        file_layout.addWidget(QLabel(self.file_path.name), row, 1)
        row += 1
        
        # File size
        file_layout.addWidget(QLabel(self.tr('taf_analysis', 'file_size')), row, 0)
        file_size_text = f"{self.tr('taf_analysis', 'bytes', size=self.file_size)} ({self.tr('taf_analysis', 'mb', size=self.file_size / 1024 / 1024)})"
        file_layout.addWidget(QLabel(file_size_text), row, 1)
        row += 1
        
        file_layout.setColumnStretch(1, 1)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Header info group
        header_group = QGroupBox(self.tr('taf_analysis', 'header_info'))
        header_layout = QGridLayout()
        
        row = 0
        
        # Header size
        header_layout.addWidget(QLabel(self.tr('taf_analysis', 'header_size')), row, 0)
        header_layout.addWidget(QLabel(self.tr('taf_analysis', 'bytes', size=self.header_size)), row, 1)
        row += 1
        
        # Audio size
        header_layout.addWidget(QLabel(self.tr('taf_analysis', 'audio_size')), row, 0)
        audio_size_text = f"{self.tr('taf_analysis', 'bytes', size=self.audio_size)} ({self.tr('taf_analysis', 'mb', size=self.audio_size / 1024 / 1024)})"
        header_layout.addWidget(QLabel(audio_size_text), row, 1)
        row += 1
        
        # SHA1 hash
        header_layout.addWidget(QLabel(self.tr('taf_analysis', 'sha1')), row, 0)
        sha1_label = QLabel(self.sha1sum.hexdigest() if self.sha1sum else "N/A")
        sha1_label.setFont(QFont("Courier"))
        sha1_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(sha1_label, row, 1)
        row += 1
        
        # Chapter count
        header_layout.addWidget(QLabel(self.tr('taf_analysis', 'chapter_count')), row, 0)
        chapter_count = len(self.tonie_header.chapterPages) if self.tonie_header else 0
        header_layout.addWidget(QLabel(str(chapter_count)), row, 1)
        row += 1
        
        header_layout.setColumnStretch(1, 1)
        header_group.setLayout(header_layout)
        layout.addWidget(header_group)
        
        layout.addStretch()
        return widget
    
    def _create_audio_info_tab(self) -> QWidget:
        """Create the audio information tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        audio_group = QGroupBox(self.tr('taf_analysis', 'audio_info'))
        audio_layout = QGridLayout()
        
        row = 0
        
        # Opus version
        audio_layout.addWidget(QLabel(self.tr('taf_analysis', 'opus_version')), row, 0)
        audio_layout.addWidget(QLabel(str(self.opus_version)), row, 1)
        row += 1
        
        # Channels
        audio_layout.addWidget(QLabel(self.tr('taf_analysis', 'channels')), row, 0)
        channel_text = self.tr('taf_analysis', 'mono') if self.channel_count == 1 else self.tr('taf_analysis', 'stereo')
        audio_layout.addWidget(QLabel(f"{self.channel_count} ({channel_text})"), row, 1)
        row += 1
        
        # Sample rate
        audio_layout.addWidget(QLabel(self.tr('taf_analysis', 'sample_rate')), row, 0)
        audio_layout.addWidget(QLabel(self.tr('taf_analysis', 'hz', rate=self.sample_rate)), row, 1)
        row += 1
        
        # Serial number
        audio_layout.addWidget(QLabel(self.tr('taf_analysis', 'serial_number')), row, 0)
        audio_layout.addWidget(QLabel(str(self.bitstream_serial_no)), row, 1)
        row += 1
        
        audio_layout.setColumnStretch(1, 1)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        layout.addStretch()
        return widget
    
    def _create_opus_comments_tab(self) -> QWidget:
        """Create the Opus comments tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier", 10))
        
        # Format comments
        comments_text = ""
        for key, value in self.opus_comments.items():
            comments_text += f"{key}: {value}\n"
        
        text_edit.setPlainText(comments_text)
        layout.addWidget(text_edit)
        
        return widget
    
    def _create_chapters_tab(self) -> QWidget:
        """Create the chapters tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier", 10))
        
        # Format chapters
        chapters_text = f"Total Chapters: {len(self.tonie_header.chapterPages)}\n\n"
        
        for idx, page in enumerate(self.tonie_header.chapterPages, 1):
            chapters_text += f"Chapter {idx}: Page {page}\n"
        
        text_edit.setPlainText(chapters_text)
        layout.addWidget(text_edit)
        
        return widget
