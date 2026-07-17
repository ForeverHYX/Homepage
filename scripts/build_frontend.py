"""Build deterministic, cache-safe frontend assets.

Readable CSS and the site-header controller live in small source modules.  The
browser still receives one CSS file and one header script, keeping the current
request profile while making the source tree maintainable.  Page-specific
scripts are minified beside their readable sources, and precompressed variants
let Nginx avoid doing repeat gzip work.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
from pathlib import Path

import rcssmin
import rjsmin
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
CSS_SOURCE_DIR = STATIC_DIR / "css" / "src"
CSS_BUNDLE = STATIC_DIR / "css" / "styles.css"
CSS_MINIFIED = STATIC_DIR / "css" / "styles.min.css"
HEADER_SOURCE_DIR = STATIC_DIR / "js" / "src" / "site-header"
HEADER_BUNDLE = STATIC_DIR / "js" / "components" / "site-header.js"
HEADER_MINIFIED = STATIC_DIR / "js" / "components" / "site-header.min.js"
ASSET_MANIFEST = STATIC_DIR / "asset-manifest.json"
FONT_VENDOR_DIR = ROOT / "assets" / "fonts" / "vendor"
FONT_STYLES_SOURCE = STATIC_DIR / "fonts" / "src" / "fonts.css"
FONT_STYLES = STATIC_DIR / "fonts" / "fonts.css"

HEADER_MODULE_ORDER = (
    "core.js",
    "anchored-popover.js",
    "navigation-search.js",
    "theme.js",
    "news-modal.js",
)

MANIFEST_EXCLUDED_SUFFIXES = frozenset({".gz", ".map"})
MANIFEST_EXCLUDED_NAMES = frozenset({"README.md", "asset-manifest.json"})

OPTIMIZED_VARIABLE_FONTS = {
    "source-sans-3-latin-v19.woff2": {"wght": (400, 600)},
    # The rendered prose ranges from 12px metadata to 28.8px headings. Keep a
    # small safety margin while dropping unused extreme display/text masters.
    "source-serif-4-latin-v14.woff2": {
        "wght": (400, 600),
        "opsz": (12, 32),
    },
}


def strip_css_comments(source: str) -> str:
    """Remove CSS comments without touching quoted content."""
    output: list[str] = []
    index = 0
    quote = ""
    while index < len(source):
        char = source[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(source):
                index += 1
                output.append(source[index])
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            output.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < len(source) and source[index + 1] == "*":
            end = source.find("*/", index + 2)
            if end < 0:
                raise ValueError("unterminated CSS comment")
            index = end + 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def minify_css(source: str) -> str:
    """Minify CSS with a parser-aware implementation."""
    return rcssmin.cssmin(source, keep_bang_comments=False).rstrip() + "\n"


def _source_files(directory: Path, pattern: str) -> list[Path]:
    files = sorted(directory.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no source files matched {directory / pattern}")
    return files


def build_css() -> None:
    sources = _source_files(CSS_SOURCE_DIR, "*.css")
    bundle = "".join(path.read_text(encoding="utf-8") for path in sources)
    CSS_BUNDLE.write_text(bundle, encoding="utf-8")
    CSS_MINIFIED.write_text(minify_css(bundle), encoding="utf-8")


def build_fonts() -> None:
    """Keep only the variable-font weight range used by the site."""
    output_dir = STATIC_DIR / "fonts"
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, axis_limits in OPTIMIZED_VARIABLE_FONTS.items():
        font = TTFont(FONT_VENDOR_DIR / filename, recalcTimestamp=False)
        instantiateVariableFont(font, axis_limits, inplace=True)
        font.flavor = "woff2"
        font.save(output_dir / filename)


def build_font_styles() -> None:
    """Fingerprint every font URL while preserving one readable CSS source."""
    source = FONT_STYLES_SOURCE.read_text(encoding="utf-8")

    def fingerprint(match: re.Match[str]) -> str:
        filename = match.group("filename")
        font_path = STATIC_DIR / "fonts" / filename
        digest = hashlib.sha256(font_path.read_bytes()).hexdigest()[:12]
        return f'url("./{filename}?v={digest}")'

    rendered = re.sub(
        r'url\("\./(?P<filename>[^"?]+\.woff2)"\)',
        fingerprint,
        source,
    )
    FONT_STYLES.write_text(rendered, encoding="utf-8")


def _classic_javascript(source: str) -> str:
    source = re.sub(r"^import .*?;\n", "", source, flags=re.MULTILINE)
    source = re.sub(r"^export (?=function )", "", source, flags=re.MULTILINE)
    return source


def build_site_header() -> None:
    modules = [
        _classic_javascript((HEADER_SOURCE_DIR / filename).read_text(encoding="utf-8"))
        for filename in HEADER_MODULE_ORDER
    ]
    entry = _classic_javascript((HEADER_SOURCE_DIR / "index.js").read_text(encoding="utf-8"))
    body = "\n".join([*modules, entry]).rstrip()
    bundle = (
        "/**\n"
        " * Generated by scripts/build_frontend.py from static/js/src/site-header/.\n"
        " * Edit the source modules, then rebuild; do not edit this file directly.\n"
        " */\n"
        "(function () {\n"
        '  "use strict";\n\n'
        f"{body}\n"
        "})();\n"
    )
    HEADER_BUNDLE.write_text(bundle, encoding="utf-8")
    HEADER_MINIFIED.write_text(rjsmin.jsmin(bundle).rstrip() + "\n", encoding="utf-8")


def build_javascript() -> None:
    build_site_header()
    for directory in (STATIC_DIR / "js" / "components", STATIC_DIR / "js" / "effects"):
        for source_path in sorted(directory.glob("*.js")):
            if source_path.name.endswith(".min.js"):
                continue
            target_path = source_path.with_name(f"{source_path.stem}.min.js")
            source = source_path.read_text(encoding="utf-8")
            target_path.write_text(rjsmin.jsmin(source).rstrip() + "\n", encoding="utf-8")


def _manifest_files() -> list[Path]:
    files: list[Path] = []
    for path in STATIC_DIR.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(STATIC_DIR)
        if (
            path == ASSET_MANIFEST
            or path.suffix in MANIFEST_EXCLUDED_SUFFIXES
            or path.name in MANIFEST_EXCLUDED_NAMES
            or "licenses" in relative.parts
        ):
            continue
        if "src" in relative.parts or path.name == ".DS_Store":
            continue
        files.append(path)
    return sorted(files)


def build_manifest() -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in _manifest_files():
        relative = path.relative_to(STATIC_DIR).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        manifest[relative] = f"/static/{relative}?v={digest}"
    ASSET_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _precompression_candidates() -> list[Path]:
    candidates = [
        CSS_MINIFIED,
        FONT_STYLES,
        *sorted(STATIC_DIR.glob("js/**/*.min.js")),
        *sorted(STATIC_DIR.glob("images/**/*.svg")),
    ]
    return [path for path in candidates if path.is_file()]


def build_precompressed_assets() -> None:
    owned = {path.with_name(f"{path.name}.gz") for path in _precompression_candidates()}
    for stale_path in STATIC_DIR.rglob("*.gz"):
        if stale_path not in owned:
            stale_path.unlink()
    candidates = _precompression_candidates()
    for path in candidates:
        compressed_path = path.with_name(f"{path.name}.gz")
        # ``gzip.compress(..., mtime=0)`` writes a platform-specific OS byte on
        # Python 3.11/3.12. GzipFile consistently writes 255, so Linux deploys
        # reproduce the exact bytes generated on macOS development machines.
        buffer = io.BytesIO()
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=buffer,
            mtime=0,
        ) as gzip_file:
            gzip_file.write(path.read_bytes())
        compressed_path.write_bytes(buffer.getvalue())


def _generated_paths() -> set[Path]:
    javascript = {
        source_path.with_name(f"{source_path.stem}.min.js")
        for directory in (
            STATIC_DIR / "js" / "components",
            STATIC_DIR / "js" / "effects",
        )
        for source_path in directory.glob("*.js")
        if not source_path.name.endswith(".min.js")
    }
    return {
        CSS_BUNDLE,
        CSS_MINIFIED,
        FONT_STYLES,
        HEADER_BUNDLE,
        HEADER_MINIFIED,
        ASSET_MANIFEST,
        *(STATIC_DIR / "fonts" / filename for filename in OPTIMIZED_VARIABLE_FONTS),
        *javascript,
        *(STATIC_DIR.rglob("*.gz")),
        *(path.with_name(f"{path.name}.gz") for path in _precompression_candidates()),
    }


def build_all() -> None:
    build_fonts()
    build_font_styles()
    build_css()
    build_javascript()
    build_manifest()
    build_precompressed_assets()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when rebuilding changes a tracked generated asset",
    )
    args = parser.parse_args()

    before = {path: path.read_bytes() if path.exists() else None for path in _generated_paths()}
    build_all()
    if args.check:
        all_paths = set(before) | _generated_paths()
        changed = [
            path
            for path in all_paths
            if before.get(path) != (path.read_bytes() if path.exists() else None)
        ]
        if changed:
            rendered = ", ".join(str(path.relative_to(ROOT)) for path in sorted(changed))
            raise SystemExit(f"generated frontend assets are stale: {rendered}")


if __name__ == "__main__":
    main()
