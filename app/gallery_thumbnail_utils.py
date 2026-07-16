from __future__ import annotations

import os
import tempfile
from pathlib import Path
from threading import Lock

from PIL import Image, ImageOps


THUMBNAIL_DIR_NAME = "_thumbs"
THUMBNAIL_MAX_DIMENSION = 1200
THUMBNAIL_QUALITY = 72

_THUMBNAIL_LOCK_COUNT = 32
_THUMBNAIL_LOCKS = tuple(Lock() for _ in range(_THUMBNAIL_LOCK_COUNT))


def get_gallery_thumbnail_path(upload_dir: Path, image_path: Path) -> Path:
    rel_path = image_path.relative_to(upload_dir)
    return upload_dir / THUMBNAIL_DIR_NAME / rel_path.with_suffix(".webp")


def _thumbnail_is_current(thumbnail_path: Path, image_path: Path) -> bool:
    try:
        return thumbnail_path.stat().st_mtime_ns >= image_path.stat().st_mtime_ns
    except FileNotFoundError:
        return False


def _thumbnail_lock(thumbnail_path: Path) -> Lock:
    lock_index = hash(str(thumbnail_path.absolute())) % _THUMBNAIL_LOCK_COUNT
    return _THUMBNAIL_LOCKS[lock_index]


def _write_gallery_thumbnail(image_path: Path, temporary_path: Path) -> None:
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
            temporary_path,
            "WEBP",
            quality=THUMBNAIL_QUALITY,
            method=4,
        )


def _generate_gallery_thumbnail(image_path: Path, thumbnail_path: Path) -> None:
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=thumbnail_path.parent,
            prefix=f".{thumbnail_path.name}.",
            suffix=".tmp",
        )
        os.close(file_descriptor)
        temporary_path = Path(temporary_name)
        _write_gallery_thumbnail(image_path, temporary_path)
        os.replace(temporary_path, thumbnail_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def ensure_gallery_thumbnail(upload_dir: Path, image_path: Path) -> Path | None:
    thumbnail_path = get_gallery_thumbnail_path(upload_dir, image_path)

    try:
        if _thumbnail_is_current(thumbnail_path, image_path):
            return thumbnail_path

        with _thumbnail_lock(thumbnail_path):
            # A concurrent request may have completed the same thumbnail while
            # this request waited for its bounded stripe lock.
            if _thumbnail_is_current(thumbnail_path, image_path):
                return thumbnail_path
            _generate_gallery_thumbnail(image_path, thumbnail_path)
        return thumbnail_path
    except Exception as exc:
        print(f"Error generating thumbnail for {image_path}: {exc}")
        return None
