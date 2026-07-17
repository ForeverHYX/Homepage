import os
import stat
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import patch

from PIL import Image

from app import gallery_thumbnail_utils
from app.cache import clear
from app.routers import pages, upload
from app.services import gallery as gallery_service


ROOT = Path(__file__).resolve().parents[1]
GALLERY_VIEW_JS = ROOT / "static" / "js" / "components" / "gallery-view.js"
GALLERY_TEMPLATE = ROOT / "app" / "templates" / "pages" / "gallery.html"


class GalleryThumbnailTests(TestCase):
    def setUp(self) -> None:
        clear()

    def tearDown(self) -> None:
        clear()

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

            previous_umask = os.umask(0o077)
            try:
                with (
                    patch.object(
                        gallery_thumbnail_utils,
                        "_write_gallery_thumbnail",
                        side_effect=slow_writer,
                    ) as writer_mock,
                    ThreadPoolExecutor(max_workers=8) as executor,
                ):
                    results = list(
                        executor.map(
                            lambda _: gallery_thumbnail_utils.ensure_gallery_thumbnail(
                                upload_dir,
                                source,
                            ),
                            range(8),
                        )
                    )
            finally:
                os.umask(previous_umask)

            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.v2.webp"
            self.assertEqual(writer_mock.call_count, 1)
            self.assertTrue(all(result == thumbnail for result in results))
            self.assertTrue(thumbnail.exists())
            self.assertEqual(stat.S_IMODE(thumbnail.stat().st_mode), 0o644)
            for directory in (
                upload_dir / "_thumbs",
                upload_dir / "_thumbs" / "Graduation",
            ):
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
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

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(pages, "get_gallery_folders", return_value=["Graduation"]),
            ):
                payload = pages._build_gallery_payload()

            images = payload["albums"][0]["images"]
            full_images = payload["albums"][0]["full_images"]
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.v2.webp"
            self.assertEqual(len(images), 1)
            self.assertTrue(
                images[0].startswith("/uploads/_thumbs/Graduation/photo.webp.v2.webp?v=2-")
            )
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

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(pages, "get_gallery_folders", return_value=["Graduation"]),
            ):
                payload = pages._build_gallery_payload("Graduation")

            images = payload["albums"][0]["images"]
            full_images = payload["albums"][0]["full_images"]
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.v2.webp"
            self.assertEqual(images, ["/uploads/Graduation/photo.webp"])
            self.assertEqual(full_images, ["/uploads/Graduation/photo.webp"])
            self.assertFalse(thumbnail.exists())

    def test_gallery_payload_cache_reuses_and_invalidates_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            Image.new("RGB", (32, 32), "navy").save(
                album_dir / "photo.webp",
                "WEBP",
            )
            metadata = album_dir / "meta.json"
            metadata.write_text('{"title":"Before"}', encoding="utf-8")
            original_builder = gallery_service._build_payload

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(
                    pages,
                    "get_gallery_folders",
                    return_value=["Graduation"],
                ),
                patch.object(
                    gallery_service,
                    "_build_payload",
                    wraps=original_builder,
                ) as build_mock,
            ):
                first = pages._build_gallery_payload("Graduation")
                first["albums"][0]["title"] = "Mutated by caller"
                second = pages._build_gallery_payload("Graduation")

                metadata.write_text(
                    '{"title":"After an external edit"}',
                    encoding="utf-8",
                )
                third = pages._build_gallery_payload("Graduation")

            self.assertEqual(second["albums"][0]["title"], "Before")
            self.assertEqual(third["albums"][0]["title"], "After an external edit")
            self.assertEqual(build_mock.call_count, 2)

    def test_same_stem_different_extensions_get_distinct_thumbnails(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            Image.new("RGB", (1600, 1200), "red").save(album_dir / "photo.jpg", "JPEG")
            Image.new("RGB", (1600, 1200), "blue").save(album_dir / "photo.png", "PNG")

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(pages, "get_gallery_folders", return_value=["Graduation"]),
            ):
                payload = pages._build_gallery_payload()

            image_urls = payload["albums"][0]["images"]
            self.assertEqual(len(image_urls), 2)
            self.assertTrue(
                image_urls[0].startswith("/uploads/_thumbs/Graduation/photo.jpg.v2.webp?v=2-")
            )
            self.assertTrue(
                image_urls[1].startswith("/uploads/_thumbs/Graduation/photo.png.v2.webp?v=2-")
            )
            thumbnail_paths = [
                upload_dir / "_thumbs" / "Graduation" / "photo.jpg.v2.webp",
                upload_dir / "_thumbs" / "Graduation" / "photo.png.v2.webp",
            ]
            self.assertTrue(all(path.exists() for path in thumbnail_paths))
            self.assertNotEqual(
                thumbnail_paths[0].read_bytes(),
                thumbnail_paths[1].read_bytes(),
            )

    def test_gallery_urls_encode_reserved_file_and_folder_characters(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_name = "Trip ?#"
            album_dir = upload_dir / album_name
            album_dir.mkdir()
            source = album_dir / "photo ?# 01.webp"
            Image.new("RGB", (1600, 1200), "navy").save(source, "WEBP")

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(
                    pages,
                    "get_gallery_folders",
                    return_value=[album_name],
                ),
            ):
                payload = pages._build_gallery_payload()
                focused_payload = pages._build_gallery_payload(album_name)

            album = payload["albums"][0]
            self.assertTrue(
                album["images"][0].startswith(
                    "/uploads/_thumbs/Trip%20%3F%23/photo%20%3F%23%2001.webp.v2.webp?v=2-"
                )
            )
            original_url = "/uploads/Trip%20%3F%23/photo%20%3F%23%2001.webp"
            self.assertEqual(album["full_images"], [original_url])
            self.assertEqual(album["focus_url"], "/gallery?focus=Trip+%3F%23")
            self.assertEqual(
                focused_payload["albums"][0]["images"],
                [original_url],
            )

    def test_current_thumbnail_repairs_static_server_permissions(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (1600, 1200), "navy").save(source, "WEBP")

            thumbnail = gallery_thumbnail_utils.ensure_gallery_thumbnail(
                upload_dir,
                source,
            )
            self.assertIsNotNone(thumbnail)
            assert thumbnail is not None
            thumbnail.chmod(0o600)

            current = gallery_thumbnail_utils.get_current_gallery_thumbnail(
                upload_dir,
                source,
            )

            self.assertEqual(current, thumbnail)
            self.assertEqual(stat.S_IMODE(thumbnail.stat().st_mode), 0o644)

    def test_delete_cannot_republish_thumbnail_after_source_removal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (1600, 1200), "navy").save(source, "WEBP")
            original_writer = gallery_thumbnail_utils._write_gallery_thumbnail
            encoded = Event()
            allow_publish = Event()

            def paused_writer(image_path: Path, temporary_path: Path) -> None:
                original_writer(image_path, temporary_path)
                encoded.set()
                self.assertTrue(allow_publish.wait(timeout=2))

            with (
                patch.object(
                    gallery_thumbnail_utils,
                    "_write_gallery_thumbnail",
                    side_effect=paused_writer,
                ),
                patch.object(upload, "UPLOAD_DIR", upload_dir),
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                generation = executor.submit(
                    gallery_thumbnail_utils.ensure_gallery_thumbnail,
                    upload_dir,
                    source,
                )
                self.assertTrue(encoded.wait(timeout=2))
                deletion = executor.submit(
                    upload._delete_upload_item,
                    "Graduation/photo.webp",
                )
                time.sleep(0.03)
                self.assertFalse(deletion.done())
                allow_publish.set()
                generation.result(timeout=2)
                deletion.result(timeout=2)

            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.v2.webp"
            self.assertFalse(source.exists())
            self.assertFalse(thumbnail.exists())

    def test_gallery_falls_back_to_original_when_publish_chmod_fails(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (1600, 1200), "navy").save(source, "WEBP")

            with (
                patch.object(
                    gallery_thumbnail_utils.os,
                    "chmod",
                    side_effect=PermissionError("read-only cache"),
                ),
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(
                    pages,
                    "get_gallery_folders",
                    return_value=["Graduation"],
                ),
                patch("builtins.print") as print_mock,
            ):
                payload = pages._build_gallery_payload()

            self.assertEqual(
                payload["albums"][0]["images"],
                ["/uploads/Graduation/photo.webp"],
            )
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp.v2.webp"
            self.assertFalse(thumbnail.exists())
            print_mock.assert_called_once()
            self.assertEqual(
                list(thumbnail.parent.glob(f".{thumbnail.name}.*.tmp")),
                [],
            )

    def test_changed_source_is_not_published_under_stale_cache_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (1600, 1200), "navy").save(source, "WEBP")
            original_writer = gallery_thumbnail_utils._write_gallery_thumbnail

            def mutate_source(image_path: Path, temporary_path: Path) -> None:
                original_writer(image_path, temporary_path)
                Image.new("RGB", (800, 600), "cyan").save(image_path, "WEBP")

            with (
                patch.object(
                    gallery_thumbnail_utils,
                    "_write_gallery_thumbnail",
                    side_effect=mutate_source,
                ),
                patch("builtins.print") as print_mock,
            ):
                thumbnail = gallery_thumbnail_utils.ensure_gallery_thumbnail(
                    upload_dir,
                    source,
                )

            expected_path = upload_dir / "_thumbs" / "Graduation" / "photo.webp.v2.webp"
            self.assertIsNone(thumbnail)
            self.assertFalse(expected_path.exists())
            print_mock.assert_called_once()

    def test_gallery_defers_cold_thumbnail_generation_until_after_response(self) -> None:
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            album_dir = upload_dir / "Graduation"
            album_dir.mkdir()
            source = album_dir / "photo.webp"
            Image.new("RGB", (1600, 1200), "navy").save(source, "WEBP")
            pending: list[Path] = []

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(
                    pages,
                    "get_gallery_folders",
                    return_value=["Graduation"],
                ),
                patch.object(
                    pages,
                    "ensure_gallery_thumbnail",
                    side_effect=AssertionError("cold render must not encode"),
                ),
            ):
                cold_payload = pages._build_gallery_payload(
                    pending_thumbnails=pending,
                )

            self.assertEqual(pending, [source.resolve()])
            self.assertEqual(
                cold_payload["albums"][0]["images"],
                ["/uploads/Graduation/photo.webp"],
            )

            gallery_thumbnail_utils.warm_gallery_thumbnails(
                upload_dir.resolve(),
                pending,
            )
            next_pending: list[Path] = []
            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(
                    pages,
                    "get_gallery_folders",
                    return_value=["Graduation"],
                ),
            ):
                warm_payload = pages._build_gallery_payload(
                    pending_thumbnails=next_pending,
                )

            self.assertEqual(next_pending, [])
            self.assertTrue(
                warm_payload["albums"][0]["images"][0].startswith(
                    "/uploads/_thumbs/Graduation/photo.webp.v2.webp?v=2-"
                )
            )

    def test_overlapping_warm_batches_merge_without_blocking_callers(self) -> None:
        upload_dir = Path("/tmp/gallery-warm-test")
        first_image = upload_dir / "Album" / "first.webp"
        second_image = upload_dir / "Album" / "second.webp"
        first_started = Event()
        allow_first_to_finish = Event()
        generated: list[Path] = []

        def controlled_ensure(_upload_dir: Path, image_path: Path) -> Path:
            generated.append(image_path)
            if image_path == first_image:
                first_started.set()
                self.assertTrue(allow_first_to_finish.wait(timeout=2))
            return image_path

        with (
            patch.object(
                gallery_thumbnail_utils,
                "ensure_gallery_thumbnail",
                side_effect=controlled_ensure,
            ),
            ThreadPoolExecutor(max_workers=1) as executor,
        ):
            first_batch = executor.submit(
                gallery_thumbnail_utils.warm_gallery_thumbnails,
                upload_dir,
                [first_image],
            )
            self.assertTrue(first_started.wait(timeout=2))

            started_at = time.perf_counter()
            gallery_thumbnail_utils.warm_gallery_thumbnails(
                upload_dir,
                [second_image],
            )
            enqueue_duration = time.perf_counter() - started_at
            self.assertLess(enqueue_duration, 0.1)

            allow_first_to_finish.set()
            first_batch.result(timeout=2)

        self.assertEqual(set(generated), {first_image, second_image})

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

            with (
                patch.object(pages, "UPLOAD_DIR", upload_dir),
                patch.object(pages, "get_gallery_folders", return_value=["Graduation"]),
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
                (upload_dir / "_thumbs" / "Graduation" / "animation.gif.v2.webp").exists()
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
        self.assertIn("asset_url('js/components/gallery-view.min.js')", template)
        self.assertIn('data-src="{{ album.full_images[loop.index0]', template)
