"""Simple cross-process file locking for JSON read/write safety."""
import os
import time
import json
import tempfile
import contextlib


LOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".locks")


def _lock_path(target_file: str) -> str:
    os.makedirs(LOCK_DIR, exist_ok=True)
    safe_name = target_file.replace("\\", "_").replace("/", "_").replace(":", "_")
    return os.path.join(LOCK_DIR, f"{safe_name}.lock")


@contextlib.contextmanager
def locked_json_read_write(filepath: str, default: dict | list | None = None, timeout: float = 5.0):
    """Read a JSON file, yield for mutation, then write it back.
    Uses filesystem-level locking via temporary directory creation (atomic on most OSes)."""
    lock = _lock_path(filepath)
    deadline = time.time() + timeout
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
                    data = default
        yield data
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    finally:
        os.rmdir(lock)
