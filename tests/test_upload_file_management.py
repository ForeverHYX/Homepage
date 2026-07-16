import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import gallery_utils
from app.main import app
from app.routers import upload


class UploadFileManagementTests(TestCase):
    def test_file_list_hides_internal_entries_and_exposes_file_behavior(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            (upload_dir / "_thumbs").mkdir()
            (upload_dir / ".staging.pdf").write_bytes(b"staging")
            (upload_dir / "photo.png").write_bytes(b"png")
            (upload_dir / "resume.pdf").write_bytes(b"pdf")
            (upload_dir / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (upload_dir / "bundle.zip").write_bytes(b"zip")

            with patch.object(upload, "UPLOAD_DIR", upload_dir), patch.object(
                upload, "require_login", return_value=None
            ):
                response = TestClient(app).get("/api/files")

            self.assertEqual(response.status_code, 200)
            by_name = {item["name"]: item for item in response.json()["files"]}
            self.assertNotIn("_thumbs", by_name)
            self.assertNotIn(".staging.pdf", by_name)
            self.assertEqual(by_name["photo.png"]["file_kind"], "image")
            self.assertTrue(by_name["photo.png"]["is_previewable"])
            self.assertEqual(by_name["resume.pdf"]["file_kind"], "pdf")
            self.assertTrue(by_name["data.csv"]["is_previewable"])
            self.assertEqual(by_name["bundle.zip"]["file_kind"], "archive")
            self.assertFalse(by_name["bundle.zip"]["is_previewable"])
            self.assertIn("download=true", by_name["bundle.zip"]["download_url"])

    def test_delete_accepts_unicode_nested_paths_and_cleans_gallery_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            album_dir = upload_dir / "旅行 照片"
            album_dir.mkdir(parents=True)
            (album_dir / "photo 01.webp").write_bytes(b"image")
            thumbnail_dir = upload_dir / "_thumbs" / "旅行 照片"
            thumbnail_dir.mkdir(parents=True)
            (thumbnail_dir / "photo 01.webp").write_bytes(b"thumb")
            config_file = root / "gallery_config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "folders": ["旅行 照片"],
                        "visibility": {"旅行 照片": "public"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(upload, "UPLOAD_DIR", upload_dir), patch.object(
                upload, "require_login", return_value=None
            ), patch.object(gallery_utils, "GALLERY_CONFIG_FILE", config_file):
                response = TestClient(app).post(
                    "/api/files/delete",
                    data={"path": "旅行 照片"},
                )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(album_dir.exists())
            self.assertFalse(thumbnail_dir.exists())
            stored = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertEqual(stored, {"folders": [], "visibility": {}})

    def test_rename_handles_spaces_conflicts_and_thumbnail_cleanup(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Album"
            album_dir.mkdir()
            original = album_dir / "old photo.webp"
            original.write_bytes(b"image")
            thumbnail = upload_dir / "_thumbs" / "Album" / "old photo.webp"
            thumbnail.parent.mkdir(parents=True)
            thumbnail.write_bytes(b"thumb")

            with patch.object(upload, "UPLOAD_DIR", upload_dir), patch.object(
                upload, "require_login", return_value=None
            ):
                response = TestClient(app).post(
                    "/api/files/rename",
                    data={"path": "Album/old photo.webp", "new_name": "new photo.webp"},
                )
                invalid = TestClient(app).post(
                    "/api/files/rename",
                    data={"path": "Album/new photo.webp", "new_name": "../escape.webp"},
                )
                (album_dir / "existing.webp").write_bytes(b"existing")
                conflict = TestClient(app).post(
                    "/api/files/rename",
                    data={"path": "Album/new photo.webp", "new_name": "existing.webp"},
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["name"], "new photo.webp")
            self.assertFalse(original.exists())
            self.assertTrue((album_dir / "new photo.webp").exists())
            self.assertFalse(thumbnail.exists())
            self.assertEqual(invalid.status_code, 400)
            self.assertEqual(conflict.status_code, 409)
