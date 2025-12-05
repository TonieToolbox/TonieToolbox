# TonieToolbox PyQt6 GUI Module

## Overview

The PyQt6 GUI module provides a modern, feature-rich graphical user interface for TonieToolbox as an alternative to the existing tkinter-based GUI. It features a clean architecture with comprehensive theming, internationalization support, and robust error handling.

## Features

### ✨ Core Features
- **Modern Qt-based Interface**: Clean, responsive UI built with PyQt6
- **Player Functionality**: Full audio player with controls, progress tracking, and file information display  
- **About Dialog**: Application information and metadata display
- **Graceful Fallback**: Automatically falls back to tkinter GUI when PyQt6 is unavailable

### 🎨 Clean Architecture & Separation of Concerns
- **Component-based Architecture**: Modular, reusable UI components
- **MVC Pattern**: Clear separation between models, views, and controllers
- **Event-driven Communication**: Decoupled components using signals/slots and event bus
- **Dependency Injection**: Loose coupling between components

### 🌍 Internationalization (I18n) Support
- **JSON-based Translations**: Easy-to-edit translation files
- **Dynamic Language Switching**: Change language without restart
- **Built-in Languages**: English and German included
- **Extensible**: Simple to add new languages

### 🎭 Comprehensive Theme System
- **Dynamic Theme Loading**: Load themes from directories at runtime
- **QSS-based Styling**: Powerful Qt stylesheet theming
- **Default Dark Theme**: Modern dark theme with blue accents
- **Theme Metadata**: Rich theme information and versioning

### 🛡️ Robust Error Handling & Threading
- **Thread-safe Operations**: Background processing with Qt threading
- **Graceful Error Recovery**: Comprehensive error handling and logging
- **Non-blocking UI**: Audio operations don't freeze the interface
- **Resource Management**: Proper cleanup and memory management

## Architecture

```
TonieToolbox/core/qt_gui/
├── __init__.py                    # Main module exports
├── app/                          # Application coordination
│   ├── application.py             # Main Qt application class
│   └── main_window.py             # Primary window implementation
├── components/                    # UI components
│   ├── base/                      # Base component classes
│   ├── player/                    # Player-specific components
│   └── about/                     # About dialog
├── themes/                        # Theme management
│   ├── manager.py                 # Theme manager and dynamic loading
│   ├── base.py                    # Base theme class
│   └── default/                   # Built-in default theme
├── i18n/                         # Internationalization
│   ├── manager.py                 # Translation management
│   ├── translations/              # Translation files
│   └── utils.py                   # Translation utilities
├── controllers/                   # Business logic controllers
│   └── player_controller.py       # Qt-adapted player controller
└── utils/                        # Qt utilities
    ├── events.py                  # Event system bridge
    └── threading.py               # Threading utilities
```

## Installation

### Option 1: Install with Qt Support (Recommended)
```bash
pip install -e ".[qt]"
```

### Option 2: Install PyQt6 Manually
```bash
pip install PyQt6>=6.10.0
pip install -e .
```

## Usage

### Command Line
The Qt GUI launches automatically when PyQt6 is available:

```bash
# Launch GUI (Qt if available, tkinter fallback)
tonietoolbox --gui

# Load a specific TAF file
tonietoolbox --gui input.taf
```

### Programmatic Usage
```python
from TonieToolbox.core.qt_gui import qt_gui_player, PYQT6_AVAILABLE

if PYQT6_AVAILABLE:
    # Launch Qt GUI
    qt_gui_player()
    
    # Or with a file
    qt_gui_player("path/to/file.taf", auto_play=True)
```

## Extending the GUI

### Adding New Themes

1. **Create theme directory**:
   ```
   themes/my_theme/
   ├── __init__.py
   ├── theme.py
   └── styles.qss
   ```

2. **Implement theme class**:
   ```python
   # themes/my_theme/theme.py
   from TonieToolbox.core.qt_gui.themes.base import BaseTheme
   
   class MyTheme(BaseTheme):
       def __init__(self):
           super().__init__("my_theme", "My Theme")
       
       @property
       def description(self) -> str:
           return "My custom theme"
       
       # Implement required methods...
   ```

