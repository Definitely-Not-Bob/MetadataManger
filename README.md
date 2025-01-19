# MetadataManger

## Project Overview

The **Metadata Manager** is a Python-based tool designed to simplify the management of metadata for MP3 files. It includes two main components:

1. **MetadataManager**: A backend library for reading, editing, and validating ID3 metadata, including cover art management.
2. **MetadataGUI**: A user-friendly graphical interface built with `tkinter`


This project aim to give precise metadata control and general users who prefer a simple graphical interface.

---

## Features

### MetadataManager
- **Read and Modify Metadata**: Works with all ID3 fields, including advanced raw fields.
- **Validation Rules**: Ensures metadata complies with configurable rules (e.g., field length, allowed characters).
- **Cover Art Management**: Allows adding, removing, or replacing album art.
- **Batch Corrections**: Automatically fixes metadata based on user-defined rules.

### MetadataGUI
- **File Selection**: Load MP3 files via a graphical file picker.
- **Field Editing**: Modify key fields (title, artist, album, genre) through easy-to-use text boxes.
- **Advanced Options**: Apply corrections and manage album art using checkboxes.
- **Metadata Display**: View detailed metadata in a scrollable text area.

---

## Installation

### Prerequisites
- Python 3.7 or later
- `mutagen` library for MP3 metadata handling

Install dependencies using `pip`:
```bash
pip install mutagen
```

### Command-Line Usage
For direct interaction with `MetadataManager`, you can write Python scripts or use an interactive shell:

```python
from metadata_manager.manager import MetadataManager

# Initialize the manager
manager = MetadataManager("config/config.json")

# Load an MP3 file
manager.load_file("example.mp3")

# Print metadata
manager.print_all_metadata()

# Modify metadata
manager.set_field("title", "New Title")
manager.save_file()
```

---

## Configuration

The behavior of the MetadataManager is controlled by a `config.json` file, which should be placed in the `config/` directory. Below is an example configuration:

```json
{
  "exclude_values": {
    "global": ["*unknown*", "*untitled*"],
    "title": ["N/A"]
  },
  "dependent_removals": {
    "artist": ["musicbrainz_artistid", "artistsort"]
  },
  "format_rules": {
    "title": {
      "strip": true,
      "uppercase": false,
      "lowercase": true,
      "max_length": 100
    }
  },
  "fields_spec": {
    "title": {
      "type": "str",
      "max_length": 200
    },
    "tracknumber": {
      "type": "int",
      "min": 1,
      "max": 99
    }
  },
  "char_filter": {
    "allowed_regex": "^[a-zA-Z0-9,.'!\-\s]+$",
    "replace_not_allowed": "_"
  }
}
```

### Key Sections
- **`exclude_values`**: Specifies values to exclude globally or for specific fields (wildcard patterns supported).
- **`dependent_removals`**: Lists fields to remove if a primary field is deleted.
- **`format_rules`**: Rules for formatting metadata fields (e.g., trimming whitespace, enforcing case).
- **`fields_spec`**: Validation rules for field types, lengths, and ranges.
- **`char_filter`**: Defines allowed characters and replacements for invalid ones.

---

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

