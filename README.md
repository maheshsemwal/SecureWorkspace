# Secure Ephemeral Workspace

A security-focused tool for creating temporary, private workspaces on public computers. This tool allows users to work in a secure environment where all changes are automatically reverted when the secure mode is disabled.

## Features

- Create isolated secure workspaces
- Track all file modifications and new file creations
- Automatically revert changes when exiting secure mode
- Clean up temporary files and restore original state

## Requirements

- Python 3.8+
- Linux-based system

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. Start the secure workspace:
```bash
python secure_workspace.py start
```

2. Work in the secure environment

3. Exit secure mode to revert all changes:
```bash
python secure_workspace.py stop
```

## Security Considerations

- All temporary files are securely deleted
- Changes are tracked using checksums
- Original files are preserved 