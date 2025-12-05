#!/usr/bin/env python3
"""
Translation utilities for easy access to translations.
"""
from typing import Optional
from .manager import get_translation_manager


def tr(*keys, language: Optional[str] = None, **kwargs) -> str:
    """
    Convenient translation function.
    
    Args:
        *keys: Key path for translation
        language: Override language (optional)
        **kwargs: Format parameters
        
    Returns:
        Translated string
        
    Example:
        tr('app', 'title')  # Gets app.title translation
        tr('player', 'duration', duration='5:23')  # With formatting
    """
    manager = get_translation_manager()
    result = manager.translate(*keys, language=language, **kwargs)
    return result


# Alias for shorter usage
_ = tr