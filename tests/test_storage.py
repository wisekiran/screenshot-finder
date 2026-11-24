import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import storage


class StorageTests(unittest.TestCase):
    def test_rescan_updates_existing_record(self):
        with TemporaryDirectory() as folder:
            database_path = Path(folder) / "test.db"
            image_path = Path(folder) / "sample.png"

            with patch.object(storage, "DATABASE_PATH", database_path):
                storage.initialize_database()

                storage.save_screenshot(
                    image_path, ["Pizza workshop"], "original-hash"
                )

                self.assertTrue(
                    storage.is_screenshot_unchanged(
                        image_path, "original-hash"
                    )
                )
                self.assertFalse(
                    storage.is_screenshot_unchanged(
                        image_path, "updated-hash"
                    )
                )

                storage.save_screenshot(
                    image_path, ["Embroidery class"], "updated-hash"
                )

                with closing(
                    sqlite3.connect(database_path)
                ) as connection:
                    count = connection.execute(
                        "SELECT COUNT(*) FROM screenshots"
                    ).fetchone()[0]

                self.assertEqual(count, 1)
                self.assertEqual(
                    storage.search_screenshots("pizza"), []
                )

                matches = storage.search_screenshots("EMBROIDERY")
                self.assertEqual(len(matches), 1)
                self.assertEqual(
                    matches[0][1], str(image_path.resolve())
                )
                self.assertTrue(
                    storage.is_screenshot_unchanged(
                        image_path, "updated-hash"
                    )
                )

    def test_search_and_hash_lookup_stay_within_collection(self):
        with TemporaryDirectory() as folder:
            database_path = Path(folder) / "test.db"
            first_image = Path(folder) / "first.png"
            second_image = Path(folder) / "second.png"

            with patch.object(storage, "DATABASE_PATH", database_path):
                storage.initialize_database()

                storage.save_screenshot(
                    first_image,
                    ["Pizza workshop"],
                    "same-content-hash",
                    collection_id="collection-a",
                )

                # A different collection cannot find the first image.
                self.assertEqual(
                    storage.search_screenshots("pizza", "collection-b"),
                    [],
                )
                self.assertIsNone(
                    storage.find_screenshot_by_hash(
                        "same-content-hash", "collection-b"
                    )
                )

                # The same content can belong to another collection.
                storage.save_screenshot(
                    second_image,
                    ["Pizza workshop"],
                    "same-content-hash",
                    collection_id="collection-b",
                )

                for collection_id, expected_path in [
                    ("collection-a", first_image),
                    ("collection-b", second_image),
                ]:
                    with self.subTest(collection_id=collection_id):
                        matches = storage.search_screenshots(
                            "PIZZA", collection_id
                        )

                        self.assertEqual(len(matches), 1)
                        self.assertEqual(
                            matches[0][1],
                            str(expected_path.resolve()),
                        )
                        self.assertEqual(
                            storage.find_screenshot_by_hash(
                                "same-content-hash", collection_id
                            ),
                            matches[0][0],
                        )

    def test_expiry_preserves_recent_and_local_records(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)

            with patch.object(storage, "DATABASE_PATH", root / "test.db"):
                storage.initialize_database()

                for filename, collection in [
                    ("expired.png", "web-old"),
                    ("recent.png", "web-new"),
                    ("local.png", "local"),
                ]:
                    image = root / filename
                    image.write_bytes(b"test contents")
                    storage.save_screenshot(
                        image, ["Pizza"], filename, collection
                    )

                with closing(sqlite3.connect(storage.DATABASE_PATH)) as connection:
                    with connection:
                        connection.execute(
                            """
                            UPDATE screenshots
                            SET indexed_at = datetime('now', '-48 hours')
                            WHERE collection_id IN ('web-old', 'local')
                            """
                        )

                self.assertEqual(storage.expire_web_uploads(), 1)
                self.assertTrue((root / "expired.png").exists())

                self.assertEqual(
                    storage.expire_web_uploads(dry_run=False), 1
                )
                self.assertFalse((root / "expired.png").exists())
                self.assertTrue((root / "recent.png").exists())
                self.assertTrue((root / "local.png").exists())

                self.assertEqual(
                    storage.search_screenshots("pizza", "web-old"), []
                )
                self.assertEqual(
                    len(storage.search_screenshots("pizza", "web-new")), 1
                )
                self.assertEqual(
                    len(storage.search_screenshots("pizza", "local")), 1
                )


if __name__ == "__main__":
    unittest.main()