
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
