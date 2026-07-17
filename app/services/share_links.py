"""Persistent, unguessable public links for files managed by the upload UI."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from threading import RLock

from app.config import SHARE_LINK_FILE


_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_LOCK = RLock()
_CACHE_SIGNATURE: tuple[str, int, int] | None = None
_CACHE_LINKS: dict[str, dict[str, object]] = {}


def _file_signature(path: Path) -> tuple[str, int, int] | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return str(path.resolve()), stat_result.st_mtime_ns, stat_result.st_size


def _load_links() -> dict[str, dict[str, object]]:
    global _CACHE_LINKS, _CACHE_SIGNATURE

    signature = _file_signature(SHARE_LINK_FILE)
    if signature == _CACHE_SIGNATURE:
        return {token: dict(entry) for token, entry in _CACHE_LINKS.items()}
    if signature is None:
        _CACHE_SIGNATURE = None
        _CACHE_LINKS = {}
        return {}

    try:
        payload = json.loads(SHARE_LINK_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}

    raw_links = payload.get("links", {}) if isinstance(payload, dict) else {}
    links: dict[str, dict[str, object]] = {}
    if isinstance(raw_links, dict):
        for token, entry in raw_links.items():
            if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
                continue
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                continue
            links[token] = {
                "path": entry["path"],
                "created_at": entry.get("created_at", 0),
            }

    _CACHE_SIGNATURE = signature
    _CACHE_LINKS = links
    return {token: dict(entry) for token, entry in links.items()}


def _save_links(links: dict[str, dict[str, object]]) -> None:
    global _CACHE_LINKS, _CACHE_SIGNATURE

    SHARE_LINK_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SHARE_LINK_FILE.parent,
            prefix=f".{SHARE_LINK_FILE.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(
                {"version": 1, "links": links},
                temporary_file,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, SHARE_LINK_FILE)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass

    _CACHE_LINKS = {token: dict(entry) for token, entry in links.items()}
    _CACHE_SIGNATURE = _file_signature(SHARE_LINK_FILE)


def get_or_create_share_token(relative_path: str) -> str:
    """Return a stable token for a file, creating one atomically if needed."""

    with _LOCK:
        links = _load_links()
        for token, entry in links.items():
            if entry.get("path") == relative_path:
                return token

        token = secrets.token_urlsafe(32)
        while token in links:
            token = secrets.token_urlsafe(32)
        links[token] = {"path": relative_path, "created_at": int(time.time())}
        _save_links(links)
        return token


def resolve_share_token(token: str) -> str | None:
    if not _TOKEN_PATTERN.fullmatch(token):
        return None
    with _LOCK:
        entry = _load_links().get(token)
        path = entry.get("path") if entry else None
        return path if isinstance(path, str) else None


def move_share_links(source_path: str, destination_path: str) -> None:
    """Keep existing public links working after a managed rename or move."""

    prefix = f"{source_path}/"
    with _LOCK:
        links = _load_links()
        changed = False
        for entry in links.values():
            path = entry.get("path")
            if path == source_path:
                entry["path"] = destination_path
                changed = True
            elif isinstance(path, str) and path.startswith(prefix):
                entry["path"] = f"{destination_path}/{path[len(prefix) :]}"
                changed = True
        if changed:
            _save_links(links)


def remove_share_links(path: str) -> None:
    """Forget links for one file or every file below a deleted directory."""

    prefix = f"{path}/"
    with _LOCK:
        links = _load_links()
        retained = {
            token: entry
            for token, entry in links.items()
            if entry.get("path") != path
            and not (isinstance(entry.get("path"), str) and str(entry["path"]).startswith(prefix))
        }
        if len(retained) != len(links):
            _save_links(retained)
