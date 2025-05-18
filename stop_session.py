#!/usr/bin/env python3

import os
import sys
import json
import shutil
import subprocess
import click
import argparse
from secure_workspace import SecureWorkspace

def _ask_for_preservation(workspace, files: list, change_type: str) -> set:
    """Ask user which files to preserve from a list of changed files."""
    if not files:
        return set()
        
    preserved = set()
    
    workspace.logger.info(f"\nThe following {change_type} files were detected:")
    for idx, file in enumerate(files, 1):
        workspace.logger.info(f"{idx}. {file}")
        
    while True:
        choice = click.prompt(
            "\nEnter file numbers to preserve (comma-separated) or 'all'/'none' or 'q' to finish",
            type=str,
            default='none'
        ).lower().strip()
        
        if choice == 'q':
            break
        elif choice == 'all':
            preserved.update(files)
            break
        elif choice == 'none':
            break
        else:
            try:
                # Parse comma-separated numbers
                selections = [int(x.strip()) for x in choice.split(',')]
                for num in selections:
                    if 1 <= num <= len(files):
                        preserved.add(files[num-1])
                    else:
                        workspace.logger.info(f"Invalid number: {num}")
            except ValueError:
                workspace.logger.info("Invalid input. Please enter numbers, 'all', 'none', or 'q'")
                
    return preserved

def stop_workspace(preserve_files=None):
    """Stop the secure workspace and handle file preservation."""
    workspace = SecureWorkspace()
    workspace.logger.info("\nStopping secure workspace...")
    
    # Load saved state
    try:
        with open(workspace.STATE_FILE, 'r') as f:
            saved_state = json.load(f)
            workspace.backup_path = saved_state['backup_path']
            workspace.original_state = saved_state['original_state']
    except (OSError, json.JSONDecodeError):
        workspace.logger.error("Failed to load secure workspace state")
        return False

    # Get current files
    cmd = ['find', os.path.expanduser('~'), '-type', 'f']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        current_files = set(result.stdout.splitlines())
    except subprocess.SubprocessError:
        workspace.logger.error("Failed to get current file list")
        return False

    new_files_removed = 0
    modified_files_reverted = 0
    deleted_files_restored = 0
    new_files_list = []
    modified_files_list = []
    deleted_files_list = []
    
    # Convert preserve_files to absolute paths if they aren't already
    preserved_files = set()
    if preserve_files:
        for file_path in preserve_files:
            if not os.path.isabs(file_path):
                abs_path = os.path.join(os.path.expanduser('~'), file_path)
            else:
                abs_path = file_path
            preserved_files.add(abs_path)

    # First collect all changes
    # Check for deleted files
    for original_path in workspace.original_state:
        if not os.path.exists(original_path):
            deleted_files_list.append(original_path)

    # Check for new and modified files
    for filepath in current_files:
        if not workspace._should_track_file(filepath):
            continue

        norm_path = workspace._normalize_path(filepath)
        
        # New file
        if norm_path not in workspace.original_state:
            new_files_list.append(norm_path)
            continue

        # Modified file
        current_hash = workspace._calculate_file_hash(norm_path)
        if current_hash != workspace.original_state[norm_path]:
            modified_files_list.append(norm_path)

    # Now handle the changes based on preserved files
    # Handle deleted files
    for original_path in workspace.original_state:
        if not os.path.exists(original_path):
            if original_path not in preserved_files:
                backup_file = os.path.join(workspace.backup_path, os.path.relpath(original_path, os.path.expanduser('~')))
                try:
                    os.makedirs(os.path.dirname(original_path), exist_ok=True)
                    shutil.copy2(backup_file, original_path)
                    deleted_files_restored += 1
                except (OSError, IOError) as e:
                    workspace.logger.error(f"Failed to restore deleted file {original_path}: {str(e)}")

    # Handle new and modified files
    for filepath in current_files:
        if not workspace._should_track_file(filepath):
            continue

        norm_path = workspace._normalize_path(filepath)
        
        # New file
        if norm_path not in workspace.original_state:
            if norm_path not in preserved_files:
                try:
                    os.remove(norm_path)
                    new_files_removed += 1
                except OSError as e:
                    workspace.logger.error(f"Failed to remove new file {norm_path}: {str(e)}")
            continue

        # Modified file
        current_hash = workspace._calculate_file_hash(norm_path)
        if current_hash != workspace.original_state[norm_path]:
            if norm_path not in preserved_files:
                backup_file = os.path.join(workspace.backup_path, os.path.relpath(norm_path, os.path.expanduser('~')))
                try:
                    shutil.copy2(backup_file, norm_path)
                    modified_files_reverted += 1
                except (OSError, IOError) as e:
                    workspace.logger.error(f"Failed to revert modified file {norm_path}: {str(e)}")

    # Clean up
    try:
        os.remove(workspace.STATE_FILE)
        shutil.rmtree(workspace.backup_path)
    except OSError as e:
        workspace.logger.error(f"Failed to clean up: {str(e)}")

    # Print detailed summary
    workspace.logger.info("\nSummary of changes:")
    
    if preserved_files:
        workspace.logger.info("\nPreserved files:")
        for file in preserved_files:
            workspace.logger.info(f"  + {file}")
    
    if new_files_removed > 0:
        workspace.logger.info(f"\nRemoved {new_files_removed} new files")
        
    if modified_files_reverted > 0:
        workspace.logger.info(f"\nReverted {modified_files_reverted} modified files")
        
    if deleted_files_restored > 0:
        workspace.logger.info(f"\nRestored {deleted_files_restored} deleted files")
        
    if not preserved_files and new_files_removed == 0 and modified_files_reverted == 0 and deleted_files_restored == 0:
        workspace.logger.info("No changes detected - workspace is clean")
        
    workspace.logger.info("\nSecure workspace stopped successfully")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stop secure workspace session')
    parser.add_argument('--preserve-files', type=str, help='JSON array of files to preserve')
    args = parser.parse_args()

    preserve_files = json.loads(args.preserve_files) if args.preserve_files else None
    stop_workspace(preserve_files) 