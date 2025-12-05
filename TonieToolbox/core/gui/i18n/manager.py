#!/usr/bin/env python3
"""
Translation manager for PyQt6 GUI internationalization.
Uses event bus for clean architecture communication.
"""
import json
from typing import Dict, Optional, Any
from pathlib import Path

try:
    from PyQt6.QtCore import QObject
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    
    class QObject:
        def __init__(self):
            pass

from TonieToolbox.core.utils import get_logger
from TonieToolbox.core.events import get_event_bus, LanguageChangedEvent

logger = get_logger(__name__)


class TranslationManager(QObject):
    """
    Centralized translation management for the PyQt6 application.
    Supports dynamic language switching and easy translation loading.
    Uses event bus for decoupled communication.
    """
    
    def __init__(self):
        """Initialize the translation manager."""
        super().__init__()
        
        self._translations: Dict[str, Dict] = {}
        self._current_language: Optional[str] = None
        self._fallback_language = "en_US"
        self._event_bus = get_event_bus()
        
        # Get translations directory
        self._translations_dir = Path(__file__).parent / "translations"
        
        # Load built-in translations
        self._load_builtin_translations()
        
        logger.info("Translation manager initialized")
    
    def _load_builtin_translations(self):
        """Load built-in translation files."""
        try:
            # Load English (default)
            self._load_translation_file("en_US")
            
            # Load German
            self._load_translation_file("de_DE")
            
            # Note: Don't set default language here to avoid re-entrant get_translation_manager() calls
            # The language will be set by get_translation_manager() after instance creation
            
            logger.debug("Built-in translations loaded")
        except Exception as e:
            logger.error(f"Failed to load built-in translations: {e}")
    
    def _load_translation_file(self, language_code: str) -> bool:
        """
        Load a translation file.
        
        Args:
            language_code: Language code (e.g., 'en_US', 'de_DE')
            
        Returns:
            True if translation was loaded successfully
        """
        try:
            translation_file = self._translations_dir / f"{language_code}.json"
            
            if not translation_file.exists():
                logger.warning(f"Translation file not found: {translation_file}")
                return False
            
            with open(translation_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            
            self._translations[language_code] = translations
            
            logger.info(f"Translation loaded: {language_code}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load translation {language_code}: {e}")
            return False
    
    def load_translation_from_dict(self, language_code: str, translations: Dict):
        """
        Load translations from a dictionary.
        
        Args:
            language_code: Language code
            translations: Translation dictionary
        """
        try:
            self._translations[language_code] = translations
            logger.info(f"Translation loaded from dict: {language_code}")
        except Exception as e:
            logger.error(f"Failed to load translation from dict {language_code}: {e}")
    
    def get_available_languages(self) -> Dict[str, str]:
        """
        Get list of available languages.
        
        Returns:
            Dictionary mapping language codes to display names
        """
        languages = {}
        for lang_code in self._translations.keys():
            # Try to get the display name from the translation itself
            display_name = self.translate("languages", lang_code, language=lang_code)
            if display_name == f"languages.{lang_code}":  # Fallback if not found
                display_name = lang_code
            languages[lang_code] = display_name
        return languages
    
    def set_language(self, language_code: str) -> bool:
        """
        Set the current language.
        
        Args:
            language_code: Language code to set
            
        Returns:
            True if language was set successfully
        """
        if language_code not in self._translations:
            logger.error(f"Language not available: {language_code}")
            return False
        
        old_language = self._current_language
        self._current_language = language_code
        
        # Publish event to event bus for decoupled communication
        self._event_bus.publish(LanguageChangedEvent(
            new_language=language_code,
            old_language=old_language
        ))
        
        logger.info(f"Language changed from {old_language} to {language_code}")
        return True
    
    def get_current_language(self) -> Optional[str]:
        """
        Get the current language code.
        
        Returns:
            Current language code or None
        """
        return self._current_language
    
    def translate(self, *keys, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key path to localized text.
        
        Args:
            *keys: Key path (e.g., 'app', 'title' for app.title OR 'app.title')
            language: Override language (uses current if None)
            **kwargs: Format parameters for string formatting
            
        Returns:
            Translated and formatted string
        """
        # Determine language to use
        target_language = language or self._current_language or self._fallback_language
        
        # Handle dot-separated keys (e.g., "dialogs.open_file.title")
        # Split if single key contains dots
        if len(keys) == 1 and '.' in keys[0]:
            keys = tuple(keys[0].split('.'))
        
        # Get translation
        translation_dict = self._translations.get(target_language, {})
        
        # Navigate to the translation using keys
        result = translation_dict
        key_path = []
        
        for key in keys:
            key_path.append(str(key))
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                # Fallback to English if available
                if target_language != self._fallback_language:
                    fallback_dict = self._translations.get(self._fallback_language, {})
                    fallback_result = fallback_dict
                    
                    for fallback_key in keys:
                        if isinstance(fallback_result, dict) and fallback_key in fallback_result:
                            fallback_result = fallback_result[fallback_key]
                        else:
                            fallback_result = None
                            break
                    
                    if fallback_result and isinstance(fallback_result, str):
                        result = fallback_result
                        logger.debug(f"Using fallback translation for: {'.'.join(key_path)}")
                        break
                
                # If no translation found, return key path
                result = '.'.join(key_path)
                logger.warning(f"Translation not found: {result}")
                break
        
        # Ensure we have a string result
        if not isinstance(result, str):
            result = '.'.join(key_path)
            logger.warning(f"Translation result is not a string: {result}")
        
        # Apply formatting if provided
        if kwargs:
            try:
                result = result.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Translation formatting failed for '{result}': {e}")
        
        return result
    
    def load_external_translation(self, language_code: str, file_path: Path) -> bool:
        """
        Load an external translation file.
        
        Args:
            language_code: Language code
            file_path: Path to JSON translation file
            
        Returns:
            True if loaded successfully
        """
        try:
            if not file_path.exists():
                logger.error(f"Translation file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            
            self._translations[language_code] = translations
            
            logger.info(f"External translation loaded: {language_code} from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load external translation {file_path}: {e}")
            return False
    
    def scan_for_translations(self, directory: Path):
        """
        Scan a directory for translation files and load them.
        
        Args:
            directory: Directory to scan for *.json files
        """
        if not directory.exists():
            logger.warning(f"Translation directory does not exist: {directory}")
            return
        
        logger.info(f"Scanning for translations in: {directory}")
        
        for file_path in directory.glob("*.json"):
            # Extract language code from filename
            language_code = file_path.stem
            try:
                self.load_external_translation(language_code, file_path)
            except Exception as e:
                logger.error(f"Error loading translation from {file_path}: {e}")
    
    def load_plugin_translation(
        self, 
        plugin_id: str, 
        language_code: str, 
        translation_data: Dict[str, Any]
    ) -> bool:
        """
        Load plugin translations into namespaced structure.
        
        Plugin translations are stored under the plugin_id namespace to avoid conflicts.
        Example: plugin_id="tonies_viewer", translation becomes accessible via
        tr("tonies_viewer", "viewer", "title")
        
        Args:
            plugin_id: Plugin identifier (namespace)
            language_code: Language code (e.g., 'en_US', 'de_DE')
            translation_data: Translation dictionary
            
        Returns:
            True if loaded successfully
        """
        try:
            # Ensure language exists in translations
            if language_code not in self._translations:
                self._translations[language_code] = {}
            
            # Merge plugin translations under plugin_id namespace
            if plugin_id not in self._translations[language_code]:
                self._translations[language_code][plugin_id] = {}
            
            # Deep merge translation data
            self._merge_translation_dict(
                self._translations[language_code][plugin_id],
                translation_data
            )
            
            logger.info(f"Plugin translation loaded: {plugin_id} ({language_code})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin translation {plugin_id}: {e}")
            return False
    
    def unload_plugin_translations(self, plugin_id: str) -> None:
        """
        Remove all translations for a plugin across all languages.
        
        Args:
            plugin_id: Plugin identifier
        """
        removed_count = 0
        for language_code in self._translations:
            if plugin_id in self._translations[language_code]:
                del self._translations[language_code][plugin_id]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Unloaded translations for plugin: {plugin_id} ({removed_count} languages)")
    
    def _merge_translation_dict(self, target: Dict, source: Dict) -> None:
        """
        Deep merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._merge_translation_dict(target[key], value)
            else:
                # Overwrite or add new key
                target[key] = value


# Global translation manager instance
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager() -> TranslationManager:
    """
    Get the global translation manager instance.
    
    Returns:
        TranslationManager singleton instance
    """
    global _translation_manager
    
    if _translation_manager is None:
        _translation_manager = TranslationManager()
        # Language will be set by the application after determining initial language
        # Don't set a default here to avoid confusing "None -> en_US -> actual_language" logs
    
    return _translation_manager