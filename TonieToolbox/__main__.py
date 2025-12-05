#!/usr/bin/python3
"""
Main entry point for the TonieToolbox package.

"""

from .core.app import TonieToolboxApp
def main() -> int:
    """Entry point for the TonieToolbox application."""
    app = TonieToolboxApp()
    return app.run()
if __name__ == "__main__":
    import sys
    sys.exit(main())