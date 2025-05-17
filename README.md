# Secure Workspace

A Python-based tool for creating isolated, reversible workspaces that track and manage file changes in your home directory. This tool allows you to experiment freely and revert changes selectively when you're done.

## Features

- **File Tracking**: Monitors all changes to files in your home directory
- **Selective Preservation**: Choose which changes to keep when exiting
- **Smart Exclusions**: Automatically ignores system files, caches, and temporary files
- **Backup System**: Creates secure backups of original files
- **Interactive Interface**: User-friendly prompts for managing changes

## Technical Implementation

### Architecture

The project is split into three main components:

1. **Core Class (`secure_workspace.py`)**
   - Handles core functionality and utilities
   - Manages file tracking and backup operations
   - Implements file filtering and pattern matching

2. **Start Session (`start_session.py`)**
   - Initializes the secure workspace
   - Creates initial file state snapshot
   - Sets up backup directory

3. **Stop Session (`stop_session.py`)**
   - Detects file changes (new, modified, deleted)
   - Manages interactive file preservation
   - Handles cleanup and restoration

### Technologies Used

- **Python 3.x**
  - `pathlib`: Path manipulation and resolution
  - `hashlib`: File content verification
  - `shutil`: File operations
  - `tempfile`: Secure temporary storage
  - `json`: State persistence
  - `click`: Command-line interface
  - `logging`: User feedback and debugging

### File Exclusion Patterns

The system automatically excludes:
```python
# Version Control
- .git, .svn, .hg

# Python
- __pycache__, .pyc, .pyo, .pyd
- .pytest_cache, .coverage, .eggs

# Node.js
- node_modules
- npm-debug.log, yarn-debug.log

# IDE and Editor
- .idea, .vscode, .vs
- *.swp, *.swo

# System
- .DS_Store, Thumbs.db
- Various cache directories
- Browser caches
- Package manager caches
```

## Usage

### Starting a Secure Workspace

```bash
python3 start_session.py
```
This will:
1. Create a snapshot of your current files
2. Set up a backup directory
3. Begin tracking changes

### During the Session

You can:
- Create new files
- Modify existing files
- Delete files
All changes are tracked and can be reverted.

### Stopping the Workspace

```bash
python3 stop_session.py
```
This will:
1. Show all changes made during the session
2. Let you choose which changes to keep
3. Revert unwanted changes
4. Clean up temporary files

### Preservation Options

When stopping, for each type of change (new/modified/deleted), you can:
- Enter numbers (e.g., "1,2,3") to keep specific files
- Type "all" to keep everything
- Type "none" to revert everything
- Type "q" to finish selection

## Security Features

- Path normalization to prevent traversal attacks
- Secure temporary file handling
- SHA-256 file hashing for change detection
- Proper permission handling during backup/restore
- Excluded system and sensitive directories

## System Requirements

- Python 3.x
- Linux/Unix-based system
- Sufficient disk space for backups
- Read/write permissions in home directory

## Installation

1. Clone the repository
2. Make scripts executable:
   ```bash
   chmod +x start_session.py stop_session.py
   ```
3. Ensure Python 3.x is installed

## Limitations

- Only tracks files in home directory
- Requires sufficient disk space for backups
- Some system files are excluded for safety
- Large binary files may slow down the process

## Future Enhancements

- Configuration file for custom exclusions
- Compression for backups
- Multiple workspace support
- Remote backup integration
- GUI interface option

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
