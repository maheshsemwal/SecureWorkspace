#!/usr/bin/env python3

import os
import sys
import json
import shutil
import subprocess
import click
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

def stop_workspace():
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
    preserved_files = set()

    # First collect all changes
    # Check for deleted files
    for original_path in workspace.original_state:
        if not os.path.exists(original_path):
            rel_path = os.path.relpath(original_path, os.path.expanduser('~'))
            deleted_files_list.append(rel_path)

    # Check for new and modified files
    for filepath in current_files:
        if not workspace._should_track_file(filepath):
            continue

        norm_path = workspace._normalize_path(filepath)
        
        # New file
        if norm_path not in workspace.original_state:
            rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
            new_files_list.append(rel_path)
            continue

        # Modified file
        current_hash = workspace._calculate_file_hash(norm_path)
        if current_hash != workspace.original_state[norm_path]:
            rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
            modified_files_list.append(rel_path)

    # Ask user which files to preserve for each category
    if new_files_list or modified_files_list or deleted_files_list:
        workspace.logger.info("\nSelect files to preserve:")
        
        if new_files_list:
            preserved_new = _ask_for_preservation(workspace, new_files_list, "new")
            preserved_files.update(preserved_new)
            
        if modified_files_list:
            preserved_modified = _ask_for_preservation(workspace, modified_files_list, "modified")
            preserved_files.update(preserved_modified)
            
        if deleted_files_list:
            preserved_deleted = _ask_for_preservation(workspace, deleted_files_list, "deleted")
            preserved_files.update(preserved_deleted)

    # Now handle the changes based on user choices
    # Handle deleted files
    for original_path in workspace.original_state:
        if not os.path.exists(original_path):
            rel_path = os.path.relpath(original_path, os.path.expanduser('~'))
            if rel_path not in preserved_files:
                backup_file = os.path.join(workspace.backup_path, rel_path)
                try:
                    os.makedirs(os.path.dirname(original_path), exist_ok=True)
                    shutil.copy2(backup_file, original_path)
                    deleted_files_restored += 1
                except (OSError, IOError):
                    pass

    # Handle new and modified files
    for filepath in current_files:
        if not workspace._should_track_file(filepath):
            continue

        norm_path = workspace._normalize_path(filepath)
        rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
        
        # New file
        if norm_path not in workspace.original_state:
            if rel_path not in preserved_files:
                try:
                    os.remove(norm_path)
                    new_files_removed += 1
                except OSError:
                    pass
            continue

        # Modified file
        current_hash = workspace._calculate_file_hash(norm_path)
        if current_hash != workspace.original_state[norm_path]:
            if rel_path not in preserved_files:
                backup_file = os.path.join(workspace.backup_path, rel_path)
                try:
                    shutil.copy2(backup_file, norm_path)
                    modified_files_reverted += 1
                except (OSError, IOError):
                    pass

    # Clean up
    try:
        os.remove(workspace.STATE_FILE)
        shutil.rmtree(workspace.backup_path)
    except OSError:
        pass

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

@click.command()
def main():
    if not stop_workspace():
        sys.exit(1)

if __name__ == '__main__':
    main() 