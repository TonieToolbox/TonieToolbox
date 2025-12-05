#!/usr/bin/env python3
"""
Utilities for GUI component development.
Provides centralized imports and mock classes for PyQt6 components.
"""
from typing import Dict, Any, Tuple
from ...dependencies.gui import get_gui_dependency_manager


def import_pyqt6_modules(*module_names: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Import PyQt6 modules using centralized dependency management.
    
    Args:
        *module_names: Names of PyQt6 modules/classes to import
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (available, modules_dict)
        
    Example:
        available, modules = import_pyqt6_modules(
            'QWidget', 'QVBoxLayout', 'QPushButton', 'pyqtSignal'
        )
        if available:
            QWidget = modules['QWidget']
            QVBoxLayout = modules['QVBoxLayout']
            QPushButton = modules['QPushButton'] 
            pyqtSignal = modules['pyqtSignal']
        else:
            # Use mock classes
            QWidget = object
            QVBoxLayout = object
            QPushButton = object
            pyqtSignal = lambda: None
    """
    gui_manager = get_gui_dependency_manager()
    pyqt6_info = gui_manager.check_pyqt6()
    
    if pyqt6_info.available:
        # Return requested modules
        modules = {}
        for module_name in module_names:
            if module_name in pyqt6_info.modules:
                modules[module_name] = pyqt6_info.modules[module_name]
            else:
                # Try to import dynamically if not in cache
                try:
                    if module_name.startswith('Q') or module_name in ('pyqtSignal', 'pyqtSlot'):
                        # Try QtWidgets first
                        try:
                            import PyQt6.QtWidgets as QtWidgets
                            if hasattr(QtWidgets, module_name):
                                modules[module_name] = getattr(QtWidgets, module_name)
                                continue
                        except ImportError:
                            pass
                        
                        # Try QtCore
                        try:
                            import PyQt6.QtCore as QtCore
                            if hasattr(QtCore, module_name):
                                modules[module_name] = getattr(QtCore, module_name)
                                continue
                        except ImportError:
                            pass
                        
                        # Try QtGui
                        try:
                            import PyQt6.QtGui as QtGui
                            if hasattr(QtGui, module_name):
                                modules[module_name] = getattr(QtGui, module_name)
                                continue
                        except ImportError:
                            pass
                            
                        # Fallback to mock
                        modules[module_name] = object
                    else:
                        modules[module_name] = object
                        
                except Exception:
                    modules[module_name] = object
        
        return True, modules
    else:
        # Return mock classes
        mock_classes = gui_manager.create_mock_classes('pyqt6')
        modules = {}
        for module_name in module_names:
            modules[module_name] = mock_classes.get(module_name, object)
        
        return False, modules


def get_pyqt6_component_base():
    """
    Get the base class for PyQt6 components with error handling.
    
    Returns:
        Tuple[bool, class, dict]: (available, base_class, required_modules)
    """
    available, modules = import_pyqt6_modules(
        'QWidget', 'QVBoxLayout', 'QHBoxLayout', 'pyqtSignal', 'Qt'
    )
    
    base_class = modules['QWidget']
    
    return available, base_class, modules


def create_component_imports_block() -> str:
    """
    Generate a standardized import block for PyQt6 components.
    This is mainly for documentation/reference purposes.
    
    Returns:
        str: Template import block code
    """
    return '''
# Use centralized GUI dependency management
from TonieToolbox.core.gui.utils.imports import import_pyqt6_modules

PYQT6_AVAILABLE, modules = import_pyqt6_modules(
    'QWidget', 'QVBoxLayout', 'QHBoxLayout', 'QLabel', 'QPushButton', 
    'pyqtSignal', 'Qt', 'QFrame', 'QSizePolicy'
)

# Extract modules
QWidget = modules['QWidget']
QVBoxLayout = modules['QVBoxLayout'] 
QHBoxLayout = modules['QHBoxLayout']
QLabel = modules['QLabel']
QPushButton = modules['QPushButton']
pyqtSignal = modules['pyqtSignal']
Qt = modules['Qt']
QFrame = modules['QFrame']
QSizePolicy = modules['QSizePolicy']
'''