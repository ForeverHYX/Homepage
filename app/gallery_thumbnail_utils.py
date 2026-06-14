from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

THUMBNAIL_DIR_NAME = "_thumbs"
THUMBNAIL_MAX_DIMENSION = 1200
THUMBNAIL_QUALITY = 72


def get_gallery_thumbnail_path(upload_dir: Path, image_path: Path) -> Path:
    rel_path = image_path.relative_to(upload_dir)
    return upload_dir / THUMBNAIL_DIR_NAME / rel_path.with_suffix(".webp")


def ensure_gallery_thumbnail(upload_dir: Path, image_path: Path) -> Path | None:
    thumbnail_path = get_gallery_thumbnail_path(upload_dir, image_path)

    try:
        if (
            thumbnail_path.exists()
            and thumbnail_path.stat().st_mtime >= image_path.stat().st_mtime
        ):
            return thumbnail_path

        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = thumbnail_path.with_name(f".{thumbnail_path.name}.tmp")

        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(
                (THUMBNAIL_MAX_DIMENSION, THUMBNAIL_MAX_DIMENSION),
                Image.Resampling.LANCZOS,
            )

            has_alpha = "A" in image.getbands()
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if has_alpha else "RGB")

            image.save(
                temp_path,
                "WEBP",
                quality=THUMBNAIL_QUALITY,
                method=4,
            )

        temp_path.replace(thumbnail_path)
        return thumbnail_path
    except Exception as exc:
        print(f"Error generating thumbnail for {image_path}: {exc}")
        try:
            temp_path.unlink(missing_ok=True)
        except UnboundLocalError:
            pass
        return None
