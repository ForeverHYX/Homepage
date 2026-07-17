"""Backward-compatible entry point for the unified frontend builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_BUILDER_PATH = Path(__file__).with_name("build_frontend.py")
_SPEC = importlib.util.spec_from_file_location("homepage_build_frontend", _BUILDER_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load frontend builder from {_BUILDER_PATH}")
_BUILDER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BUILDER)

build_css = _BUILDER.build_css
minify_css = _BUILDER.minify_css
strip_css_comments = _BUILDER.strip_css_comments


def main() -> None:
    build_css()


if __name__ == "__main__":
    main()
