import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import auth, gallery_utils, templating
from app import main as main_module
from app.main import app
from app.routers import media as media_router
from app.routers import pages, upload
from app.services import media as media_service
from app.services import share_links


class AnonymousAccessBoundaryTests(TestCase):
    def test_upload_page_redirects_before_rendering_admin_controls(self) -> None:
        with patch.object(pages, "get_current_user", return_value=False):
            response = TestClient(app, follow_redirects=False).get("/upload")

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login?next=%2Fupload")
        self.assertNotIn("Upload Manager", response.text)

    def test_public_navigation_hides_upload_link(self) -> None:
        with patch.object(templating, "get_current_user", return_value=False):
            response = TestClient(app).get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('href="/upload"', response.text)

    def test_authenticated_navigation_and_upload_page_remain_available(self) -> None:
        with (
            patch.object(pages, "get_current_user", return_value=True),
            patch.object(templating, "get_current_user", return_value=True),
        ):
            response = TestClient(app).get("/upload")

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/upload"', response.text)
        self.assertIn("Upload Manager", response.text)
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_file_listing_download_and_mutations_require_login(self) -> None:
        client = TestClient(app)
        responses = [
            client.get("/api/files"),
            client.get("/api/files/private.pdf"),
            client.post("/api/folder", data={"name": "blocked"}),
            client.post("/api/files/delete", data={"path": "blocked"}),
            client.post(
                "/api/files/rename",
                data={"path": "blocked", "new_name": "still-blocked.txt"},
            ),
            client.post("/api/files/share", data={"path": "blocked"}),
        ]

        self.assertTrue(all(response.status_code == 401 for response in responses))

    def test_authenticated_cross_origin_mutation_is_rejected(self) -> None:
        with patch.object(auth, "get_current_user", return_value=True):
            response = TestClient(app).post(
                "/api/folder",
                data={"name": "blocked"},
                headers={"Origin": "https://attacker.example"},
            )

        self.assertEqual(response.status_code, 403)

    def test_robots_excludes_admin_api_and_share_routes(self) -> None:
        response = TestClient(app).get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Disallow: /api/", response.text)
        self.assertIn("Disallow: /login", response.text)
        self.assertIn("Disallow: /share/", response.text)
        self.assertIn("Disallow: /upload", response.text)


