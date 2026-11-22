import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fingerprints import calculate_file_hash


class FileHashTests(unittest.TestCase):
    def test_identical_content_has_same_hash(self):
        with TemporaryDirectory() as folder:
            first = Path(folder) / "first.png"
            second = Path(folder) / "second.png"

            first.write_bytes(b"same image contents")
            second.write_bytes(b"same image contents")

            self.assertEqual(
                calculate_file_hash(first),
                calculate_file_hash(second),
            )

    def test_changed_content_has_different_hash(self):
        with TemporaryDirectory() as folder:
            image = Path(folder) / "sample.png"
            image.write_bytes(b"original contents")
            original_hash = calculate_file_hash(image)

            image.write_bytes(b"updated contents")

            self.assertNotEqual(
                original_hash,
                calculate_file_hash(image),
            )


if __name__ == "__main__":
    unittest.main()