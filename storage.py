from contextlib import closing
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).parent / "data" / "screenshots.db"


def initialize_database() -> None:
    """Create the screenshot table if it does not exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE,
                extracted_text TEXT NOT NULL,
                indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_screenshot(image_path: Path, lines: list[str]) -> None:
    """Save extracted text, updating the record if its path already exists."""
    file_path = str(image_path.resolve())
    extracted_text = "\n".join(lines)

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO screenshots (file_path, extracted_text)
                VALUES (?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    extracted_text = excluded.extracted_text,
                    indexed_at = CURRENT_TIMESTAMP
                """,
                (file_path, extracted_text),
            )