#!/usr/bin/python3
"""
V2 format handler for tonies.custom.json operations.
Handles tonies JSON data in v2 format with full feature parity.
"""
import os
import json
import time
import locale
import re
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseFormatHandler
from ...utils import get_logger
from ...config.application_constants import LANGUAGE_MAPPING, GENRE_MAPPING

logger = get_logger(__name__)


class ToniesJsonV2Handler(BaseFormatHandler):
    """Handler for tonies.custom.json operations using v2 format."""
    
    def __init__(self, repository=None):
        """
        Initialize the v2 handler.
        
        Args:
            repository: TeddyCloud repository interface (ITeddyCloudRepository)
                       for server operations. Can be None for offline mode.
        """    
        super().__init__(repository)
        self.logger = logger

    def load_from_server(self) -> bool:
        """
        Load tonies.custom.json from the TeddyCloud server via repository.
        
        Returns:
            bool: True if successful, False otherwise
        """          
        if self.repository is None:
            self.logger.error("Cannot load from server: no repository provided")
            return False
        try:
            result = self.repository.get_tonies_custom_json()            
            if result is not None:
                self.custom_json = result
                self.is_loaded = True
                self.logger.info("Successfully loaded tonies.custom.json with %d entries", len(self.custom_json))
                return True
            else:
                self.logger.error("Failed to load tonies.custom.json from server")
                return False
        except Exception as e:
            self.logger.error("Error loading tonies.custom.json: %s", e)
            return False

    def load_from_file(self, file_path: str) -> bool:
        """
        Load tonies.custom.json from a local file.
        Args:
            file_path (str): Path to the tonies.custom.json file
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                self.logger.info("Loading tonies.custom.json from file: %s", file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.custom_json = data
                        self.is_loaded = True
                        self.logger.info("Successfully loaded tonies.custom.json with %d entries", len(self.custom_json))
                        return True
                    else:
                        self.logger.error("Invalid tonies.custom.json format in file, expected list")
                        return False
            else:
                self.logger.info("tonies.custom.json file not found, starting with empty list")
                self.custom_json = []
                self.is_loaded = True
                return True
        except Exception as e:
            self.logger.error("Error loading tonies.custom.json from file: %s", e)
            return False

    def save_to_file(self, file_path: str) -> bool:
        """
        Save tonies.custom.json to a local file.
        Args:
            file_path (str): Path where to save the tonies.custom.json file
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_loaded:
            self.logger.error("Cannot save tonies.custom.json: data not loaded")
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            self.logger.info("Saving tonies.custom.json to file: %s", file_path)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.custom_json, f, indent=2, ensure_ascii=False)
            self.logger.info("Successfully saved tonies.custom.json to file")
            return True
        except Exception as e:
            self.logger.error("Error saving tonies.custom.json to file: %s", e)
            return False

    def find_entry_by_hash(self, taf_hash: str) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[int]]:
        """
        Find an entry by hash value in v2 format.
        Args:
            taf_hash (str): Hash value to search for
        Returns:
            tuple: (entry_dict, entry_index, data_index) or (None, None, None) if not found
        """
        for entry_idx, entry in enumerate(self.custom_json):
            if 'data' not in entry:
                continue
            for data_idx, data_item in enumerate(entry['data']):
                if 'ids' in data_item:
                    for id_entry in data_item['ids']:
                        if id_entry.get('hash') == taf_hash:
                            return entry, entry_idx, data_idx
        return None, None, None

    def find_entry_by_series_episodes(self, series: str, episodes: str) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[int]]:
        """
        Find an entry by series and episodes in v2 format.
        Args:
            series (str): Series name to search for
            episodes (str): Episodes to search for
        Returns:
            tuple: (entry_dict, entry_index, data_index) or (None, None, None) if not found
        """
        for entry_idx, entry in enumerate(self.custom_json):
            if 'data' not in entry:
                continue
            for data_idx, data_item in enumerate(entry['data']):
                if (data_item.get('series') == series and 
                    data_item.get('episode') == episodes):
                    return entry, entry_idx, data_idx
        return None, None, None

    def add_entry_from_taf(self, taf_file: str, input_files: List[str], artwork_url: Optional[str] = None) -> bool:
        """
        Add an entry to the custom JSON from a TAF file in v2 format.
        Args:
            taf_file (str): Path to the TAF file
            input_files (list[str]): List of input audio files used to create the TAF
            artwork_url (str | None): URL of the uploaded artwork (if any)
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_loaded:
            self.logger.error("Cannot add entry: tonies.custom.json not loaded")
            return False
        
        try:
            self.logger.info("Adding entry for %s to tonies.custom.json", taf_file)
            
            # Extract metadata from input files
            metadata = self._extract_metadata_from_files(input_files)
            
            # Extract hash and timestamp from TAF file header
            from ...analysis.header import get_header_info
            with open(taf_file, 'rb') as f:
                header_size, tonie_header, file_size, audio_size, sha1, opus_head_found, \
                opus_version, channel_count, sample_rate, bitstream_serial_no, opus_comments = get_header_info(f)                
                taf_hash = tonie_header.dataHash.hex().upper()
                timestamp = bitstream_serial_no
                self.logger.debug("Extracted hash: %s, timestamp: %s", taf_hash, timestamp)

            taf_size = os.path.getsize(taf_file)
            series = metadata.get('albumartist', metadata.get('artist', 'Unknown Artist'))
            episode = metadata.get('album', os.path.splitext(os.path.basename(taf_file))[0])
            track_desc = metadata.get('track_descriptions', [])
            language = self._determine_language(metadata)
            category = self._determine_category(metadata)
            runtime = self._calculate_runtime(input_files)

            new_id_entry = {
                "audio-id": timestamp,
                "hash": taf_hash,
                "size": taf_size,
                "tracks": len(track_desc),
                "confidence": 1
            }

            # Check for existing entry by hash
            existing_entry, entry_idx, data_idx = self.find_entry_by_hash(taf_hash)
            if existing_entry:
                self.logger.info("Found existing entry with the same hash, updating it")
                data_item = existing_entry['data'][data_idx]
                if artwork_url:
                    data_item['image'] = artwork_url
                if track_desc:
                    data_item['track-desc'] = track_desc
                return True

            # Check for existing entry by series/episodes
            existing_entry, entry_idx, data_idx = self.find_entry_by_series_episodes(series, episode)
            if existing_entry:
                self.logger.info("Found existing entry with same series/episode, adding hash")
                data_item = existing_entry['data'][data_idx]
                if 'ids' not in data_item:
                    data_item['ids'] = []
                data_item['ids'].append(new_id_entry)
                if artwork_url:
                    data_item['image'] = artwork_url
                return True

            # Create new entry
            self.logger.debug("Creating new entry")
            article_number = self._generate_article_number()
            
            new_data_item = {
                "series": series,
                "episode": episode,
                "article": article_number,
                "language": language,
                "category": category,
                "track-desc": track_desc,
                "release": int(time.time()),
                "runtime": runtime,
                "image": artwork_url if artwork_url else "",
                "ids": [new_id_entry]
            }

            new_entry = {
                "data": [new_data_item]
            }

            self.custom_json.append(new_entry)
            self.logger.info("Successfully added new entry for %s", taf_file)
            return True

        except Exception as e:
            self.logger.error("Error adding entry for %s: %s", taf_file, e)
            return False

    def _extract_metadata_from_files(self, input_files: List[str]) -> Dict[str, Any]:
        """Extract metadata from audio files."""
        from ...media.tags import get_media_tag_service
        
        tag_service = get_media_tag_service(self.logger)
        metadata = {}
        track_descriptions = []
        
        for file_path in input_files:
            tags = tag_service.get_file_tags(file_path)
            if 'title' in tags:
                track_descriptions.append(tags['title'])
            else:
                filename = os.path.splitext(os.path.basename(file_path))[0]
                track_descriptions.append(filename)
            
            for tag_name, tag_value in tags.items():
                if tag_name not in metadata:
                    metadata[tag_name] = tag_value
        
        metadata['track_descriptions'] = track_descriptions
        return metadata

    def _determine_language(self, metadata: Dict[str, Any]) -> str:
        """Determine language from metadata or system locale."""
        if 'language' in metadata:
            lang_value = metadata['language'].lower().strip()
            if lang_value in LANGUAGE_MAPPING:
                return LANGUAGE_MAPPING[lang_value]
        
        try:
            system_lang, _ = locale.getdefaultlocale()
            if system_lang:
                lang_code = system_lang.split('_')[0].lower()
                if lang_code in LANGUAGE_MAPPING:
                    return LANGUAGE_MAPPING[lang_code]
        except Exception:
            pass
        
        return 'de-de'

    def _determine_category(self, metadata: Dict[str, Any]) -> str:
        """Determine category in v2 format."""
        if 'genre' in metadata:
            genre_value = metadata['genre'].lower().strip()
            if any(keyword in genre_value for keyword in ['musik', 'song', 'music', 'lied']):
                return "music"
            elif any(keyword in genre_value for keyword in ['hörspiel', 'audio play', 'hörbuch', 'audiobook']):
                return "Hörspiele & Hörbücher"
            elif any(keyword in genre_value for keyword in ['märchen', 'fairy', 'tales']):
                return "Märchen"
            elif any(keyword in genre_value for keyword in ['wissen', 'knowledge', 'learn']):
                return "Wissen & Hörmagazine"
            elif any(keyword in genre_value for keyword in ['schlaf', 'sleep', 'meditation']):
                return "Schlaflieder & Entspannung"
        return "Hörspiele & Hörbücher"

    def _generate_article_number(self) -> str:
        """Generate unique article number."""
        highest_num = 80000000  # Start from a high number for custom content
        
        for entry in self.custom_json:
            if 'data' not in entry:
                continue
            for data_item in entry['data']:
                article = data_item.get('article', '')
                if article.startswith('tt-42'):
                    try:
                        num_part = article.replace('tt-42', '')
                        num = int(num_part)
                        highest_num = max(highest_num, num)
                    except (ValueError, TypeError):
                        pass
        
        return f"tt-42{highest_num + 1:010d}"

    def _calculate_runtime(self, input_files: List[str]) -> int:
        """Calculate total runtime in minutes from audio files."""
        try:
            import mutagen
            total_runtime_seconds = 0
            
            for file_path in input_files:
                if not os.path.exists(file_path):
                    continue
                try:
                    audio = mutagen.File(file_path)
                    if audio and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                        total_runtime_seconds += int(audio.info.length)
                except Exception as e:
                    self.logger.warning("Error processing file %s: %s", file_path, e)
            
            return round(total_runtime_seconds / 60)
        except ImportError:
            self.logger.warning("Mutagen library not available, cannot calculate runtime")
            return 0
        except Exception as e:
            self.logger.error("Error calculating runtime: %s", e)
            return 0