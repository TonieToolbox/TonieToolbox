#!/usr/bin/env python3
"""
Base component classes for PyQt6 GUI architecture.
Provides foundation for all UI components with consistent patterns.
"""
from abc import ABC, abstractmethod
from typing import Optional, Any

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object
    QVBoxLayout = object
    QHBoxLayout = object
    QObject = object
    pyqtSignal = lambda: None

from ...i18n.utils import tr
from TonieToolbox.core.utils import get_logger
from TonieToolbox.core.events import get_event_bus, LanguageChangedEvent

logger = get_logger(__name__)


class QtBaseComponent(QWidget):
    """
    Abstract base class for all Qt GUI components.
    Provides common functionality and enforces consistent patterns.
    """
    
    # Signals
    error_occurred = pyqtSignal(str)
    state_changed = pyqtSignal(str, object)
    
    def __init__(self, parent=None, translation_manager=None, **kwargs):
        """
        Initialize the component.
        
        Args:
            parent: Parent widget
            translation_manager: Translation manager for i18n
            **kwargs: Additional configuration options
        """
        super().__init__(parent)
        
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not available")
        
        # Dependency injection
        self.translation_manager = translation_manager
        self._event_bus = get_event_bus()
        
        # Component state
        self._initialized = False
        self._destroyed = False
        
        # Component configuration
        self.config = kwargs
        
        # Subscribe to language change events
        self._event_bus.subscribe(LanguageChangedEvent, self._on_language_changed)
        
        # Initialize the component
        self._initialize()
    
    def _initialize(self):
        """Internal initialization - creates widget and sets up component."""
        try:
            self._create_layout()
            self._setup_ui()
            self._setup_component()
            self._connect_signals()
            
            self._initialized = True
            logger.debug(f"Initialized Qt component: {self.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qt component {self.__class__.__name__}: {e}")
            self.error_occurred.emit(str(e))
            raise
    
    @abstractmethod
    def _create_layout(self):
        """Create the widget layout. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _setup_ui(self):
        """Setup the user interface. Must be implemented by subclasses."""
        pass
    
    def _setup_component(self):
        """Setup component-specific functionality. Override in subclasses."""
        pass
    
    def _connect_signals(self):
        """Connect signals and slots. Override in subclasses."""
        pass
    
    def tr(self, *keys, **kwargs) -> str:
        """
        Translate text using the translation manager.
        
        Args:
            *keys: Translation key path
            **kwargs: Format parameters
            
        Returns:
            Translated text
        """
        return tr(*keys, **kwargs)
    
    def retranslate_ui(self):
        """
        Retranslate UI elements when language changes.
        Override this method in subclasses to update translated text.
        """
        pass
    
    def _on_language_changed(self, event: LanguageChangedEvent):
        """
        Handle language changed event from event bus.
        
        Args:
            event: Language changed event
        """
        self.retranslate_ui()
    
    def emit_error(self, message: str):
        """
        Emit an error signal.
        
        Args:
            message: Error message
        """
        logger.error(f"Component error in {self.__class__.__name__}: {message}")
        self.error_occurred.emit(message)
    
    def emit_state_change(self, state: str, data: Any = None):
        """
        Emit a state change signal.
        
        Args:
            state: State name
            data: Optional state data
        """
        logger.debug(f"State change in {self.__class__.__name__}: {state}")
        self.state_changed.emit(state, data)
    
    def set_enabled_safe(self, enabled: bool):
        """
        Safely set the enabled state of the component.
        
        Args:
            enabled: Whether component should be enabled
        """
        try:
            self.setEnabled(enabled)
        except Exception as e:
            logger.error(f"Failed to set enabled state for {self.__class__.__name__}: {e}")
    
    def set_visible_safe(self, visible: bool):
        """
        Safely set the visible state of the component.
        
        Args:
            visible: Whether component should be visible
        """
        try:
            self.setVisible(visible)
        except Exception as e:
            logger.error(f"Failed to set visible state for {self.__class__.__name__}: {e}")
    
    def cleanup(self):
        """Cleanup component resources."""
        if self._destroyed:
            return
        
        logger.debug(f"Cleaning up Qt component: {self.__class__.__name__}")
        
        try:
            # Unsubscribe from language change events
            self._event_bus.unsubscribe(LanguageChangedEvent, self._on_language_changed)
            
            self._cleanup_component()
            self._destroyed = True
        except Exception as e:
            logger.error(f"Error during cleanup of {self.__class__.__name__}: {e}")
    
    def _cleanup_component(self):
        """Component-specific cleanup. Override in subclasses."""
        pass
    
    def is_initialized(self) -> bool:
        """
        Check if component is initialized.
        
        Returns:
            True if component is initialized
        """
        return self._initialized
    
    def is_destroyed(self) -> bool:
        """
        Check if component is destroyed.
        
        Returns:
            True if component is destroyed
        """
        return self._destroyed
    
    def closeEvent(self, event):
        """Handle close event."""
        self.cleanup()
        super().closeEvent(event)


class QtBaseFrame(QtBaseComponent):
    """
    Base frame component with vertical layout.
    Convenience class for simple frame-based components.
    """
    
    def __init__(self, parent=None, **kwargs):
        """Initialize the frame."""
        self.main_layout = None
        
        # Extract translation_manager from kwargs before passing to super
        translation_manager = kwargs.pop('translation_manager', None)
        
        super().__init__(parent, translation_manager=translation_manager, **kwargs)
    
    def _create_layout(self):
        """Create vertical layout for the frame."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
    
    def _setup_ui(self):
        """Setup UI - to be implemented by subclasses."""
        pass


class QtBaseDialog(QtBaseComponent):
    """
    Base dialog component.
    Provides common dialog functionality and patterns.
    """
    
    # Additional signals for dialogs
    accepted = pyqtSignal()
    rejected = pyqtSignal()
    
    def __init__(self, parent=None, **kwargs):
        """Initialize the dialog."""
        super().__init__(parent, **kwargs)
        
        # Set dialog properties
        if PYQT6_AVAILABLE:
            self.setWindowModality(2)  # Qt.WindowModal
    
    def accept(self):
        """Accept the dialog."""
        self.accepted.emit()
        self.close()
    
    def reject(self):
        """Reject the dialog."""
        self.rejected.emit()
        self.close()
    
    def exec(self):
        """Execute the dialog modally."""
        if PYQT6_AVAILABLE:
            self.show()
            self.activateWindow()
            self.raise_()
            return True
        return False