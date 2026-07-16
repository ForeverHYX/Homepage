import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient

from app.main import app
from app.routers import pages


ROOT = Path(__file__).resolve().parents[1]


class SeoRoutesTests(TestCase):
    def test_robots_txt_allows_crawling_and_points_to_sitemap(self) -> None:
        response = TestClient(app).get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertIn("User-agent: *", response.text)
        self.assertIn("Allow: /", response.text)
        self.assertIn("Sitemap: https://foreverhyx.top/sitemap.xml", response.text)


    def test_sitemap_xml_lists_public_canonical_pages(self) -> None:
        response = TestClient(app).get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/xml"))
        self.assertIn("<urlset", response.text)
        for url in [
            "https://foreverhyx.top/",
            "https://foreverhyx.top/publications",
            "https://foreverhyx.top/daily",
            "https://foreverhyx.top/gallery",
            "https://foreverhyx.top/resume",
        ]:
            self.assertIn(f"<loc>{url}</loc>", response.text)

    def test_indexnow_key_file_is_publicly_verifiable(self) -> None:
        indexnow_key = getattr(pages, "INDEXNOW_KEY", "")

        self.assertRegex(indexnow_key, r"^[0-9a-f]{32}$")
        response = TestClient(app).get(f"/{indexnow_key}.txt")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/plain"))
        self.assertEqual(response.text.strip(), indexnow_key)

    def test_indexnow_submitter_builds_payload_from_sitemap_urls(self) -> None:
        script_path = ROOT / "scripts" / "indexnow_submit.py"
        self.assertTrue(script_path.exists())

        spec = importlib.util.spec_from_file_location("indexnow_submit", script_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        sitemap_response = TestClient(app).get("/sitemap.xml")
        urls = module.parse_sitemap_urls(sitemap_response.text)
        payload = module.build_payload(urls)

        self.assertEqual(payload["host"], "foreverhyx.top")
        self.assertEqual(payload["key"], pages.INDEXNOW_KEY)
        self.assertEqual(
            payload["keyLocation"],
            f"https://foreverhyx.top/{pages.INDEXNOW_KEY}.txt",
        )
        self.assertEqual(payload["urlList"], urls)
        self.assertIn("https://foreverhyx.top/", urls)

    def test_indexnow_submitter_runs_as_direct_script(self) -> None:
        script_path = ROOT / "scripts" / "indexnow_submit.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Submit foreverhyx.top URLs to IndexNow.", result.stdout)
