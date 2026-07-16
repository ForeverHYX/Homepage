import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import gallery_utils, news
from app.cache import _cache
from app.main import app
from app.routers import pages, upload


def _make_album(upload_dir: Path, name: str) -> None:
    album_dir = upload_dir / name
    album_dir.mkdir(parents=True)
    Image.new("RGB", (32, 32), "navy").save(album_dir / "photo.webp", "WEBP")


def _write_gallery_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "folders": ["Legacy"],
                "visibility": {
                    "Public": "public",
                    "Private": "private",
                    "Hidden": "hidden",
                },
            }
        ),
        encoding="utf-8",
    )


class GalleryVisibilityTests(TestCase):
    def test_gallery_api_filters_private_albums_by_upload_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            config_file = root / "gallery_config.json"
            for album in ["Legacy", "Public", "Private", "Hidden"]:
                _make_album(upload_dir, album)
            _write_gallery_config(config_file)

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                gallery_utils, "GALLERY_CONFIG_FILE", config_file
            ):
                with patch("app.routers.pages.get_current_user", return_value=False):
                    response = TestClient(app).get("/api/site/gallery")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["cache-control"], "public, max-age=60")
                self.assertEqual(response.headers["vary"], "Cookie")
                self.assertEqual(
                    {album["rel_path"] for album in response.json()["albums"]},
                    {"Legacy", "Public"},
                )

                with patch("app.routers.pages.get_current_user", return_value=True):
                    response = TestClient(app).get("/api/site/gallery")
                self.assertEqual(response.headers["cache-control"], "private, no-store")
                self.assertEqual(response.headers["vary"], "Cookie")
                self.assertEqual(
                    {album["rel_path"] for album in response.json()["albums"]},
                    {"Legacy", "Public", "Private"},
                )

    def test_private_focused_album_is_unavailable_without_upload_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            config_file = root / "gallery_config.json"
            _make_album(upload_dir, "Private")
            _write_gallery_config(config_file)

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                gallery_utils, "GALLERY_CONFIG_FILE", config_file
            ):
                with patch("app.routers.pages.get_current_user", return_value=False):
                    response = TestClient(app).get("/api/site/gallery?focus=Private")
                self.assertEqual(response.json()["albums"], [])
                self.assertFalse(response.json()["is_focused"])

                with patch("app.routers.pages.get_current_user", return_value=True):
                    response = TestClient(app).get("/api/site/gallery?focus=Private")
                self.assertEqual([album["rel_path"] for album in response.json()["albums"]], ["Private"])
                self.assertTrue(response.json()["is_focused"])

    def test_upload_file_list_exposes_gallery_visibility(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            config_file = root / "gallery_config.json"
            for album in ["Public", "Private", "Hidden"]:
                (upload_dir / album).mkdir()
            _write_gallery_config(config_file)

            with patch.object(upload, "UPLOAD_DIR", upload_dir), patch.object(
                gallery_utils, "GALLERY_CONFIG_FILE", config_file
            ), patch.object(upload, "require_login", return_value=None):
                response = TestClient(app).get("/api/files")

            self.assertEqual(response.status_code, 200)
            by_path = {item["path"]: item for item in response.json()["files"]}
            self.assertEqual(by_path["Public"]["gallery_visibility"], "public")
            self.assertEqual(by_path["Private"]["gallery_visibility"], "private")
            self.assertEqual(by_path["Hidden"]["gallery_visibility"], "hidden")
            self.assertTrue(by_path["Public"]["is_gallery"])
            self.assertTrue(by_path["Private"]["is_gallery"])
            self.assertFalse(by_path["Hidden"]["is_gallery"])

    def test_upload_visibility_endpoint_updates_gallery_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            config_file = root / "gallery_config.json"
            (upload_dir / "Album").mkdir()

            with patch.object(upload, "UPLOAD_DIR", upload_dir), patch.object(
                gallery_utils, "GALLERY_CONFIG_FILE", config_file
            ), patch.object(upload, "require_login", return_value=None):
                response = TestClient(app).post(
                    "/api/gallery/visibility",
                    data={"path": "Album", "visibility": "private"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["visibility"], "private")

            stored = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(stored["visibility"], {"Album": "private"})
            self.assertEqual(stored["folders"], [])

    def test_gallery_page_empty_state_says_no_available(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            config_file = root / "gallery_config.json"
            _make_album(upload_dir, "Private")
            config_file.write_text(
                json.dumps({"visibility": {"Private": "private"}}),
                encoding="utf-8",
            )

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                gallery_utils, "GALLERY_CONFIG_FILE", config_file
            ), patch("app.routers.pages.get_current_user", return_value=False):
                response = TestClient(app).get("/gallery")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "public, max-age=60")
            self.assertEqual(response.headers["vary"], "Cookie")
            self.assertIn("No available albums.", response.text)

    def test_upload_page_contains_visibility_editor_control(self) -> None:
        response = TestClient(app).get("/upload")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="metaGalleryVisibility"', response.text)
        self.assertIn("Login-only Gallery", response.text)

    def test_news_cache_uses_gallery_config_mtime(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_dir = root / "content"
            upload_dir = root / "uploads"
            content_dir.mkdir()
            upload_dir.mkdir()
            config_file = root / "gallery_config.json"
            album_dir = upload_dir / "Yixing"
            album_dir.mkdir()
            (album_dir / "meta.json").write_text(
                json.dumps({"title": "Bamboo Sea", "date": "2026-01-01"}),
                encoding="utf-8",
            )
            config_file.write_text(
                json.dumps({"visibility": {"Yixing": "public"}}),
                encoding="utf-8",
            )

            _cache.clear()
            with patch.object(news, "CONTENT_DIR", content_dir), patch.object(
                news, "UPLOAD_DIR", upload_dir
            ), patch.object(
                news, "GALLERY_CONFIG_FILE", config_file
            ), patch.object(gallery_utils, "GALLERY_CONFIG_FILE", config_file):
                public_news = news.parse_and_merge_news(limit=6)
                self.assertIn("Bamboo Sea", public_news)

                time.sleep(0.01)
                config_file.write_text(
                    json.dumps({"visibility": {"Yixing": "private"}}),
                    encoding="utf-8",
                )

                private_news = news.parse_and_merge_news(limit=6)
                self.assertNotIn("Bamboo Sea", private_news)
