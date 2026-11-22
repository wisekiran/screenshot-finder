from contextlib import closing
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).parent / "data" / "screenshots.db"


def initialize_database() -> None:
    """Create the table and add any missing fingerprint column."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    extracted_text TEXT NOT NULL,
                    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    file_hash TEXT
                )
            """)

            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(screenshots)"
                ).fetchall()
            }

            if "file_hash" not in columns:
                connection.execute(
                    "ALTER TABLE screenshots ADD COLUMN file_hash TEXT"
                )

def save_screenshot(
    image_path: Path,
    lines: list[str],
    file_hash: str,
) -> None:
    """Save OCR text and the fingerprint of the processed image."""
    file_path = str(image_path.resolve())
    extracted_text = "\n".join(lines)

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO screenshots (
                    file_path, extracted_text, file_hash
                )
                VALUES (?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    extracted_text = excluded.extracted_text,
                    file_hash = excluded.file_hash,
                    indexed_at = CURRENT_TIMESTAMP
                """,
                (file_path, extracted_text, file_hash),
            )

def is_screenshot_unchanged(image_path: Path, file_hash: str) -> bool:
    """Check whether this path already has the same saved fingerprint."""
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        row = connection.execute(
            """
            SELECT file_hash
            FROM screenshots
            WHERE file_path = ?
            """,
            (str(image_path.resolve()),),
        ).fetchone()

    return row is not None and row[0] == file_hash

def search_screenshots(query: str) -> list[tuple[int, str]]:
    """Find screenshots containing the query, ignoring letter case."""
    query = query.strip()

    if not query:
        return []

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        rows = connection.execute(
            """
            SELECT id, file_path
            FROM screenshots
            WHERE instr(lower(extracted_text), lower(?)) > 0
            ORDER BY id
            """,
            (query,),
        ).fetchall()

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(screenshots)"
            ).fetchall()
        }

        if "file_hash" not in columns:
            connection.execute(
                "ALTER TABLE screenshots ADD COLUMN file_hash TEXT"
            )

        connection.commit()

    return rows