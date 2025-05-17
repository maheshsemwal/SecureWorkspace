#!/usr/bin/env python3

import os
import sys
import json
import shutil
import hashlib
import logging
import tempfile
import time
import subprocess
from pathlib import Path
from typing import Dict, Set
import click

class SecureWorkspace:
    STATE_FILE = '/tmp/.secure_workspace_state'
    EXCLUDED_PATHS = ['/proc', '/sys', '/dev', '/run', '/tmp', '/var/log']
    EXCLUDED_PATTERNS = [
        # Version control
        '.git', '.svn', '.hg',
        
        # Python
        '__pycache__', '.pyc', '.pyo', '.pyd', '.pytest_cache', '.coverage', '.eggs',
        
        # Node.js
        'node_modules', 'npm-debug.log', 'yarn-debug.log', 'yarn-error.log',
        
        # IDE and editor files
        '.idea', '.vscode', '.vs', '*.swp', '*.swo', '.DS_Store', 'Thumbs.db',
        
        # Build and dist
        'build', 'dist', '*.egg-info',
        
        # Our own files
        '.secure_workspace_state',
        
        # System files
        'SingletonSocket', '.Xauthority', '.X11-unix', '.cache',
        '.local/share/Trash', '.mozilla/firefox/*.default/Cache',
        
        # Package manager caches
        '.npm', '.yarn', '.pip', '.gradle', '.m2',
        
        # Browser caches
        'Cache', 'CacheStorage', '.config/google-chrome/Default/Cache',
        '.config/chromium/Default/Cache', '.mozilla/firefox/*.default/cache2'
    ]
    
    def __init__(self):
        self.backup_path = None
        self.original_state = {}
        self.new_files = set()
        
        # Set up logging with info level only
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _normalize_path(self, path: str) -> str:
        try:
            return str(Path(path).resolve())
        except (OSError, RuntimeError):
            return path

    def _should_track_file(self, path: str) -> bool:
        path = self._normalize_path(path)
        
        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return False
            
        # Skip excluded patterns using more sophisticated matching
        path_lower = path.lower()  # Case-insensitive matching
        rel_path = os.path.relpath(path, os.path.expanduser('~'))
        
        for pattern in self.EXCLUDED_PATTERNS:
            # Handle glob patterns
            if '*' in pattern:
                if any(part.startswith('.') and part.endswith('Cache') for part in path_lower.split(os.sep)):
                    return False
                continue
                
            # Direct matching against path components
            if pattern in path_lower.split(os.sep):
                return False
                
            # Check if pattern appears in the path
            if pattern.startswith('.') and pattern.lower() in path_lower:
                return False
        
        # Only track files in home directory
        if not path.startswith(os.path.expanduser('~')):
            return False
            
        return os.path.isfile(path)

    def _calculate_file_hash(self, filepath: str) -> str:
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ''

    def _backup_file(self, filepath: str):
        if not self.backup_path:
            self.backup_path = tempfile.mkdtemp()
            
        rel_path = os.path.relpath(filepath, os.path.expanduser('~'))
        backup_file = os.path.join(self.backup_path, rel_path)
        
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        try:
            shutil.copy2(filepath, backup_file)
        except (OSError, IOError):
            pass

    def start(self):
        self.logger.info("\nInitializing secure workspace...")
        
        # Get initial state of files
        cmd = ['find', os.path.expanduser('~'), '-type', 'f']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            files = result.stdout.splitlines()
        except subprocess.SubprocessError:
            self.logger.error("Failed to get initial file list")
            return False

        # Track initial state
        tracked_files = 0
        for filepath in files:
            if self._should_track_file(filepath):
                norm_path = self._normalize_path(filepath)
                self.original_state[norm_path] = self._calculate_file_hash(norm_path)
                self._backup_file(norm_path)
                tracked_files += 1

        # Save state
        with open(self.STATE_FILE, 'w') as f:
            json.dump({
                'backup_path': self.backup_path,
                'original_state': self.original_state
            }, f)

        self.logger.info(f"Secure workspace started - tracking {tracked_files} files")
        self.logger.info("Any new files or modifications will be tracked and reverted when stopping")
        return True

    def _ask_for_preservation(self, files: list, change_type: str) -> set:
        """Ask user which files to preserve from a list of changed files."""
        if not files:
            return set()
            
        preserved = set()
        
        self.logger.info(f"\nThe following {change_type} files were detected:")
        for idx, file in enumerate(files, 1):
            self.logger.info(f"{idx}. {file}")
            
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
                            self.logger.info(f"Invalid number: {num}")
                except ValueError:
                    self.logger.info("Invalid input. Please enter numbers, 'all', 'none', or 'q'")
                    
        return preserved

    def stop(self):
        self.logger.info("\nStopping secure workspace...")
        
        # Load saved state
        try:
            with open(self.STATE_FILE, 'r') as f:
                saved_state = json.load(f)
                self.backup_path = saved_state['backup_path']
                self.original_state = saved_state['original_state']
        except (OSError, json.JSONDecodeError):
            self.logger.error("Failed to load secure workspace state")
            return False

        # Get current files
        cmd = ['find', os.path.expanduser('~'), '-type', 'f']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            current_files = set(result.stdout.splitlines())
        except subprocess.SubprocessError:
            self.logger.error("Failed to get current file list")
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
        for original_path in self.original_state:
            if not os.path.exists(original_path):
                rel_path = os.path.relpath(original_path, os.path.expanduser('~'))
                deleted_files_list.append(rel_path)

        # Check for new and modified files
        for filepath in current_files:
            if not self._should_track_file(filepath):
                continue

            norm_path = self._normalize_path(filepath)
            
            # New file
            if norm_path not in self.original_state:
                rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
                new_files_list.append(rel_path)
                continue

            # Modified file
            current_hash = self._calculate_file_hash(norm_path)
            if current_hash != self.original_state[norm_path]:
                rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
                modified_files_list.append(rel_path)

        # Ask user which files to preserve for each category
        if new_files_list or modified_files_list or deleted_files_list:
            self.logger.info("\nSelect files to preserve:")
            
            if new_files_list:
                preserved_new = self._ask_for_preservation(new_files_list, "new")
                preserved_files.update(preserved_new)
                
            if modified_files_list:
                preserved_modified = self._ask_for_preservation(modified_files_list, "modified")
                preserved_files.update(preserved_modified)
                
            if deleted_files_list:
                preserved_deleted = self._ask_for_preservation(deleted_files_list, "deleted")
                preserved_files.update(preserved_deleted)

        # Now handle the changes based on user choices
        # Handle deleted files
        for original_path in self.original_state:
            if not os.path.exists(original_path):
                rel_path = os.path.relpath(original_path, os.path.expanduser('~'))
                if rel_path not in preserved_files:
                    backup_file = os.path.join(self.backup_path, rel_path)
                    try:
                        os.makedirs(os.path.dirname(original_path), exist_ok=True)
                        shutil.copy2(backup_file, original_path)
                        deleted_files_restored += 1
                    except (OSError, IOError):
                        pass

        # Handle new and modified files
        for filepath in current_files:
            if not self._should_track_file(filepath):
                continue

            norm_path = self._normalize_path(filepath)
            rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
            
            # New file
            if norm_path not in self.original_state:
                if rel_path not in preserved_files:
                    try:
                        os.remove(norm_path)
                        new_files_removed += 1
                    except OSError:
                        pass
                continue

            # Modified file
            current_hash = self._calculate_file_hash(norm_path)
            if current_hash != self.original_state[norm_path]:
                if rel_path not in preserved_files:
                    backup_file = os.path.join(self.backup_path, rel_path)
                    try:
                        shutil.copy2(backup_file, norm_path)
                        modified_files_reverted += 1
                    except (OSError, IOError):
                        pass

        # Clean up
        try:
            os.remove(self.STATE_FILE)
            shutil.rmtree(self.backup_path)
        except OSError:
            pass

        # Print detailed summary
        self.logger.info("\nSummary of changes:")
        
        if preserved_files:
            self.logger.info("\nPreserved files:")
            for file in preserved_files:
                self.logger.info(f"  + {file}")
        
        if new_files_removed > 0:
            self.logger.info(f"\nRemoved {new_files_removed} new files")
            
        if modified_files_reverted > 0:
            self.logger.info(f"\nReverted {modified_files_reverted} modified files")
            
        if deleted_files_restored > 0:
            self.logger.info(f"\nRestored {deleted_files_restored} deleted files")
            
        if not preserved_files and new_files_removed == 0 and modified_files_reverted == 0 and deleted_files_restored == 0:
            self.logger.info("No changes detected - workspace is clean")
            
        self.logger.info("\nSecure workspace stopped successfully")
        return True

@click.command()
@click.argument('action', type=click.Choice(['start', 'stop']))
def main(action):
    workspace = SecureWorkspace()
    
    if action == 'start':
        if not workspace.start():
            sys.exit(1)
    else:
        if not workspace.stop():
            sys.exit(1)

if __name__ == '__main__':
    main() 
