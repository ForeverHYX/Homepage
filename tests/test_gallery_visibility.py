import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
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
    def setUp(self) -> None:
        _cache.clear()

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

    def test_gallery_json_reads_are_cached_and_return_unpolluted_copies(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_file = root / "gallery_config.json"
            config_file.write_text(
                json.dumps({"visibility": {"Album": "public"}}),
                encoding="utf-8",
            )
            album_dir = root / "Album"
            album_dir.mkdir()
            (album_dir / "meta.json").write_text(
                json.dumps(
                    {
                        "title": "Original",
                        "extra": {"nested": "original"},
                    }
                ),
                encoding="utf-8",
            )
            original_reader = gallery_utils._read_json_object

            with patch.object(
                gallery_utils,
                "GALLERY_CONFIG_FILE",
                config_file,
            ), patch.object(
                gallery_utils,
                "_read_json_object",
                wraps=original_reader,
            ) as read_mock:
                first_visibility = gallery_utils.get_gallery_visibility_map()
                first_visibility["Album"] = "hidden"
                second_visibility = gallery_utils.get_gallery_visibility_map()

                first_meta = gallery_utils.get_folder_meta(album_dir)
                first_meta["title"] = "Polluted"
                first_meta["extra"]["nested"] = "polluted"
                second_meta = gallery_utils.get_folder_meta(album_dir)

            self.assertEqual(second_visibility["Album"], "public")
            self.assertEqual(second_meta["title"], "Original")
            self.assertEqual(second_meta["extra"]["nested"], "original")
            self.assertEqual(read_mock.call_count, 2)

    def test_gallery_writes_use_unique_atomic_temporary_files_and_invalidate(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_file = root / "gallery_config.json"
            config_file.write_text(
                json.dumps({"visibility": {"Album": "public"}}),
                encoding="utf-8",
            )
            album_dir = root / "Album"
            album_dir.mkdir()
            meta_file = album_dir / "meta.json"
            meta_file.write_text(
                json.dumps({"title": "Before"}),
                encoding="utf-8",
            )
            self.assertEqual(gallery_utils.get_folder_meta(album_dir)["title"], "Before")

            real_replace = os.replace
            temporary_paths: list[Path] = []

            def replace_and_observe(source, destination):
                source_path = Path(source)
                destination_path = Path(destination)
                temporary_paths.append(source_path)
                self.assertEqual(source_path.parent, destination_path.parent)
                self.assertTrue(source_path.name.startswith(f".{destination_path.name}."))
                json.loads(source_path.read_text(encoding="utf-8"))
                real_replace(source, destination)

            with patch.object(
                gallery_utils,
                "GALLERY_CONFIG_FILE",
                config_file,
            ), patch.object(
                gallery_utils.os,
                "replace",
                side_effect=replace_and_observe,
            ):
                gallery_utils.set_gallery_folder_visibility("Album", "private")
                gallery_utils.save_folder_meta(
                    album_dir,
                    "After",
                    "Description",
                    "2026-07-17",
                )
                self.assertEqual(
                    gallery_utils.get_gallery_visibility_map()["Album"],
                    "private",
                )
                self.assertEqual(
                    gallery_utils.get_folder_meta(album_dir)["title"],
                    "After",
                )

            self.assertEqual(len(temporary_paths), 2)
            self.assertEqual(len(set(temporary_paths)), 2)
            self.assertTrue(all(not path.exists() for path in temporary_paths))

    def test_concurrent_visibility_updates_do_not_lose_folders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "gallery_config.json"
            config_file.write_text("{}", encoding="utf-8")
            original_writer = gallery_utils._atomic_write_json

            def slow_writer(*args, **kwargs) -> None:
                time.sleep(0.02)
                original_writer(*args, **kwargs)

            with patch.object(
                gallery_utils,
                "GALLERY_CONFIG_FILE",
                config_file,
            ), patch.object(
                gallery_utils,
                "_atomic_write_json",
                side_effect=slow_writer,
            ), ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        gallery_utils.set_gallery_folder_visibility,
                        "Public",
                        "public",
                    ),
                    executor.submit(
                        gallery_utils.set_gallery_folder_visibility,
                        "Private",
                        "private",
                    ),
                ]
                for future in futures:
                    future.result()
                visibility = gallery_utils.get_gallery_visibility_map()

            self.assertEqual(
                visibility,
                {"Public": "public", "Private": "private"},
            )

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

    def test_saving_gallery_metadata_invalidates_the_merged_news_cache(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_dir = root / "content"
            upload_dir = root / "uploads"
            content_dir.mkdir()
            album_dir = upload_dir / "Yixing"
            album_dir.mkdir(parents=True)
            config_file = root / "gallery_config.json"
            config_file.write_text(
                json.dumps({"visibility": {"Yixing": "public"}}),
                encoding="utf-8",
            )
            gallery_utils.save_folder_meta(
                album_dir,
                "Before",
                "",
                "2026-01-01",
            )

            with patch.object(news, "CONTENT_DIR", content_dir), patch.object(
                news,
                "UPLOAD_DIR",
                upload_dir,
            ), patch.object(
                news,
                "GALLERY_CONFIG_FILE",
                config_file,
            ), patch.object(
                gallery_utils,
                "GALLERY_CONFIG_FILE",
                config_file,
            ):
                self.assertIn("Before", news.parse_and_merge_news())
                gallery_utils.save_folder_meta(
                    album_dir,
                    "After",
                    "",
                    "2026-01-01",
                )
                refreshed_news = news.parse_and_merge_news()

            self.assertIn("After", refreshed_news)
            self.assertNotIn("Before", refreshed_news)
