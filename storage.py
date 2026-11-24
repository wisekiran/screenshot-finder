from contextlib import closing
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).parent / "data" / "screenshots.db"


def initialize_database() -> None:
    """Create the screenshots table and add missing columns."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL UNIQUE,
                    extracted_text TEXT NOT NULL,
                    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    file_hash TEXT,
                    collection_id TEXT NOT NULL DEFAULT 'local'
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

            if "collection_id" not in columns:
                connection.execute("""
                    ALTER TABLE screenshots
                    ADD COLUMN collection_id TEXT NOT NULL DEFAULT 'local'
                """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_screenshots_collection_hash
                ON screenshots (collection_id, file_hash)
            """)

def save_screenshot(
    image_path: Path,
    lines: list[str],
    file_hash: str,
    collection_id: str = "local",
) -> None:
    """Save OCR text and its fingerprint within a collection."""
    file_path = str(image_path.resolve())
    extracted_text = "\n".join(lines)

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO screenshots (
                    file_path, extracted_text, file_hash, collection_id
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    extracted_text = excluded.extracted_text,
                    file_hash = excluded.file_hash,
                    indexed_at = CURRENT_TIMESTAMP
                WHERE screenshots.collection_id = excluded.collection_id
                """,
                (file_path, extracted_text, file_hash, collection_id),
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

def search_screenshots(
    query: str,
    collection_id: str = "local",
) -> list[tuple[int, str]]:
    """Find matching screenshots within one collection."""
    query = query.strip()

    if not query:
        return []

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        rows = connection.execute(
            """
            SELECT id, file_path
            FROM screenshots
            WHERE collection_id = ?
              AND instr(lower(extracted_text), lower(?)) > 0
            ORDER BY id
            """,
            (collection_id, query),
        ).fetchall()

    return rows

def find_screenshot_by_hash(
    file_hash: str,
    collection_id: str,
) -> int | None:
    """Return an existing screenshot ID for this content and collection."""
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        row = connection.execute(
            """
            SELECT id
            FROM screenshots
            WHERE collection_id = ? AND file_hash = ?
            ORDER BY id
            LIMIT 1
            """,
            (collection_id, file_hash),
        ).fetchone()

    return None if row is None else row[0]

def get_screenshot_path(
    screenshot_id: int,
    collection_id: str,
) -> Path | None:
    """Find an image path only within the requested collection."""
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        row = connection.execute(
            """
            SELECT file_path
            FROM screenshots
            WHERE id = ? AND collection_id = ?
            """,
            (screenshot_id, collection_id),
        ).fetchone()

    return None if row is None else Path(row[0])

def delete_collection(collection_id: str) -> int:
    """Remove a collection's image files and database records."""
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        rows = connection.execute(
            """
            SELECT file_path
            FROM screenshots
            WHERE collection_id = ?
            """,
            (collection_id,),
        ).fetchall()

        for (file_path,) in rows:
            Path(file_path).unlink(missing_ok=True)

        with connection:
            connection.execute(
                "DELETE FROM screenshots WHERE collection_id = ?",
                (collection_id,),
            )

    return len(rows)

def expire_web_uploads(
    max_age_hours: int = 24,
    dry_run: bool = True,
) -> int:
    """Find or delete expired web images and their database records."""
    if max_age_hours < 1:
        raise ValueError("Expiry must be at least one hour.")

    modifier = f"-{max_age_hours} hours"

    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            # Prevent another writer from updating selected records
            # while cleanup is removing their files.
            connection.execute("BEGIN IMMEDIATE")

            rows = connection.execute(
                """
                SELECT id, file_path
                FROM screenshots
                WHERE collection_id != 'local'
                  AND indexed_at <= datetime('now', ?)
                """,
                (modifier,),
            ).fetchall()

            if not dry_run:
                for screenshot_id, file_path in rows:
                    Path(file_path).unlink(missing_ok=True)

                    connection.execute(
                        "DELETE FROM screenshots WHERE id = ?",
                        (screenshot_id,),
                    )

    return len(rows)