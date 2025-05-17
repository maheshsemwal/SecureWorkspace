#!/usr/bin/env python3

import os
import sys
import json
import shutil
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Dict, Set

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
        """Normalize a file path to its absolute form."""
        try:
            return str(Path(path).resolve())
        except (OSError, RuntimeError):
            return path

    def _should_track_file(self, path: str) -> bool:
        """Determine if a file should be tracked based on exclusion rules."""
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
        """Calculate SHA-256 hash of a file."""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ''

    def _backup_file(self, filepath: str):
        """Create a backup copy of a file."""
        if not self.backup_path:
            self.backup_path = tempfile.mkdtemp()
            
        rel_path = os.path.relpath(filepath, os.path.expanduser('~'))
        backup_file = os.path.join(self.backup_path, rel_path)
        
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        try:
            shutil.copy2(filepath, backup_file)
        except (OSError, IOError):
            pass 
