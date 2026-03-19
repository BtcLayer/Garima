"""
JSONL Queue Storage Module
Thread-safe storage using JSON Lines format with exclusive file locking.

Uses fcntl.flock on Unix/Linux/macOS, and threading.Lock on Windows for 
cross-platform file locking support.

Usage:
    from storage.jsonl_queue import append_jsonl, read_jsonl
    
    # Append a record
    append_jsonl('data/queue.jsonl', {'user_id': 1, 'action': 'buy'})
    
    # Read all records
    records = read_jsonl('data/queue.jsonl')
"""

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, List, Dict

# Global locks per file path for thread safety (especially on Windows)
_file_locks = {}
_locks_lock = threading.Lock()


def _get_file_lock(path: str) -> threading.Lock:
    """Get or create a threading lock for a file path."""
    with _locks_lock:
        if path not in _file_locks:
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


# Cross-platform file locking
if sys.platform == 'win32':
    LOCK_EX = 1
    LOCK_SH = 2
    LOCK_UN = 0
    
    def lock_file(f, lock_type):
        """Windows: Use threading locks via context manager pattern."""
        # On Windows, we use threading.Lock stored globally per file
        # The lock is acquired before calling this function
        pass
    
    def acquire_file_lock(path: str):
        """Acquire thread lock for file (Windows)."""
        return _get_file_lock(path).__enter__()
    
    def release_file_lock(f):
        """Release thread lock for file (Windows)."""
        pass

else:
    import fcntl
    
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_UN = fcntl.LOCK_UN
    
    def lock_file(f, lock_type):
        """Unix: Use fcntl.flock for file locking."""
        fcntl.flock(f.fileno(), lock_type)
    
    def acquire_file_lock(path: str):
        """Acquire file lock (Unix - file handle based)."""
        return None  # File locking done via fcntl
    
    def release_file_lock(f):
        """Release file lock (Unix - file handle based)."""
        pass


def append_jsonl(path: str, record: Dict[str, Any]) -> None:
    """
    Append a JSON record to a JSONL file with exclusive file locking.
    
    Uses fcntl.flock (Unix) or threading.Lock (Windows) for thread-safe 
    exclusive locking to ensure atomicity of writes. Flushes and syncs to 
    disk for durability.
    
    Args:
        path: File path to JSONL file (creates if doesn't exist)
        record: Dictionary to append as JSON line
    
    Raises:
        IOError: If file locking fails
        ValueError: If record is not JSON serializable
    
    Example:
        append_jsonl('queue.jsonl', {'id': 1, 'status': 'pending'})
    """
    # Ensure directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    # Acquire thread lock on Windows
    if sys.platform == 'win32':
        lock = _get_file_lock(path)
        lock.acquire()
    
    try:
        # Open in append mode, create if doesn't exist
        with open(path, 'a') as f:
            # Acquire exclusive lock (Unix via fcntl)
            if sys.platform != 'win32':
                lock_file(f, LOCK_EX)
            
            # Write JSON line
            json.dump(record, f)
            f.write('\n')
            
            # Ensure data reaches disk
            f.flush()
            os.fsync(f.fileno())
            
            # Release lock (Unix via fcntl)
            if sys.platform != 'win32':
                lock_file(f, LOCK_UN)
    finally:
        # Release thread lock on Windows
        if sys.platform == 'win32':
            lock.release()


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    Read all records from a JSONL file.
    
    Args:
        path: File path to JSONL file
    
    Returns:
        List of dictionaries parsed from JSON lines
        Returns empty list if file doesn't exist
    
    Raises:
        ValueError: If any line is not valid JSON
    
    Example:
        records = read_jsonl('queue.jsonl')
        for record in records:
            print(record['id'])
    """
    if not os.path.exists(path):
        return []
    
    # Acquire thread lock on Windows
    if sys.platform == 'win32':
        lock = _get_file_lock(path)
        lock.acquire()
    
    try:
        records = []
        with open(path, 'r') as f:
            # Acquire shared lock (Unix via fcntl)
            if sys.platform != 'win32':
                lock_file(f, LOCK_SH)
            
            try:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # Skip empty lines
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError as e:
                            raise ValueError(
                                f"Invalid JSON at line {line_num} in {path}: {line[:50]}..."
                            ) from e
            finally:
                if sys.platform != 'win32':
                    lock_file(f, LOCK_UN)
        
        return records
    finally:
        # Release thread lock on Windows
        if sys.platform == 'win32':
            lock.release()


def clear_jsonl(path: str) -> None:
    """
    Clear all records from a JSONL file (truncate to empty).
    
    Args:
        path: File path to JSONL file
    """
    # Acquire thread lock on Windows
    if sys.platform == 'win32':
        lock = _get_file_lock(path)
        lock.acquire()
    
    try:
        with open(path, 'w') as f:
            # Acquire exclusive lock (Unix via fcntl)
            if sys.platform != 'win32':
                lock_file(f, LOCK_EX)
            
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())
            
            # Release lock (Unix via fcntl)
            if sys.platform != 'win32':
                lock_file(f, LOCK_UN)
    finally:
        # Release thread lock on Windows
        if sys.platform == 'win32':
            lock.release()
