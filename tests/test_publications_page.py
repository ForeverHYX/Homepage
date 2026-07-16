from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import markdown_utils
from app.cache import _cache
from app.main import app
from app.routers import pages


class PublicationsPageTests(TestCase):
    def test_structured_parser_preserves_publication_fields_and_badge_series(self) -> None:
        with TemporaryDirectory() as temp_dir:
            content_dir = Path(temp_dir)
            (content_dir / "content.md").write_text(
                """# Selected Publication

:::publication
type: conference
title: First GPU Paper
venue: Conference on Fast Machines (FAST26)
authors: A. Author, **Y. Hong**,
  and B. Author
keywords: GPU Modeling | Simulation
paper: https://example.com/paper.pdf
code: https://github.com/example/code
:::

:::publication
type: journal
title: Journal Follow-up
venue: Transactions on Architecture
authors: **Y. Hong**
tags: Architecture, AI
:::
""",
                encoding="utf-8",
            )

            _cache.clear()
            with patch.object(markdown_utils, "CONTENT_DIR", content_dir):
                publications = markdown_utils.get_publications()

        self.assertEqual(len(publications), 2)
        self.assertEqual(publications[0]["index_label"], "C1")
        self.assertEqual(publications[1]["index_label"], "T1")
        self.assertEqual(publications[0]["venue_label"], "FAST26")
        self.assertEqual(publications[0]["keywords"], ["GPU Modeling", "Simulation"])
        self.assertIn("and B. Author", publications[0]["authors"])
        self.assertEqual(publications[0]["slug"], "first-gpu-paper")
        self.assertIn('class="publication-link publication-link-paper"', publications[0]["html"])
        self.assertIn("<strong>Y. Hong</strong>", publications[1]["authors_html"])

    def test_publications_page_reuses_article_layout_and_filters_by_keyword(self) -> None:
        client = TestClient(app)
        response = client.get("/publications")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Publications | Yixun Hong", response.text)
        self.assertIn('class="article-grid publication-grid"', response.text)
        self.assertIn('class="card home-glass article-card publication-page-card"', response.text)
        self.assertIn("FlashGPU-sim: Enabling GPU Modeling", response.text)
        self.assertIn("Keywords", response.text)
        self.assertIn("GPU Modeling", response.text)

        filtered = client.get("/publications", params={"keywords": "GPU Modeling,Simulation"})
        self.assertEqual(filtered.status_code, 200)
        self.assertIn("FlashGPU-sim: Enabling GPU Modeling", filtered.text)
        self.assertIn("Filtered by:", filtered.text)
        self.assertIn("publication-keyword is-active", filtered.text)

        empty = client.get("/publications", params={"keywords": "Not Present"})
        self.assertEqual(empty.status_code, 200)
        self.assertIn("No publications found.", empty.text)

    def test_publication_filter_urls_toggle_encoded_multi_keywords(self) -> None:
        self.assertEqual(
            pages._publication_keywords_url(["GPU Modeling"], "AI Workloads"),
            "/publications?keywords=GPU%20Modeling%2CAI%20Workloads",
        )
        self.assertEqual(
            pages._publication_keywords_url(["GPU Modeling", "AI Workloads"], "GPU Modeling"),
            "/publications?keywords=AI%20Workloads",
        )
        self.assertEqual(pages._publication_keywords_url(["GPU Modeling"], "GPU Modeling"), "/publications")

    def test_publications_api_and_search_index_expose_publication_data(self) -> None:
        client = TestClient(app)
        response = client.get("/api/site/publications", params={"keyword": "GPU Modeling"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "public, max-age=60")
        payload = response.json()
        self.assertEqual(payload["filter_keywords"], ["GPU Modeling"])
        self.assertEqual(payload["publications"][0]["index_label"], "C1")

        search_payload = client.get("/api/search-index").json()
        publication = next(item for item in search_payload if item["type"] == "Publication")
        self.assertIn("FlashGPU-sim", publication["title"])
        self.assertTrue(publication["url"].startswith("/publications#"))

    def test_homepage_uses_selected_publication_heading_and_accent(self) -> None:
        response = TestClient(app).get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Selected Publication", response.text)
        self.assertIn("section-selected-publication", response.text)
        self.assertNotIn('class="section-title">Publications</h2>', response.text)
