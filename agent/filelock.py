"""
Cross-process file locking via atomic directory creation.

Provides a single context manager ``locked_json_read_write`` that:
  1. Reads a JSON file from disk.
  2. Yields the parsed data to the caller for mutation.
  3. Writes the (possibly modified) data back to the same file.

The lock is implemented by creating an empty directory at a well-known
path under ``.locks/``. ``os.makedirs(lock, exist_ok=False)`` is atomic
on Windows (NTFS) and POSIX — it succeeds for exactly one process and
raises ``FileExistsError`` for all others. This avoids the complexity of
``portalocker`` or platform-specific fcntl/flock calls.

Limitations:
  - Lock files are **not** automatically cleaned up on crash (the
    ``finally`` block calls ``os.rmdir``, but if the process is killed
    mid-write the lock directory will remain and must be removed manually).
  - Timeout is configurable; the default is 5 seconds with 50 ms retry
    intervals.
"""
import os
import time
import json
import tempfile
import contextlib


LOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".locks")


def _lock_path(target_file: str) -> str:
    """Return the filesystem path for the lock directory of *target_file*.

    The target path's special characters (``\\``, ``/``, ``:``) are replaced
    with underscores to produce a safe directory name inside ``.locks/``.

    Args:
        target_file: Absolute path to the file being protected.

    Returns:
        An absolute path to a lock directory (no file extension).
    """
    os.makedirs(LOCK_DIR, exist_ok=True)
    safe_name = target_file.replace("\\", "_").replace("/", "_").replace(":", "_")
    return os.path.join(LOCK_DIR, f"{safe_name}.lock")


@contextlib.contextmanager
def locked_json_read_write(filepath: str, default: dict | list | None = None, timeout: float = 5.0):
    """Read a JSON file, yield for mutation, then write it back.

    A filesystem-based lock ensures only one process accesses the file at
    a time. The lock is released in the ``finally`` block even if an
    exception occurs inside the ``with`` block.

    Args:
        filepath: Path to the JSON file to read/write.
        default: Fallback value if the file does not exist or contains
            invalid JSON. Must be a ``dict``, ``list``, or ``None``.
        timeout: Maximum seconds to wait for the lock before raising
            ``TimeoutError`` (default 5.0). Each failed acquisition attempt
            sleeps 50 ms.

    Yields:
        The parsed JSON data (``dict`` or ``list``) or *default* if the
        file is missing or corrupt.

    Raises:
        TimeoutError: If the lock cannot be acquired within *timeout*
            seconds. This usually indicates a long-running writer or a
            stale lock directory that needs manual removal.
        OSError: Propagated from ``os.makedirs`` or file I/O.

    Example:
        >>> with locked_json_read_write("data.json", default={}) as data:
        ...     data["counter"] += 1
    """
    lock = _lock_path(filepath)
    deadline = time.time() + timeout
    # Busy-wait with 50 ms sleep — cheap enough for the expected low-contention
    # use case (occasional background ingestion writes).
    while True:
        try:
            os.makedirs(lock, exist_ok=False)
            break
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"Could not acquire lock for {filepath} within {timeout}s")
            time.sleep(0.05)

    try:
        data = default
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    # If the file is truncated or corrupt, fall back to default
                    # rather than crashing. The next successful write will
                    # overwrite it with a valid document.
                    data = default
        yield data
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    finally:
        os.rmdir(lock)
