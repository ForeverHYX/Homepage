from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PIL import Image

from app.routers import pages


class GalleryThumbnailTests(TestCase):
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
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp"
            self.assertEqual(images, ["/uploads/_thumbs/Graduation/photo.webp"])
            self.assertEqual(full_images, ["/uploads/Graduation/photo.webp"])
            self.assertTrue(thumbnail.exists())

            with Image.open(thumbnail) as img:
                self.assertLessEqual(max(img.size), 1200)

    def test_focused_gallery_uses_original_images(self) -> None:
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
            thumbnail = upload_dir / "_thumbs" / "Graduation" / "photo.webp"
            self.assertEqual(images, ["/uploads/Graduation/photo.webp"])
            self.assertEqual(full_images, ["/uploads/Graduation/photo.webp"])
            self.assertFalse(thumbnail.exists())
