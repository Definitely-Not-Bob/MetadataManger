import os
import json
import fnmatch
import re
from typing import Any, Dict, List, Optional, Union

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError, APIC
from mutagen.mp3 import MP3

class MetadataManager:
    """
    Extended management of ID3 (MP3) metadata.
    - Loads exclusion, replacement, dependency, formatting, and validation rules
      (type, range, length) from an external configuration file.
    - Works with ALL ID3 fields (including musicbrainz_*, isrc, etc.).
    - Allows adding/removing/reading cover art (APIC).
    """

    def __init__(self, config_file: str):
        """
        Initializes the metadata manager, loading settings from the configuration file.
        """
        self.config: Dict[str, Any] = {}
        self.audio_easy: Optional[EasyID3] = None  # For simplified text fields
        self.audio_id3: Optional[ID3] = None       # For handling APIC and raw frames
        self.file_path: Optional[str] = None

        self._load_config(config_file)

    def _load_config(self, config_file: str) -> None:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def load_file(self, file_path: str) -> None:
        """
        Opens the .mp3 file and reads its metadata:
         - self.audio_easy for simplified ID3 text fields.
         - self.audio_id3 for handling APIC (cover art) or unmapped frames.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            self.audio_id3 = ID3(file_path)
        except ID3NoHeaderError:
            self.audio_id3 = ID3()

        try:
            self.audio_easy = EasyID3(file_path)
        except ID3NoHeaderError:
            self.audio_easy = EasyID3()
            self.audio_easy.save(file_path)

        self.file_path = file_path
        self.audio_info = MP3(file_path).info

    def save_file(self) -> None:
        """
        Saves all modifications (text and images) to the MP3 file.
        """
        if not self.file_path:
            raise ValueError("No loaded file to save.")

        if self.audio_easy:
            self.audio_easy.save(self.file_path)
        if self.audio_id3:
            self.audio_id3.save(self.file_path)

    def print_all_metadata(self) -> None:
        """
        Prints all ID3 metadata fields (including non-standard ones) to the console.
        """
        if not self.audio_easy or not self.audio_id3:
            raise ValueError("No file loaded.")

        print("=== ALL FIELDS (EasyID3 + raw) ===")

        print("\n--- EasyID3 Fields ---")
        for field_name, values in self.audio_easy.items():
            print(f"{field_name}: {values}")

        print("\n--- ID3 Additional Frames ---")
        easy_keys_lower = [k.lower() for k in self.audio_easy.keys()]
        for frame_id in self.audio_id3:
            if frame_id.lower() not in easy_keys_lower:
                frame_obj = self.audio_id3[frame_id]
                print(f"{frame_id}: {frame_obj}")

        if hasattr(self, 'audio_info') and self.audio_info:
            print("\n--- Info (non-ID3) ---")
            print(f"Bitrate: {self.audio_info.bitrate} bps")
            print(f"Sample Rate: {self.audio_info.sample_rate} Hz")
            print(f"Channels: {self.audio_info.channels}")

    def get_field(self, field_name: str) -> Optional[str]:
        """
        Returns the first value of an ID3 field in EasyID3 format (if available).
        """
        if not self.audio_easy:
            raise ValueError("No file loaded.")
        return self.audio_easy.get(field_name, [None])[0]

    def set_field(self, field_name: str, value: str) -> None:
        """
        Sets a field (single value) in EasyID3 metadata.
        """
        if not self.audio_easy:
            raise ValueError("No file loaded.")
        self.audio_easy[field_name] = [value]

    def get_album_art(self) -> Optional[bytes]:
        """
        Returns the album art bytes if present, otherwise None.
        """
        if not self.audio_id3:
            raise ValueError("No file loaded.")

        apic_keys = [k for k in self.audio_id3.keys() if k.startswith("APIC")]
        if not apic_keys:
            return None

        apic = self.audio_id3[apic_keys[0]]
        if isinstance(apic, APIC):
            return apic.data
        return None

    def set_album_art(self, image_data: bytes, mime_type: str = "image/jpeg") -> None:
        """
        Sets the album art, replacing any existing images.
        """
        if not self.audio_id3 or not self.file_path:
            raise ValueError("No file loaded.")

        for key in [k for k in self.audio_id3.keys() if k.startswith("APIC")]:
            del self.audio_id3[key]

        self.audio_id3.add(APIC(
            encoding=3,        # UTF-8
            mime=mime_type,    # e.g., image/jpeg or image/png
            type=3,            # Cover (front)
            desc="Cover",
            data=image_data
        ))

    def remove_album_art(self) -> None:
        """
        Removes any existing album art (APIC frames).
        """
        if not self.audio_id3:
            raise ValueError("No file loaded.")

        for key in [k for k in self.audio_id3.keys() if k.startswith("APIC")]:
            del self.audio_id3[key]

    def _apply_format_rules(self, value: Any, rules: Dict[str, Any]) -> str:
        """
        Applies formatting rules (e.g., strip, uppercase, lowercase, max_length).
        If value is not a string, attempts to convert it to a string.
        """
        if not isinstance(value, str):
            value = str(value)

        if rules.get("strip", False):
            value = value.strip()

        if rules.get("uppercase", False):
            value = value.upper()

        if rules.get("lowercase", False):
            value = value.lower()

        if "max_length" in rules:
            max_len = rules["max_length"]
            value = value[:max_len]

        return value

    def check_and_correct_all(self) -> None:
        """
        Validates and corrects all EasyID3 and additional ID3 fields.
        Rules:
          - Removes or replaces excluded values (including wildcard patterns).
          - Applies formatting and validation rules (type, range, etc.).
          - Removes dependent fields if a primary field is removed.
          - Checks allowed characters (if defined in config).
        """
        if not self.audio_easy or not self.audio_id3:
            raise ValueError("No file loaded.")

        exclude_cfg = self.config.get("exclude_values", {})
        dependent_removals = self.config.get("dependent_removals", {})
        format_rules = self.config.get("format_rules", {})
        fields_spec = self.config.get("fields_spec", {})
        char_filter = self.config.get("char_filter", {})

        exclude_action = exclude_cfg.get("action", "remove")
        exclude_replace_val = exclude_cfg.get("replace_with", "[EXCLUDED]")

        for field in list(self.audio_easy.keys()):
            original_values = self.audio_easy[field]
            final_values: List[str] = []

            for value in original_values:
                value = self._apply_format_rules(value, format_rules.get(field, {}))
                value = self._filter_chars(value, char_filter)

                if self._match_exclude(value, exclude_cfg, field):
                    if exclude_action == "remove":
                        continue
                    elif exclude_action == "replace":
                        value = exclude_replace_val

                validated_value = self._validate_value(field, value, fields_spec.get(field, {}))
                if validated_value is not None:
                    final_values.append(validated_value)

            if not final_values:
                del self.audio_easy[field]
                self._remove_dependent_fields(field, dependent_removals)
            else:
                self.audio_easy[field] = final_values

        text_frames = []
        for frame_id in self.audio_id3.keys():
            if frame_id.lower() in [k.lower() for k in self.audio_easy.keys()]:
                continue

            frame = self.audio_id3[frame_id]
            if hasattr(frame, "text"):
                text_frames.append(frame_id)

        for frame_id in text_frames:
            frame = self.audio_id3[frame_id]
            if not frame.text or not isinstance(frame.text, list):
                continue

            original_texts = frame.text
            new_texts: List[str] = []

            for value in original_texts:
                value = self._apply_format_rules(value, format_rules.get(frame_id, {}))
                value = self._filter_chars(value, char_filter)

                if self._match_exclude(value, exclude_cfg, frame_id):
                    if exclude_action == "remove":
                        continue
                    elif exclude_action == "replace":
                        value = exclude_replace_val

                validated_value = self._validate_value(frame_id, value, fields_spec.get(frame_id, {}))
                if validated_value is not None:
                    new_texts.append(validated_value)

            if not new_texts:
                del self.audio_id3[frame_id]
                self._remove_dependent_fields(frame_id, dependent_removals)
            else:
                frame.text = new_texts
                self.audio_id3[frame_id] = frame

    def _match_exclude(self, value: str, exclude_cfg: Dict[str, Any], field_name: str) -> bool:
        """
        Checks if a value matches global or field-specific exclusion patterns.
        Uses fnmatch for wildcard support.
        """
        global_excludes = exclude_cfg.get("global", [])
        field_excludes = exclude_cfg.get(field_name, [])

        value_lower = value.lower()

        for pattern in global_excludes:
            if fnmatch.fnmatch(value_lower, pattern.lower()):
                return True

        for pattern in field_excludes:
            if fnmatch.fnmatch(value_lower, pattern.lower()):
                return True

        return False

    def _filter_chars(self, value: str, char_filter: Dict[str, Any]) -> str:
        """
        Filters or replaces disallowed characters based on the allowed_regex in config.
        """
        allowed_regex = char_filter.get("allowed_regex")
        replace_char = char_filter.get("replace_not_allowed", "")

        if not allowed_regex:
            return value

        pattern_for_not_allowed = re.sub("^\^|\$$", "", allowed_regex)
        pattern_for_not_allowed = f"[^{pattern_for_not_allowed}]"

        return re.sub(pattern_for_not_allowed, replace_char, value)

    def _validate_value(self, field_name: str, value: str, spec: Dict[str, Any]) -> Optional[str]:
        """
        Validates the value according to type, range, and max_length rules.
        Returns the value (potentially truncated) or None if invalid.
        """
        if not spec:
            return value

        expected_type = spec.get("type", "str")
        max_length = spec.get("max_length")
        min_val = spec.get("min")
        max_val = spec.get("max")

        if expected_type == "str":
            if max_length and len(value) > max_length:
                value = value[:max_length]
            return value

        if expected_type == "int":
            try:
                num = int(value)
            except ValueError:
                return None

            if (min_val is not None and num < min_val) or \
               (max_val is not None and num > max_val):
                return None

            return str(num)

        return value

    def _remove_dependent_fields(self, removed_field: str, dep_cfg: Dict[str, List[str]]) -> None:
        """
        Removes dependent fields if a primary field is removed.
        """
        if removed_field not in dep_cfg:
            return

        fields_to_remove = dep_cfg[removed_field]
        for f in fields_to_remove:
            if self.audio_easy and f in self.audio_easy:
                del self.audio_easy[f]

            if self.audio_id3 and f in self.audio_id3:
                del self.audio_id3[f]

if __name__ == "__main__":
    path = os.path.dirname(os.path.abspath(__file__))

    config_path = os.path.join(path, 'config.json')
    mp3_file = os.path.join(path, '505.mp3')

    manager = MetadataManager(config_path)
    manager.load_file(mp3_file)

    print("=== METADATA BEFORE CORRECTION ===")
    manager.print_all_metadata()

    manager.check_and_correct_all()

    print("\n=== METADATA AFTER CORRECTION ===")
    manager.print_all_metadata()

    manager.save_file()

    current_cover = manager.get_album_art()
    if current_cover:
        print(f"\nCover size: {len(current_cover)} bytes")
    else:
        print("\nNo cover art found.")
