from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from glob import escape as escape_glob
from pathlib import Path
from threading import Lock, RLock

from PIL import Image, ImageOps


THUMBNAIL_DIR_NAME = "_thumbs"
THUMBNAIL_MAX_DIMENSION = 1200
THUMBNAIL_QUALITY = 72
THUMBNAIL_FILE_MODE = 0o644
THUMBNAIL_DIRECTORY_MODE = 0o755
THUMBNAIL_CACHE_VERSION = 2
GALLERY_THUMBNAIL_SOURCE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".webp"}
)
GALLERY_IMAGE_EXTENSIONS = GALLERY_THUMBNAIL_SOURCE_EXTENSIONS | {".gif"}

_THUMBNAIL_LOCK_COUNT = 32
_THUMBNAIL_LOCKS = tuple(Lock() for _ in range(_THUMBNAIL_LOCK_COUNT))
_THUMBNAIL_WARM_STATE_LOCK = Lock()
_THUMBNAIL_WARM_PENDING: set[tuple[Path, Path]] = set()
_THUMBNAIL_WARM_DRAINING = False
_GALLERY_SOURCE_MUTATION_LOCK = RLock()


@contextmanager
def gallery_thumbnail_source_mutation() -> Iterator[None]:
    """Serialize source mutation with thumbnail publication."""
    with _GALLERY_SOURCE_MUTATION_LOCK:
        yield


def get_gallery_thumbnail_path(upload_dir: Path, image_path: Path) -> Path:
    rel_path = image_path.relative_to(upload_dir)
    # Preserve the source extension in the cache name so sibling files such
    # as ``photo.jpg`` and ``photo.png`` cannot overwrite one another.
    thumbnail_name = f"{rel_path.name}.v{THUMBNAIL_CACHE_VERSION}.webp"
    return upload_dir / THUMBNAIL_DIR_NAME / rel_path.parent / thumbnail_name


def get_gallery_thumbnail_cache_paths(
    upload_dir: Path,
    image_path: Path,
) -> set[Path]:
    """Return current and historical cache paths owned by one source file."""
    rel_path = image_path.relative_to(upload_dir)
    cache_parent = upload_dir / THUMBNAIL_DIR_NAME / rel_path.parent
    paths = {
        cache_parent / f"{rel_path.name}.webp",
        cache_parent / rel_path.with_suffix(".webp").name,
        get_gallery_thumbnail_path(upload_dir, image_path),
    }
    if cache_parent.is_dir():
        paths.update(
            cache_parent.glob(f"{escape_glob(rel_path.name)}.v*.webp")
        )
    return paths


def _thumbnail_is_current(thumbnail_path: Path, image_path: Path) -> bool:
    try:
        return thumbnail_path.stat().st_mtime_ns >= image_path.stat().st_mtime_ns
    except FileNotFoundError:
        return False


def _ensure_thumbnail_permissions(thumbnail_path: Path) -> None:
    """Keep generated assets readable by a separate static-file server user."""
    current_mode = stat.S_IMODE(thumbnail_path.stat().st_mode)
    if current_mode != THUMBNAIL_FILE_MODE:
        os.chmod(thumbnail_path, THUMBNAIL_FILE_MODE)


def _ensure_thumbnail_directory_permissions(
    upload_dir: Path,
    thumbnail_path: Path,
) -> None:
    thumbnail_root = upload_dir / THUMBNAIL_DIR_NAME
    thumbnail_path.parent.relative_to(thumbnail_root)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

    current = thumbnail_path.parent
    while True:
        current_mode = stat.S_IMODE(current.stat().st_mode)
        if current_mode != THUMBNAIL_DIRECTORY_MODE:
            os.chmod(current, THUMBNAIL_DIRECTORY_MODE)
        if current == thumbnail_root:
            break
        current = current.parent


