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


if __name__ == "__main__":
    unittest.main()