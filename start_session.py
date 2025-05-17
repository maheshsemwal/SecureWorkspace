#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import click
from secure_workspace import SecureWorkspace

def start_workspace():
    """Initialize and start a new secure workspace session."""
    workspace = SecureWorkspace()
    workspace.logger.info("\nInitializing secure workspace...")
    
    # Get initial state of files
    cmd = ['find', os.path.expanduser('~'), '-type', 'f']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        files = result.stdout.splitlines()
    except subprocess.SubprocessError:
        workspace.logger.error("Failed to get initial file list")
        return False

    # Track initial state
    tracked_files = 0
    for filepath in files:
        if workspace._should_track_file(filepath):
            norm_path = workspace._normalize_path(filepath)
            workspace.original_state[norm_path] = workspace._calculate_file_hash(norm_path)
            workspace._backup_file(norm_path)
            tracked_files += 1

    # Save state
    with open(workspace.STATE_FILE, 'w') as f:
        json.dump({
            'backup_path': workspace.backup_path,
            'original_state': workspace.original_state
        }, f)

    workspace.logger.info(f"Secure workspace started - tracking {tracked_files} files")
    workspace.logger.info("Any new files or modifications will be tracked and reverted when stopping")
    return True

@click.command()
def main():
    if not start_workspace():
        sys.exit(1)

if __name__ == '__main__':
    main() 