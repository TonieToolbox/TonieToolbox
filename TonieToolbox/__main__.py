#!/usr/bin/python3
"""
Main entry point for the TonieToolbox package.
"""

import sys
from .core.app import TonieToolboxApp


def main() -> int:
    """
    Entry point for the TonieToolbox CLI application.
    
    Uses command-line arguments to determine mode (CLI or GUI via --gui flag).
    
    Returns:
        Exit code: 0 for success, non-zero for errors
    """
    app = TonieToolboxApp()
    return app.run()


def main_gui() -> int:
    """
    Entry point for the TonieToolbox GUI application.
    
    Automatically launches in GUI mode without requiring --gui flag.
    This entry point suppresses the console window on Windows when
    launched via the gui-scripts entry point.
    
    Returns:
        Exit code: 0 for success, non-zero for errors
    """
    app = TonieToolboxApp()
    # Force GUI mode by injecting --gui argument
    return app.run(['--gui'])


if __name__ == "__main__":
    sys.exit(main())