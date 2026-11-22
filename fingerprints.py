import hashlib
from pathlib import Path


def calculate_file_hash(file_path: Path) -> str:
    """Calculate a SHA-256 fingerprint of a file's contents."""
    hasher = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            hasher.update(chunk)

    return hasher.hexdigest()