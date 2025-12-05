#!/usr/bin/env python3
"""
GUI dependency management for TonieToolbox.
Centralizes detection and management of GUI libraries like PyQt6.
"""
import sys
from typing import Optional, Dict, Any, Tuple
from ..utils import get_logger

logger = get_logger(__name__)


class GUIDependencyInfo:
    """Information about a GUI dependency."""
    
    def __init__(self, name: str, available: bool = False, version: Optional[str] = None, 
                 error: Optional[str] = None, modules: Optional[Dict[str, Any]] = None):
        self.name = name
        self.available = available
        self.version = version
        self.error = error
        self.modules = modules or {}


class GUIDependencyManager:
    """Centralized management of GUI library dependencies."""
    
    def __init__(self):
        """Initialize the GUI dependency manager."""
        self.logger = logger
        self._pyqt6_info: Optional[GUIDependencyInfo] = None
        self._tkinter_info: Optional[GUIDependencyInfo] = None
        
    def check_pyqt6(self) -> GUIDependencyInfo:
        """
        Check PyQt6 availability and return detailed information.
        
        Returns:
            GUIDependencyInfo: Complete information about PyQt6 availability
        """
        if self._pyqt6_info is not None:
            return self._pyqt6_info
            
        try:
            # Import core PyQt6 modules
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QCoreApplication, pyqtSignal, Qt
            from PyQt6.QtGui import QAction, QIcon, QPixmap, QFont
            
            # Get version information
            import PyQt6.QtCore
            version = getattr(PyQt6.QtCore, 'PYQT_VERSION_STR', 'Unknown')
            
            modules = {
                'QApplication': QApplication,
                'QCoreApplication': QCoreApplication,
                'pyqtSignal': pyqtSignal,
                'Qt': Qt,
                'QAction': QAction,
                'QIcon': QIcon,
                'QPixmap': QPixmap,
                'QFont': QFont,
            }
            
            self._pyqt6_info = GUIDependencyInfo(
                name='PyQt6',
                available=True,
                version=version,
                modules=modules
            )
            
            self.logger.debug(f"PyQt6 is available, version: {version}")
            
        except ImportError as e:
            self._pyqt6_info = GUIDependencyInfo(
                name='PyQt6',
                available=False,
                error=str(e)
            )
            
            self.logger.debug(f"PyQt6 is not available: {e}")
            
        return self._pyqt6_info
    
    def check_tkinter(self) -> GUIDependencyInfo:
        """
        Check tkinter availability and return detailed information.
        
        Returns:
            GUIDependencyInfo: Complete information about tkinter availability
        """
        if self._tkinter_info is not None:
            return self._tkinter_info
            
        try:
            import tkinter as tk
            from tkinter import ttk, messagebox, filedialog
            
            # Get version
            version = tk.TkVersion if hasattr(tk, 'TkVersion') else 'Unknown'
            
            modules = {
                'tk': tk,
                'ttk': ttk,
                'messagebox': messagebox,
                'filedialog': filedialog,
            }
            
            self._tkinter_info = GUIDependencyInfo(
                name='tkinter',
                available=True,
                version=str(version),
                modules=modules
            )
            
            self.logger.debug(f"tkinter is available, version: {version}")
            
        except ImportError as e:
            self._tkinter_info = GUIDependencyInfo(
                name='tkinter',
                available=False,
                error=str(e)
            )
            
            self.logger.debug(f"tkinter is not available: {e}")
            
        return self._tkinter_info
    
    def get_best_gui_option(self) -> Tuple[str, GUIDependencyInfo]:
        """
        Determine the best available GUI option.
        
        Returns:
            Tuple[str, GUIDependencyInfo]: (gui_type, dependency_info)
            gui_type is 'pyqt6', 'tkinter', or 'none'
        """
        # Check PyQt6 first (preferred)
        pyqt6_info = self.check_pyqt6()
        if pyqt6_info.available:
            return 'pyqt6', pyqt6_info
            
        # Fall back to tkinter
        tkinter_info = self.check_tkinter()
        if tkinter_info.available:
            return 'tkinter', tkinter_info
            
        # No GUI available
        return 'none', GUIDependencyInfo(
            name='None',
            available=False,
            error="No GUI libraries available"
        )
    
    def create_mock_classes(self, gui_type: str) -> Dict[str, Any]:
        """
        Create mock classes for when GUI libraries are not available.
        
        Args:
            gui_type: The type of GUI library to mock ('pyqt6' or 'tkinter')
            
        Returns:
            Dict[str, Any]: Dictionary of mock classes and functions
        """
        if gui_type == 'pyqt6':
            return {
                # Core classes
                'QApplication': object,
                'QWidget': object,
                'QMainWindow': object,
                'QDialog': object,
                'QFrame': object,
                'QObject': object,
                
                # Layout classes
                'QVBoxLayout': object,
                'QHBoxLayout': object,
                'QGridLayout': object,
                
                # Widget classes
                'QLabel': object,
                'QPushButton': object,
                'QLineEdit': object,
                'QTextEdit': object,
                'QListWidget': object,
                'QListWidgetItem': object,
                'QComboBox': object,
                'QCheckBox': object,
                'QProgressBar': object,
                'QSlider': object,
                'QScrollArea': object,
                'QSplitter': object,
                'QStatusBar': object,
                'QMenuBar': object,
                'QMenu': object,
                'QFileDialog': object,
                'QMessageBox': object,
                
                # Core functionality
                'Qt': object,
                'pyqtSignal': lambda *args, **kwargs: None,
                'pyqtSlot': lambda *args, **kwargs: lambda f: f,
                'QTimer': object,
                'QThread': object,
                'QByteArray': object,
                
                # Graphics classes
                'QAction': object,
                'QIcon': object,
                'QPixmap': object,
                'QFont': object,
                'QColor': object,
                'QBrush': object,
                'QPen': object,
                'QPalette': object,
                
                # Events and input
                'QKeySequence': object,
                'QDropEvent': object,
                'QDragEnterEvent': object,
                'QMimeData': object,
                'QDrag': object,
                
                # Selection and model
                'QAbstractItemView': object,
                'QModelIndex': object,
                'QSizePolicy': object,
            }
        elif gui_type == 'tkinter':
            return {
                'tk': object,
                'ttk': object,
                'messagebox': object,
                'filedialog': object,
                'Tk': object,
                'Toplevel': object,
                'Frame': object,
                'Label': object,
                'Button': object,
                'Entry': object,
                'Text': object,
                'Listbox': object,
                'Combobox': object,
                'Checkbutton': object,
                'Scale': object,
                'Scrollbar': object,
                'Canvas': object,
                'Menu': object,
            }
        else:
            return {}
    
    def install_gui_dependency(self, gui_type: str = 'pyqt6') -> bool:
        """
        Attempt to install a GUI dependency.
        
        Args:
            gui_type: The GUI library to install ('pyqt6' or 'tkinter')
            
        Returns:
            bool: True if installation was successful
        """
        if gui_type == 'pyqt6':
            try:
                import subprocess
                import sys
                
                self.logger.info("Attempting to install PyQt6...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', 'PyQt6>=6.10.0'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info("PyQt6 installation successful")
                    # Reset cached info to force re-check
                    self._pyqt6_info = None
                    return self.check_pyqt6().available
                else:
                    self.logger.error(f"PyQt6 installation failed: {result.stderr}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Failed to install PyQt6: {e}")
                return False
                
        elif gui_type == 'tkinter':
            self.logger.warning("tkinter should be included with Python. If not available, reinstall Python with tkinter support.")
            return False
            
        return False


# Global GUI dependency manager instance
_gui_dependency_manager: Optional[GUIDependencyManager] = None


def get_gui_dependency_manager() -> GUIDependencyManager:
    """Get the global GUI dependency manager instance."""
    global _gui_dependency_manager
    if _gui_dependency_manager is None:
        _gui_dependency_manager = GUIDependencyManager()
    return _gui_dependency_manager


# Convenience helper functions
def check_pyqt6_available() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if PyQt6 is available.
    
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (available, version, error)
    """
    manager = get_gui_dependency_manager()
    info = manager.check_pyqt6()
    return info.available, info.version, info.error


def get_pyqt6_modules() -> Optional[Dict[str, Any]]:
    """
    Get PyQt6 modules if available.
    
    Returns:
        Optional[Dict[str, Any]]: PyQt6 modules or None if not available
    """
    manager = get_gui_dependency_manager()
    info = manager.check_pyqt6()
    return info.modules if info.available else None


def get_gui_mock_classes(gui_type: str = 'pyqt6') -> Dict[str, Any]:
    """
    Get mock classes for when GUI libraries are not available.
    
    Args:
        gui_type: The GUI library type to mock
        
    Returns:
        Dict[str, Any]: Mock classes and functions
    """
    manager = get_gui_dependency_manager()
    return manager.create_mock_classes(gui_type)