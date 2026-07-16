import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PIL import Image

from app import gallery_thumbnail_utils
from app.routers import pages


ROOT = Path(__file__).resolve().parents[1]
GALLERY_VIEW_JS = ROOT / "static" / "js" / "components" / "gallery-view.js"
GALLERY_TEMPLATE = ROOT / "app" / "templates" / "pages" / "gallery.html"


class GalleryThumbnailTests(TestCase):
    def test_concurrent_first_requests_generate_one_atomic_thumbnail(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (2400, 1600), "navy").save(source, "WEBP")
            original_writer = gallery_thumbnail_utils._write_gallery_thumbnail

            def slow_writer(image_path: Path, temporary_path: Path) -> None:
                time.sleep(0.03)
                original_writer(image_path, temporary_path)

            with patch.object(
                gallery_thumbnail_utils,
                "_write_gallery_thumbnail",
                side_effect=slow_writer,
            ) as writer_mock, ThreadPoolExecutor(max_workers=8) as executor:
                results = list(
                    executor.map(
                        lambda _: gallery_thumbnail_utils.ensure_gallery_thumbnail(
                            upload_dir,
                            source,
                        ),
                        range(8),
                    )
                )

            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.webp"
            self.assertEqual(writer_mock.call_count, 1)
            self.assertTrue(all(result == thumbnail for result in results))
            self.assertTrue(thumbnail.exists())
            self.assertEqual(
                list(thumbnail.parent.glob(f".{thumbnail.name}.*.tmp")),
                [],
            )
            with Image.open(thumbnail) as image:
                image.verify()

    def test_unfocused_gallery_uses_generated_thumbnails(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (2400, 1600), "navy").save(source, "WEBP")

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                pages, "get_gallery_folders", return_value=["Graduation"]
            ):
                payload = pages._build_gallery_payload()

            images = payload["albums"][0]["images"]
            full_images = payload["albums"][0]["full_images"]
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.webp"
            self.assertEqual(images, ["/uploads/_thumbs/Graduation/photo.webp.webp"])
            self.assertEqual(full_images, ["/uploads/Graduation/photo.webp"])
            self.assertTrue(thumbnail.exists())

            with Image.open(thumbnail) as img:
                self.assertLessEqual(max(img.size), 1200)

    def test_focused_gallery_preserves_original_image_quality(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (2400, 1600), "navy").save(source, "WEBP")

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                pages, "get_gallery_folders", return_value=["Graduation"]
            ):
                payload = pages._build_gallery_payload("Graduation")

            images = payload["albums"][0]["images"]
            full_images = payload["albums"][0]["full_images"]
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.webp"
            self.assertEqual(images, ["/uploads/Graduation/photo.webp"])
            self.assertEqual(full_images, ["/uploads/Graduation/photo.webp"])
            self.assertFalse(thumbnail.exists())

    def test_same_stem_different_extensions_get_distinct_thumbnails(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            Image.new("RGB", (1600, 1200), "red").save(album_dir / "photo.jpg", "JPEG")
            Image.new("RGB", (1600, 1200), "blue").save(album_dir / "photo.png", "PNG")

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                pages, "get_gallery_folders", return_value=["Graduation"]
            ):
                payload = pages._build_gallery_payload()

            expected_urls = [
                "/uploads/_thumbs/Graduation/photo.jpg.webp",
                "/uploads/_thumbs/Graduation/photo.png.webp",
            ]
            self.assertEqual(payload["albums"][0]["images"], expected_urls)
            thumbnail_paths = [
                upload_dir / "_thumbs" / "Graduation" / "photo.jpg.webp",
                upload_dir / "_thumbs" / "Graduation" / "photo.png.webp",
            ]
            self.assertTrue(all(path.exists() for path in thumbnail_paths))
            self.assertNotEqual(
                thumbnail_paths[0].read_bytes(),
                thumbnail_paths[1].read_bytes(),
            )

    def test_animated_gif_keeps_original_in_focused_and_album_views(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "animation.gif"
            first_frame = Image.new("RGB", (40, 40), "navy")
            second_frame = Image.new("RGB", (40, 40), "cyan")
            first_frame.save(
                source,
                "GIF",
                save_all=True,
                append_images=[second_frame],
                duration=80,
                loop=0,
            )

            with patch.object(pages, "UPLOAD_DIR", upload_dir), patch.object(
                pages, "get_gallery_folders", return_value=["Graduation"]
            ):
                album_payload = pages._build_gallery_payload()
                focused_payload = pages._build_gallery_payload("Graduation")

            original_url = "/uploads/Graduation/animation.gif"
            self.assertEqual(album_payload["albums"][0]["images"], [original_url])
            self.assertEqual(focused_payload["albums"][0]["images"], [original_url])
            self.assertEqual(
                album_payload["albums"][0]["full_images"],
                [original_url],
            )
            self.assertFalse(
                (upload_dir / "_thumbs" / "Graduation" / "animation.gif.webp").exists()
            )

    def test_gallery_autoscroll_has_one_visibility_aware_scheduler(self) -> None:
        source = GALLERY_VIEW_JS.read_text(encoding="utf-8")
        template = GALLERY_TEMPLATE.read_text(encoding="utf-8")

        self.assertNotIn("setInterval", source)
        self.assertIn("window.performance.now()", source)
        self.assertIn("new IntersectionObserver", source)
        self.assertIn('document.addEventListener("visibilitychange", updateScheduler)', source)
        self.assertIn("state.visible && !state.paused && hasOverflow(state)", source)
        self.assertIn(
            "state.container.scrollWidth > state.container.clientWidth + 4",
            source,
        )
        self.assertIn('window.addEventListener("pagehide", stopScheduler)', source)
        self.assertIn('window.addEventListener("pageshow", updateScheduler)', source)
        self.assertIn("preview.currentSrc || preview.src", source)
        self.assertIn("new window.Image()", source)
        self.assertIn("loadToken !== fullImageLoadToken", source)
        self.assertIn('img.removeAttribute("src")', source)
        self.assertIn('src="/static/js/components/gallery-view.js?v=99"', template)
        self.assertIn('data-src="{{ album.full_images[loop.index0]', template)
