import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app import assets


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"


class FrontendBuildTests(TestCase):
    def test_checked_in_frontend_assets_are_fresh(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/build_frontend.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_entries_match_asset_bytes(self) -> None:
        manifest = json.loads((STATIC_DIR / "asset-manifest.json").read_text(encoding="utf-8"))

        for required in (
            "css/styles.min.css",
            "fonts/fonts.css",
            "js/components/site-header.min.js",
            "js/effects/lightfield.min.js",
        ):
            self.assertIn(required, manifest)

        for relative_path, url in manifest.items():
            path = STATIC_DIR / relative_path
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            self.assertTrue(path.is_file(), relative_path)
            self.assertEqual(url, f"/static/{relative_path}?v={digest}")

    def test_precompressed_assets_are_reproducible_and_exact(self) -> None:
        compressed_assets = sorted(STATIC_DIR.rglob("*.gz"))
        self.assertTrue(compressed_assets)

        for compressed_path in compressed_assets:
            source_path = compressed_path.with_suffix("")
            compressed = compressed_path.read_bytes()
            self.assertTrue(source_path.is_file(), compressed_path)
            self.assertEqual(compressed[:4], b"\x1f\x8b\x08\x00")
            self.assertEqual(compressed[4:8], b"\x00\x00\x00\x00")
            self.assertEqual(compressed[9], 255)
            self.assertEqual(gzip.decompress(compressed), source_path.read_bytes())

    def test_font_styles_and_preloads_share_content_fingerprints(self) -> None:
        manifest = json.loads((STATIC_DIR / "asset-manifest.json").read_text(encoding="utf-8"))
        font_styles = (STATIC_DIR / "fonts" / "fonts.css").read_text(encoding="utf-8")
        templates = "".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "app" / "templates" / "base.html",
                ROOT / "app" / "templates" / "pages" / "home.html",
            )
        )

        for filename in (
            "source-sans-3-latin-v19.woff2",
            "source-serif-4-latin-v14.woff2",
            "dancing-script-latin-v29.woff2",
            "zhi-mang-xing-hyx-v19.woff2",
        ):
            fingerprinted_url = manifest[f"fonts/{filename}"]
            relative_url = fingerprinted_url.removeprefix("/static/fonts/")
            self.assertIn(f'url("./{relative_url}")', font_styles)
            self.assertIn(f"asset_url('fonts/{filename}')", templates)


class AssetUrlTests(TestCase):
    def tearDown(self) -> None:
        assets._asset_manifest.cache_clear()

    def test_asset_url_uses_manifest_and_has_an_encoded_fallback(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "asset-manifest.json"
            manifest_path.write_text(
                json.dumps({"css/app.css": "/static/css/app.css?v=abc123"}),
                encoding="utf-8",
            )
            with patch.object(assets, "ASSET_MANIFEST_PATH", manifest_path):
                assets._asset_manifest.cache_clear()
                self.assertEqual(
                    assets.asset_url("/static/css/app.css"),
                    "/static/css/app.css?v=abc123",
                )
                self.assertEqual(
                    assets.asset_url("images/a file.svg"),
                    "/static/images/a%20file.svg",
                )

    def test_invalid_manifest_fails_open_for_local_development(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "asset-manifest.json"
            manifest_path.write_text("not json", encoding="utf-8")
            with patch.object(assets, "ASSET_MANIFEST_PATH", manifest_path):
                assets._asset_manifest.cache_clear()
                self.assertEqual(
                    assets.asset_url("css/app.css"),
                    "/static/css/app.css",
                )