3. **Register theme**:
   ```python
   from TonieToolbox.core.qt_gui.themes.manager import get_theme_manager
   
   theme_manager = get_theme_manager()
   theme_manager.load_theme_from_directory(Path("themes/my_theme"))
   ```

### Adding New Languages

1. **Create translation file**:
   ```bash
   # Create es_ES.json for Spanish
   cp i18n/translations/en_US.json i18n/translations/es_ES.json
   ```

2. **Translate content**:
   ```json
   {
     "app": {
       "title": "TonieToolbox",
       "description": "Herramienta para convertir archivos..."
     }
   }
   ```

3. **Load translation**:
   ```python
   from TonieToolbox.core.qt_gui.i18n.manager import get_translation_manager
   
   translation_manager = get_translation_manager()
   translation_manager.load_external_translation("es_ES", Path("es_ES.json"))
   ```

### Adding New Components

1. **Create component class**:
   ```python
   from TonieToolbox.core.qt_gui.components.base.component import QtBaseFrame
   
   class MyComponent(QtBaseFrame):
       def _setup_ui(self):
           # Create your UI here
           pass
   ```

2. **Use in main window**:
   ```python
   my_component = MyComponent(parent=self)
   layout.addWidget(my_component)
   ```

## Component API

### Base Component
All components inherit from `QtBaseComponent`:

```python
class MyComponent(QtBaseComponent):
    # Required methods
    def _create_layout(self):
        """Create the widget layout"""
        pass
    
    def _setup_ui(self):
        """Setup the user interface"""
        pass
    
    # Optional methods
    def _setup_component(self):
        """Setup component-specific functionality"""
        pass
    
    def _connect_signals(self):
        """Connect signals and slots"""
        pass
    
    def _cleanup_component(self):
        """Component-specific cleanup"""
        pass
```

### Translation API
Use the translation system in components:

```python
# In components
text = self.tr("player", "controls", "play")  # Gets "Play" button text
formatted = self.tr("player", "info", "duration", duration="5:23")

# Standalone usage
from TonieToolbox.core.qt_gui.i18n.utils import tr
text = tr("app", "title")  # Gets app title
```

### Theming API
Apply themes dynamically:

```python
from TonieToolbox.core.qt_gui.themes.manager import get_theme_manager

theme_manager = get_theme_manager()

# List available themes
themes = theme_manager.get_available_themes()

# Apply theme
theme_manager.apply_theme("default")

# Get theme info
info = theme_manager.get_theme_info("default")
```

## Configuration

### Theme Configuration
Themes support comprehensive styling through QSS:

```css
/* Global styling */
QApplication {
    background-color: #2b2b2b;
    color: #ffffff;
}

/* Button styling with states */
QPushButton {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

/* Custom properties */
QPushButton[primary="true"] {
    background-color: #3daee9;
}
```

### Translation Configuration
Translations use hierarchical JSON structure:

```json
{
  "player": {
    "controls": {
      "play": "Play",
      "pause": "Pause"
    },
    "info": {
      "duration": "Duration: {duration}",
      "chapters": "Chapters: {count}"
    }
  }
}
```

## Development

### Running Tests
```bash
python test_qt_gui.py
```

### Debug Mode
Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Contributing
1. Follow the existing component architecture
2. Add translations for new UI text
3. Include proper error handling
4. Write tests for new functionality
5. Update documentation

## Requirements

- **Python 3.12+**
- **PyQt6 6.10.0+** (optional, graceful fallback)
- **Existing TonieToolbox dependencies**

## License

GPL-3.0 (same as TonieToolbox)

## Notes

- The Qt GUI automatically falls back to the tkinter GUI when PyQt6 is unavailable
- All components are designed to be thread-safe and handle errors gracefully
- The architecture supports easy extension with new themes, languages, and components
- Performance is optimized with background threading and efficient resource management