"""Small, thread-safe caches for file-backed application content."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Hashable, TypeVar


T = TypeVar("T")
FileSignature = tuple[int, int] | None

CACHE_MAX_ENTRIES = 256

# ``_cache`` remains available for older tests and integrations that only call
# ``clear()`` on it. Application modules should use the helpers below so cache
# access stays synchronized and entries retain one consistent shape.
_cache: OrderedDict[tuple[str, Hashable], dict[str, Any]] = OrderedDict()
_cache_lock = RLock()


def file_signature(path: Path) -> FileSignature:
    """Return the inexpensive signature used to invalidate file-derived data."""
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return None
    return stat_result.st_mtime_ns, stat_result.st_size


def cache_by_signature(
    key: Hashable,
    signature: Hashable,
    loader: Callable[[], T],
    *,
    namespace: str = "default",
) -> T:
    """Return a cached value while ``signature`` remains unchanged.

    Loading occurs under a re-entrant lock. This deliberately favors a small,
    predictable cache over duplicate Markdown/JSON work when concurrent
    requests arrive immediately after a content change.
    """
    cache_key = (namespace, key)
    with _cache_lock:
        entry = _cache.get(cache_key)
        if entry is not None and entry["signature"] == signature:
            _cache.move_to_end(cache_key)
            return entry["value"]

        value = loader()
        _cache[cache_key] = {"signature": signature, "value": value}
        _cache.move_to_end(cache_key)
        while len(_cache) > CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)
        return value


def cache_by_mtime(
    path: Path,
    loader: Callable[[], T],
    *,
    namespace: str = "default",
) -> T:
    """Cache a loader result by resolved path, nanosecond mtime, and size.

    An explicit namespace lets one file safely back multiple derived values,
    such as parsed sections, rendered HTML, and structured publications.
    """
    resolved_path = path.resolve()
    return cache_by_signature(
        str(resolved_path),
        file_signature(resolved_path),
        loader,
        namespace=namespace,
    )


def invalidate_key(key: Hashable, *, namespace: str = "default") -> None:
    """Remove one logical cache entry."""
    with _cache_lock:
        _cache.pop((namespace, key), None)


def invalidate_namespace(namespace: str) -> None:
    """Remove every entry in one logical namespace."""
    with _cache_lock:
        matching_keys = [key for key in _cache if key[0] == namespace]
        for key in matching_keys:
            _cache.pop(key, None)


def invalidate(path: Path, *, namespace: str | None = None) -> None:
    """Invalidate one or every namespace associated with ``path``."""
    resolved_key = str(path.resolve())
    with _cache_lock:
        if namespace is not None:
            _cache.pop((namespace, resolved_key), None)
            return
        matching_keys = [key for key in _cache if key[1] == resolved_key]
        for key in matching_keys:
            _cache.pop(key, None)


def clear() -> None:
    """Clear every application content cache."""
    with _cache_lock:
        _cache.clear()
