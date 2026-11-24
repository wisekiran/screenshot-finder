import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

# Supply a test-only key before importing the application.
with patch.dict(os.environ, {"SECRET_KEY": "test-only-secret-key"}):
    import app as web

import storage


class WebTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)

        patches = [
            patch.object(storage, "DATABASE_PATH", self.root / "test.db"),
            patch.object(web, "UPLOAD_ROOT", self.root / "uploads"),
            patch.object(web, "get_ocr_engine", return_value=object()),
            patch.object(
                web,
                "extract_text",
                return_value=["Pizza workshop"],
            ),
            patch.dict(
                web.app.config,
                {
                    "TESTING": True,
                    "SECRET_KEY": "test-only-secret-key",
                    "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
                },
            ),
        ]

        for patcher in patches:
            mocked = patcher.start()
            self.addCleanup(patcher.stop)

            if patcher is patches[3]:
                self.mock_ocr = mocked

        storage.initialize_database()
        self.client = web.app.test_client()

    def upload_image(self, client=None):
        """Generate a real PNG without using personal screenshots."""
        if client is None:
            client = self.client

        image_bytes = io.BytesIO()
        Image.new("RGB", (20, 20), color="yellow").save(
            image_bytes,
            format="PNG",
        )
        image_bytes.seek(0)

        return client.post(
            "/import",
            data={"screenshots": (image_bytes, "sample.png")},
            content_type="multipart/form-data",
        )

    def current_summary(self):
        with self.client.session_transaction() as browser_session:
            return dict(browser_session["last_import"])

    def test_import_redirects_and_confirmation_can_refresh(self):
        response = self.upload_image()

        self.assertEqual(response.status_code, 303)
        self.assertTrue(
            response.headers["Location"].endswith("/import/complete")
        )
        self.assertEqual(self.current_summary()["processed"], 1)

        for _ in range(2):
            confirmation = self.client.get("/import/complete")
            self.assertEqual(confirmation.status_code, 200)

        self.mock_ocr.assert_called_once()

    def test_duplicate_import_skips_ocr_and_extra_file(self):
        self.upload_image()
        self.upload_image()

        summary = self.current_summary()
        self.assertEqual(summary["processed"], 0)
        self.assertEqual(summary["duplicates_skipped"], 1)
        self.mock_ocr.assert_called_once()

        saved_images = list((self.root / "uploads").rglob("*.png"))
        self.assertEqual(len(saved_images), 1)

    def test_other_browser_cannot_search_or_open_image(self):
        self.upload_image()

        with self.client.session_transaction() as browser_session:
            collection_id = browser_session["collection_id"]

        matches = storage.search_screenshots("pizza", collection_id)
        self.assertEqual(len(matches), 1)
        screenshot_id = matches[0][0]
        image_url = f"/screenshots/{screenshot_id}"

        owner_search = self.client.get("/search?q=pizza")
        self.assertIn(
            image_url.encode(),
            owner_search.data,
        )

        owner_image = self.client.get(image_url)
        try:
            self.assertEqual(owner_image.status_code, 200)
        finally:
            owner_image.close()

        other_browser = web.app.test_client()

        other_search = other_browser.get("/search?q=pizza")
        self.assertEqual(other_search.status_code, 200)
        self.assertNotIn(image_url.encode(), other_search.data)
        self.assertEqual(
            other_browser.get(image_url).status_code,
            404,
        )

    def test_invalid_image_is_rejected_before_ocr(self):
        response = self.client.post(
            "/import",
            data={
                "screenshots": (
                    io.BytesIO(b"not an image"),
                    "fake.png",
                )
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.current_summary()["rejected"], 1)
        self.mock_ocr.assert_not_called()

    def test_upload_limit_shows_friendly_error(self):
        with patch.dict(web.app.config, {"MAX_CONTENT_LENGTH": 100}):
            response = self.client.post(
                "/import",
                data={
                    "screenshots": (
                        io.BytesIO(b"x" * 200),
                        "large.png",
                    )
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 413)
        self.assertIn(b"Too much evidence.", response.data)

    def test_ocr_failure_removes_unindexed_image(self):
        with patch.object(
            web,
            "extract_text",
            side_effect=RuntimeError("Simulated OCR failure"),
        ):
            response = self.upload_image()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            list((self.root / "uploads").rglob("*.png")),
            [],
        )

        with self.client.session_transaction() as browser_session:
            collection_id = browser_session["collection_id"]

        self.assertEqual(
            storage.search_screenshots("pizza", collection_id),
            [],
        )

    def test_delete_removes_only_current_collection(self):
        self.upload_image()

        with self.client.session_transaction() as browser_session:
            collection_id = browser_session["collection_id"]
            browser_session["form_token"] = "valid-test-token"

        screenshot_id = storage.search_screenshots(
            "pizza", collection_id
        )[0][0]
        image_path = storage.get_screenshot_path(
            screenshot_id, collection_id
        )

        other_browser = web.app.test_client()
        self.upload_image(other_browser)

        with other_browser.session_transaction() as browser_session:
            other_collection = browser_session["collection_id"]

        other_id = storage.search_screenshots(
            "pizza", other_collection
        )[0][0]

        response = self.client.post(
            "/collection/delete",
            data={"form_token": "valid-test-token"},
        )

        self.assertEqual(response.status_code, 303)
        self.assertFalse(image_path.exists())
        self.assertEqual(
            storage.search_screenshots("pizza", collection_id), []
        )
        self.assertEqual(
            self.client.get(f"/screenshots/{screenshot_id}").status_code,
            404,
        )

        # Another visitor's collection remains available.
        self.assertEqual(
            len(storage.search_screenshots("pizza", other_collection)),
            1,
        )
        other_image = other_browser.get(f"/screenshots/{other_id}")
        try:
            self.assertEqual(other_image.status_code, 200)
        finally:
            other_image.close()

    def test_delete_rejects_missing_or_wrong_token(self):
        self.upload_image()

        with self.client.session_transaction() as browser_session:
            collection_id = browser_session["collection_id"]
            browser_session["form_token"] = "expected-token"

        for submitted_data in [
            {},
            {"form_token": "wrong-token"},
        ]:
            with self.subTest(submitted_data=submitted_data):
                response = self.client.post(
                    "/collection/delete",
                    data=submitted_data,
                )
                self.assertEqual(response.status_code, 400)

        matches = storage.search_screenshots("pizza", collection_id)
        self.assertEqual(len(matches), 1)

        image_path = storage.get_screenshot_path(
            matches[0][0], collection_id
        )
        self.assertTrue(image_path.is_file())


if __name__ == "__main__":
    unittest.main()