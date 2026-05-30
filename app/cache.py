"""Simple mtime-based in-memory cache for file-backed content."""
from pathlib import Path
from typing import Any, Callable, Dict

_cache: Dict[str, dict] = {}


def cache_by_mtime(path: Path, loader: Callable[[], Any]) -> Any:
    """Return cached loader() result if file mtime has not changed."""
    if not path.exists():
        return loader()
    key = str(path.resolve())
    mtime = path.stat().st_mtime
    entry = _cache.get(key)
    if entry and entry["mtime"] == mtime:
        return entry["value"]
    value = loader()
    _cache[key] = {"mtime": mtime, "value": value}
    return value


def invalidate(path: Path) -> None:
    key = str(path.resolve())
    _cache.pop(key, None)


def clear() -> None:
    _cache.clear()
