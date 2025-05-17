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
    EXCLUDED_PATTERNS = ['.git', '__pycache__', '.secure_workspace_state', 'SingletonSocket', '.Xauthority', '.X11-unix']
    
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
            
        # Skip excluded patterns
        if any(pattern in path for pattern in self.EXCLUDED_PATTERNS):
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
        new_files_list = []
        modified_files_list = []

        # Check for new and modified files
        for filepath in current_files:
            if not self._should_track_file(filepath):
                continue

            norm_path = self._normalize_path(filepath)
            
            # New file
            if norm_path not in self.original_state:
                try:
                    # Get relative path for cleaner output
                    rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
                    new_files_list.append(rel_path)
                    os.remove(norm_path)
                    new_files_removed += 1
                except OSError:
                    pass
                continue

            # Modified file
            current_hash = self._calculate_file_hash(norm_path)
            if current_hash != self.original_state[norm_path]:
                rel_path = os.path.relpath(norm_path, os.path.expanduser('~'))
                backup_file = os.path.join(self.backup_path, rel_path)
                try:
                    shutil.copy2(backup_file, norm_path)
                    modified_files_list.append(rel_path)
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
        if new_files_removed > 0:
            self.logger.info(f"\nRemoved {new_files_removed} new files:")
            for file in new_files_list:
                self.logger.info(f"  - {file}")
        
        if modified_files_reverted > 0:
            self.logger.info(f"\nReverted {modified_files_reverted} modified files:")
            for file in modified_files_list:
                self.logger.info(f"  - {file}")
                
        if new_files_removed == 0 and modified_files_reverted == 0:
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