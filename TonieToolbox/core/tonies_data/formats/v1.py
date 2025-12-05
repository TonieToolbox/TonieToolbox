#!/usr/bin/python3
"""
V1 format handler for tonies.custom.json operations.
Handles tonies JSON data in v1 format with full feature parity.
"""
import os
import json
import time
import locale
import re
import hashlib
import mutagen
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseFormatHandler
from ...utils import get_logger
from ...config.application_constants import LANGUAGE_MAPPING, GENRE_MAPPING

logger = get_logger(__name__)


class ToniesJsonV1Handler(BaseFormatHandler):
    """Handler for tonies.custom.json operations using v1 format."""
    
    def __init__(self, repository=None):
        """
        Initialize the v1 handler.
        
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
                if len(result) > 0 and "data" in result[0]:
                    self.logger.debug("Converting v2 format from server to v1 format")
                    self.custom_json = self._convert_v2_to_v1(result)
                else:
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
                        if len(data) > 0 and "data" in data[0]:
                            self.logger.debug("Converting v2 format from file to v1 format")
                            self.custom_json = self._convert_v2_to_v1(data)
                        else:
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

    def find_entry_by_hash(self, taf_hash: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """
        Find an entry by hash value.
        Args:
            taf_hash (str): Hash value to search for
        Returns:
            tuple: (entry_dict, entry_index) or (None, None) if not found
        """
        for i, entry in enumerate(self.custom_json):
            if 'hash' in entry:
                for hash_value in entry['hash']:
                    if hash_value == taf_hash:
                        return entry, i
        return None, None

    def find_entry_by_series_episodes(self, series: str, episodes: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """
        Find an entry by series and episodes.
        Args:
            series (str): Series name to search for
            episodes (str): Episodes to search for
        Returns:
            tuple: (entry_dict, entry_index) or (None, None) if not found
        """
        for i, entry in enumerate(self.custom_json):
            if entry.get('series') == series and entry.get('episodes') == episodes:
                return entry, i
        return None, None

    def add_entry_from_taf(self, taf_file: str, input_files: List[str], artwork_url: Optional[str] = None) -> bool:
        """
        Add an entry to the custom JSON from a TAF file.
        If an entry with the same hash exists, it will be updated.
        If an entry with the same series+episodes exists, the new hash will be added to it.
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
            self.logger.debug("Extracted metadata: %s", metadata)
            
            # Extract hash and timestamp from TAF file header
            from ...analysis.header import get_header_info
            with open(taf_file, 'rb') as f:
                header_size, tonie_header, file_size, audio_size, sha1, opus_head_found, \
                opus_version, channel_count, sample_rate, bitstream_serial_no, opus_comments = get_header_info(f)                
                taf_hash = tonie_header.dataHash.hex().upper()
                timestamp = str(bitstream_serial_no)
                self.logger.debug("Extracted hash: %s, timestamp: %s", taf_hash, timestamp)

            # Extract series and episodes information
            series = metadata.get('albumartist', metadata.get('artist', 'Unknown Artist'))
            episodes = metadata.get('album', os.path.splitext(os.path.basename(taf_file))[0])
            copyright = metadata.get('copyright', '')
            
            # Extract year information
            year = self._extract_year_from_metadata(metadata, episodes, copyright)
            year_formatted = f"{year:04d}" if year and 1900 <= year <= 2099 else None
            
            # Generate title
            title = f"{series} - {year_formatted} - {episodes}" if year_formatted else f"{series} - {episodes}"
            
            # Extract other metadata
            tracks = metadata.get('track_descriptions', [])
            language = self._determine_language(metadata)
            category = self._determine_category_v1(metadata)

            # Check for existing entry by hash
            existing_entry, entry_idx = self.find_entry_by_hash(taf_hash)
            if existing_entry:
                self.logger.info("Found existing entry with the same hash, updating it")
                self._update_existing_entry(existing_entry, artwork_url, tracks, episodes, series)
                self.renumber_series_entries(series)
                return True

            # Check for existing entry by series/episodes
            existing_entry, entry_idx = self.find_entry_by_series_episodes(series, episodes)
            if existing_entry:
                self.logger.info("Found existing entry with the same series/episodes, adding hash to it")
                self._add_hash_to_existing_entry(existing_entry, taf_hash, timestamp, artwork_url)
                self.renumber_series_entries(series)
                return True

            # Create new entry
            self.logger.debug("No existing entry found, creating new entry")
            entry_no = self._generate_entry_no(series, episodes, year)
            model_number = self._generate_model_number()

            entry = {
                "no": entry_no,
                "model": model_number,
                "audio_id": [timestamp],
                "hash": [taf_hash],
                "title": title,
                "series": series,
                "episodes": episodes,
                "tracks": tracks,
                "release": timestamp,
                "language": language,
                "category": category,
                "pic": artwork_url if artwork_url else ""
            }

            self.custom_json.append(entry)
            self.logger.info("Successfully added entry for %s", taf_file)
            self.renumber_series_entries(series)
            return True

        except Exception as e:
            self.logger.error("Error adding entry for %s: %s", taf_file, e)
            return False

    def renumber_series_entries(self, series: str) -> None:
        """
        Re-sort and re-number all entries for a series by year (chronological),
        with entries without a year coming last.
        Args:
            series (str): Series name to renumber
        """
        series_entries = [entry for entry in self.custom_json if entry.get('series') == series]
        
        with_year = []
        without_year = []
        
        for entry in series_entries:
            year = self._extract_year_from_text(entry.get('title', ''))
            if not year:
                year = self._extract_year_from_text(entry.get('episodes', ''))
            
            if year:
                with_year.append((year, entry))
            else:
                without_year.append(entry)

        # Sort entries with year chronologically
        with_year.sort(key=lambda x: x[0])
        
        # Renumber all entries
        new_no = 1
        for _, entry in with_year:
            entry['no'] = str(new_no)
            new_no += 1
        
        for entry in without_year:
            entry['no'] = str(new_no)
            new_no += 1

    def _extract_year_from_metadata(self, metadata: Dict[str, Any], episodes: str, copyright: str) -> Optional[int]:
        """Extract year from metadata, episodes, or copyright."""
        year = None
        year_str = metadata.get('year', metadata.get('date', None))
        
        if year_str:
            try:
                year_match = re.search(r'(\d{4})', str(year_str))
                if year_match:
                    year = int(year_match.group(1))
                else:
                    year_val = int(year_str)
                    if 0 <= year_val <= 99:
                        if year_val <= 25:
                            year = 2000 + year_val
                        else:
                            year = 1900 + year_val
                    else:
                        year = year_val
            except (ValueError, TypeError):
                self.logger.debug("Could not convert metadata year '%s' to integer", year_str)

        if not year:
            year_from_episodes = self._extract_year_from_text(episodes)
            year_from_copyright = self._extract_year_from_text(copyright)            
            year = year_from_episodes or year_from_copyright

        return year

    def _update_existing_entry(self, entry: Dict[str, Any], artwork_url: Optional[str], 
                             tracks: List[str], episodes: str, series: str):
        """Update an existing entry with new information."""
        if artwork_url and artwork_url != entry.get('pic', ''):
            self.logger.debug("Updating artwork URL")
            entry['pic'] = artwork_url
        if tracks and tracks != entry.get('tracks', []):
            self.logger.debug("Updating track descriptions")
            entry['tracks'] = tracks
        if episodes and episodes != entry.get('episodes', ''):
            self.logger.debug("Updating episodes")
            entry['episodes'] = episodes
        if series and series != entry.get('series', ''):
            self.logger.debug("Updating series")
            entry['series'] = series

    def _add_hash_to_existing_entry(self, entry: Dict[str, Any], taf_hash: str, 
                                   timestamp: str, artwork_url: Optional[str]):
        """Add hash to existing entry."""
        if 'audio_id' not in entry:
            entry['audio_id'] = []
        if 'hash' not in entry:
            entry['hash'] = []
        
        entry['audio_id'].append(timestamp)
        entry['hash'].append(taf_hash)
        
        if artwork_url and artwork_url != entry.get('pic', ''):
            self.logger.debug("Updating artwork URL")
            entry['pic'] = artwork_url

    def _extract_year_from_text(self, text: str) -> Optional[int]:
        """
        Extract a year (1900-2099) from text.
        Args:
            text (str): The text to extract the year from
        Returns:
            int | None: The extracted year as int, or None if no valid year found
        """
        year_pattern = re.compile(r'(19\d{2}|20\d{2})')
        year_match = year_pattern.search(text)
        if year_match:
            try:
                extracted_year = int(year_match.group(1))
                if 1900 <= extracted_year <= 2099:
                    return extracted_year
            except (ValueError, TypeError):
                pass
        return None

    def _generate_entry_no(self, series: str, episodes: str, year: Optional[int] = None) -> str:
        """
        Generate an entry number based on specific rules:
        1. For series entries with years: assign numbers in chronological order (1, 2, 3, etc.)
        2. For entries without years: assign the next available number after those with years
        Args:
            series (str): Series name
            episodes (str): Episodes name
            year (int | None): Release year from metadata, if available
        Returns:
            str: Generated entry number as string
        """
        if not series:
            max_no = 0
            for entry in self.custom_json:
                try:
                    no_value = int(entry.get('no', '0'))
                    max_no = max(max_no, no_value)
                except (ValueError, TypeError):
                    pass
            return str(max_no + 1)

        # Find existing entries for this series
        series_entries = [entry for entry in self.custom_json if entry.get('series') == series]
        used_numbers = set()
        
        for entry in series_entries:
            try:
                used_numbers.add(int(entry.get('no', '0')))
            except (ValueError, TypeError):
                pass

        highest_no = max(used_numbers) if used_numbers else 0
        return str(highest_no + 1)

    def _generate_model_number(self) -> str:
        """
        Generate a unique model number for a new entry.
        Returns:
            str: Unique model number in the format "tt-42" followed by sequential number with zero padding
        """
        highest_num = -1
        pattern = re.compile(r'tt-42(\d+)')
        
        for entry in self.custom_json:
            model = entry.get('model', '')
            match = pattern.match(model)
            if match:
                try:
                    num = int(match.group(1))
                    highest_num = max(highest_num, num)
                except (IndexError, ValueError):
                    pass

        next_num = highest_num + 1
        return f"tt-42{next_num:010d}"

    def _determine_category_v1(self, metadata: Dict[str, Any]) -> str:
        """
        Determine the category in v1 format.
        Args:
            metadata (dict): Dictionary containing file metadata
        Returns:
            str: Category string in v1 format
        """
        if 'genre' in metadata:
            genre_value = metadata['genre'].lower().strip()
            if any(keyword in genre_value for keyword in ['musik', 'song', 'music', 'lied']):
                return "music"
            elif any(keyword in genre_value for keyword in ['hörspiel', 'audio play', 'hörbuch', 'audiobook']):
                return "audio-play"
            elif any(keyword in genre_value for keyword in ['märchen', 'fairy', 'tales']):
                return "fairy-tale"
            elif any(keyword in genre_value for keyword in ['wissen', 'knowledge', 'learn']):
                return "knowledge"
            elif any(keyword in genre_value for keyword in ['schlaf', 'sleep', 'meditation']):
                return "sleep"
        return "audio-play"

    def _extract_metadata_from_files(self, input_files: List[str]) -> Dict[str, Any]:
        """
        Extract metadata from audio files to use in the custom JSON entry.
        Args:
            input_files (list[str]): List of paths to audio files
        Returns:
            dict: Dictionary containing metadata extracted from files
        """
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

    def _convert_v2_to_v1(self, v2_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert data from v2 format to v1 format.
        Args:
            v2_data (list[dict]): Data in v2 format
        Returns:
            list[dict]: Converted data in v1 format
        """
        v1_data = []
        entry_no = 0
        
        for v2_entry in v2_data:
            if 'data' not in v2_entry:
                continue
            
            for v2_data_item in v2_entry['data']:
                series = v2_data_item.get('series', '')
                episodes = v2_data_item.get('episode', '')
                model = v2_data_item.get('article', '')
                title = f"{series} - {episodes}" if series and episodes else episodes
                
                v1_entry = {
                    "no": str(entry_no),
                    "model": model,
                    "audio_id": [],
                    "hash": [],
                    "title": title,
                    "series": series,
                    "episodes": episodes,
                    "tracks": v2_data_item.get('track-desc', []),
                    "release": str(v2_data_item.get('release', int(time.time()))),
                    "language": v2_data_item.get('language', 'de-de'),
                    "category": self._convert_category_v2_to_v1(v2_data_item.get('category', '')),
                    "pic": v2_data_item.get('image', '')
                }
                
                if 'ids' in v2_data_item:
                    for id_entry in v2_data_item['ids']:
                        if 'audio-id' in id_entry:
                            v1_entry['audio_id'].append(str(id_entry['audio-id']))
                        if 'hash' in id_entry:
                            v1_entry['hash'].append(id_entry['hash'].upper())
                
                v1_data.append(v1_entry)
                entry_no += 1
        
        return v1_data

    def _convert_category_v2_to_v1(self, v2_category: str) -> str:
        """
        Convert category from v2 format to v1 format.
        Args:
            v2_category (str): Category in v2 format
        Returns:
            str: Category in v1 format
        """
        v2_to_v1_mapping = {
            "music": "music",
            "Hörspiele & Hörbücher": "audio-play",
            "Schlaflieder & Entspannung": "sleep",
            "Wissen & Hörmagazine": "knowledge",
            "Märchen": "fairy-tale"
        }
        return v2_to_v1_mapping.get(v2_category, "audio-play")