def get_current_gallery_thumbnail(
    upload_dir: Path,
    image_path: Path,
) -> Path | None:
    """Return a fresh, web-readable thumbnail without doing image work."""
    thumbnail_path = get_gallery_thumbnail_path(upload_dir, image_path)
    try:
        if not _thumbnail_is_current(thumbnail_path, image_path):
            return None
        _ensure_thumbnail_directory_permissions(upload_dir, thumbnail_path)
        _ensure_thumbnail_permissions(thumbnail_path)
        return thumbnail_path
    except OSError:
        return None


def get_gallery_thumbnail_cache_token(image_path: Path) -> str:
    """Version thumbnail URLs when the source image or cache schema changes."""
    source_stat = image_path.stat()
    return (
        f"{THUMBNAIL_CACHE_VERSION}-"
        f"{source_stat.st_mtime_ns:x}-{source_stat.st_size:x}"
    )


def _thumbnail_lock(thumbnail_path: Path) -> Lock:
    lock_index = hash(str(thumbnail_path.resolve())) % _THUMBNAIL_LOCK_COUNT
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


def _source_signature(image_path: Path) -> tuple[int, int, int, int]:
    source_stat = image_path.stat()
    return (
        source_stat.st_dev,
        source_stat.st_ino,
        source_stat.st_mtime_ns,
        source_stat.st_size,
    )


def _generate_gallery_thumbnail(
    upload_dir: Path,
    image_path: Path,
    thumbnail_path: Path,
) -> None:
    with gallery_thumbnail_source_mutation():
        source_signature = _source_signature(image_path)
        _ensure_thumbnail_directory_permissions(upload_dir, thumbnail_path)
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
            if _source_signature(image_path) != source_signature:
                raise OSError("Gallery source changed during thumbnail generation")
            # mkstemp intentionally creates 0600 files. Set the final public-
            # cache mode before the atomic replace so Nginx can read the asset
            # immediately without ever seeing a partially written file.
            os.chmod(temporary_path, THUMBNAIL_FILE_MODE)
            os.replace(temporary_path, thumbnail_path)
            if _source_signature(image_path) != source_signature:
                thumbnail_path.unlink(missing_ok=True)
                raise OSError("Gallery source changed during thumbnail publication")
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def ensure_gallery_thumbnail(upload_dir: Path, image_path: Path) -> Path | None:
    thumbnail_path = get_gallery_thumbnail_path(upload_dir, image_path)

    try:
        current_thumbnail = get_current_gallery_thumbnail(upload_dir, image_path)
        if current_thumbnail is not None:
            return current_thumbnail

        with _thumbnail_lock(thumbnail_path):
            # A concurrent request may have completed the same thumbnail while
            # this request waited for its bounded stripe lock.
            current_thumbnail = get_current_gallery_thumbnail(upload_dir, image_path)
            if current_thumbnail is not None:
                return current_thumbnail
            _generate_gallery_thumbnail(upload_dir, image_path, thumbnail_path)
        return thumbnail_path
    except Exception as exc:
        print(f"Error generating thumbnail for {image_path}: {exc}")
        return None


def warm_gallery_thumbnails(
    upload_dir: Path,
    image_paths: Iterable[Path],
) -> None:
    """Generate missing thumbnails after the Gallery response has been sent."""
    global _THUMBNAIL_WARM_DRAINING

    pending = {(upload_dir, image_path) for image_path in image_paths}
    if not pending:
        return

    with _THUMBNAIL_WARM_STATE_LOCK:
        _THUMBNAIL_WARM_PENDING.update(pending)
        if _THUMBNAIL_WARM_DRAINING:
            return
        _THUMBNAIL_WARM_DRAINING = True

    try:
        while True:
            with _THUMBNAIL_WARM_STATE_LOCK:
                if not _THUMBNAIL_WARM_PENDING:
                    _THUMBNAIL_WARM_DRAINING = False
                    return
                batch = tuple(_THUMBNAIL_WARM_PENDING)
                _THUMBNAIL_WARM_PENDING.clear()

            for pending_upload_dir, image_path in batch:
                ensure_gallery_thumbnail(pending_upload_dir, image_path)
    except BaseException:
        with _THUMBNAIL_WARM_STATE_LOCK:
            _THUMBNAIL_WARM_DRAINING = False
        raise