class UploadedMediaAccessTests(TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        upload_dir = root / "uploads"
        for folder in [
            "Public/PrivateNested",
            "Private",
            "Hidden",
            "_thumbs/Public/PrivateNested",
        ]:
            (upload_dir / folder).mkdir(parents=True, exist_ok=True)
        for relative_path in [
            "Public/photo.webp",
            "Public/PrivateNested/photo.webp",
            "Private/photo.webp",
            "Hidden/photo.webp",
            "_thumbs/Public/photo.webp.v2.webp",
            "_thumbs/Public/PrivateNested/photo.webp.v2.webp",
        ]:
            (upload_dir / relative_path).write_bytes(relative_path.encode("utf-8"))
        (upload_dir / "resume.pdf").write_bytes(b"public-resume")
        (upload_dir / "secret.pdf").write_bytes(b"private-secret")
        config_file = root / "gallery_config.json"
        config_file.write_text(
            '{"visibility":{"Public":"public","Public/PrivateNested":"private",'
            '"Private":"private","Hidden":"hidden"}}',
            encoding="utf-8",
        )
        return upload_dir, config_file

    def test_only_explicit_site_assets_and_public_gallery_media_are_anonymous(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir, config_file = self._fixture(Path(temp_dir))
            with (
                patch.object(media_service, "UPLOAD_DIR", upload_dir),
                patch.object(gallery_utils, "GALLERY_CONFIG_FILE", config_file),
                patch.object(media_service, "USE_X_ACCEL_REDIRECT", False),
            ):
                client = TestClient(app)
                public_album = client.get("/uploads/Public/photo.webp")
                public_thumbnail = client.get("/uploads/_thumbs/Public/photo.webp.v2.webp")
                public_resume = client.get("/uploads/resume.pdf")
                nested_private = client.get("/uploads/Public/PrivateNested/photo.webp")
                nested_private_thumbnail = client.get(
                    "/uploads/_thumbs/Public/PrivateNested/photo.webp.v2.webp"
                )
                private_album = client.get("/uploads/Private/photo.webp")
                hidden_album = client.get("/uploads/Hidden/photo.webp")
                ordinary_file = client.get("/uploads/secret.pdf")

            self.assertEqual(public_album.status_code, 200)
            self.assertEqual(public_thumbnail.status_code, 200)
            self.assertEqual(public_resume.status_code, 200)
            self.assertEqual(nested_private.status_code, 404)
            self.assertEqual(nested_private_thumbnail.status_code, 404)
            self.assertEqual(private_album.status_code, 404)
            self.assertEqual(hidden_album.status_code, 404)
            self.assertEqual(ordinary_file.status_code, 404)
            self.assertEqual(
                public_album.headers["cache-control"],
                media_service.PUBLIC_MEDIA_CACHE_CONTROL,
            )

    def test_authenticated_private_media_is_no_store(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir, config_file = self._fixture(Path(temp_dir))
            with (
                patch.object(media_service, "UPLOAD_DIR", upload_dir),
                patch.object(gallery_utils, "GALLERY_CONFIG_FILE", config_file),
                patch.object(media_service, "USE_X_ACCEL_REDIRECT", False),
                patch.object(media_router, "get_current_user", return_value=True),
            ):
                response = TestClient(app).get("/uploads/Private/photo.webp")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            self.assertEqual(response.headers["x-robots-tag"], "noindex, nofollow, noarchive")

    def test_production_response_delegates_bytes_to_internal_nginx_location(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir, config_file = self._fixture(Path(temp_dir))
            with (
                patch.object(media_service, "UPLOAD_DIR", upload_dir),
                patch.object(gallery_utils, "GALLERY_CONFIG_FILE", config_file),
                patch.object(media_service, "USE_X_ACCEL_REDIRECT", True),
            ):
                response = TestClient(app).get("/uploads/Public/photo.webp")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers["x-accel-redirect"],
                "/_homepage_uploads/Public/photo.webp",
            )
            self.assertEqual(response.content, b"")


class ShareLinkTests(TestCase):
    def test_share_link_is_stable_public_and_preserved_across_rename(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            original = upload_dir / "private file.pdf"
            original.write_bytes(b"shared-content")
            share_file = root / ".share-links.json"

            with (
                patch.object(upload, "UPLOAD_DIR", upload_dir),
                patch.object(media_service, "UPLOAD_DIR", upload_dir),
                patch.object(media_service, "USE_X_ACCEL_REDIRECT", False),
                patch.object(share_links, "SHARE_LINK_FILE", share_file),
                patch.object(upload, "require_login", return_value=None),
            ):
                client = TestClient(app)
                direct = client.get("/uploads/private%20file.pdf")
                created = client.post("/api/files/share", data={"path": "private file.pdf"})
                repeated = client.post("/api/files/share", data={"path": "private file.pdf"})
                share_url = created.json()["url"]
                shared = client.get(share_url)
                renamed = client.post(
                    "/api/files/rename",
                    data={"path": "private file.pdf", "new_name": "renamed.pdf"},
                )
                shared_after_rename = client.get(share_url)

            self.assertEqual(direct.status_code, 404)
            self.assertEqual(created.status_code, 200)
            self.assertEqual(repeated.json()["url"], share_url)
            self.assertTrue(share_url.startswith("/share/"))
            self.assertEqual(shared.status_code, 200)
            self.assertEqual(shared.content, b"shared-content")
            self.assertEqual(renamed.status_code, 200)
            self.assertEqual(shared_after_rename.content, b"shared-content")
            self.assertEqual(stat.S_IMODE(share_file.stat().st_mode), 0o600)
            self.assertEqual(list(share_file.parent.glob(".*.tmp")), [])

    def test_deleted_file_invalidates_its_share_link(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            upload_dir = root / "uploads"
            upload_dir.mkdir()
            (upload_dir / "temporary.pdf").write_bytes(b"temporary")
            share_file = root / ".share-links.json"

            with (
                patch.object(upload, "UPLOAD_DIR", upload_dir),
                patch.object(media_service, "UPLOAD_DIR", upload_dir),
                patch.object(media_service, "USE_X_ACCEL_REDIRECT", False),
                patch.object(share_links, "SHARE_LINK_FILE", share_file),
                patch.object(upload, "require_login", return_value=None),
            ):
                client = TestClient(app)
                share_url = client.post("/api/files/share", data={"path": "temporary.pdf"}).json()[
                    "url"
                ]
                deleted = client.post("/api/files/delete", data={"path": "temporary.pdf"})
                unavailable = client.get(share_url)

            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(unavailable.status_code, 404)


class ProductionSurfaceTests(TestCase):
    def test_api_docs_can_be_disabled_for_production(self) -> None:
        with patch.object(main_module, "ENABLE_API_DOCS", False):
            production_app = main_module.create_app()
        client = TestClient(production_app)

        self.assertEqual(client.get("/docs").status_code, 404)
        self.assertEqual(client.get("/redoc").status_code, 404)
        self.assertEqual(client.get("/openapi.json").status_code, 404)
