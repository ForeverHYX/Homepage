import unittest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.daily import build_daily_payload, daily_payload_search_entries, daily_search_entries, fetch_daily_favorites_archive, load_daily_payload
from app.daily_articles import daily_article_slug, ensure_daily_article_markdown, generate_daily_article_markdown
from app.routers import pages


SAMPLE_RECOMMENDER_PAYLOAD = {
    "run_date": "2026-06-14",
    "section_labels": {
        "agentic_architecture": "Agentic Architecture",
        "microarchitecture_simulators": "Microarchitecture and Simulators",
    },
    "recommendations": [
        {
            "rank": 1,
            "paper_id": "2606.00001",
            "title": "Agentic AI-Driven Microarchitecture Exploration",
            "abstract": "LLM agents explore cache replacement and data prefetchers with gem5.",
            "authors": ["A. Architect", "B. Builder", "C. Compiler", "D. Designer", "E. Evaluator"],
            "affiliations": ["Hidden Lab"],
            "categories": ["cs.AR"],
            "sections": ["agentic_architecture", "microarchitecture_simulators"],
            "positive_matches": [
                "agentic_architecture:hardware design agent",
                "microarchitecture_simulators:gem5",
            ],
            "tldr": "This paper builds an agent-guided loop for microarchitecture design exploration.",
            "url": "https://arxiv.org/abs/2606.00001",
            "pdf_url": "https://arxiv.org/pdf/2606.00001",
            "code_urls": ["https://github.com/example/agentic-arch"],
        }
    ],
}


def sample_daily_page_payload():
    return build_daily_payload(
        {
            "run_date": "2026-06-14",
            "recommendations": [
                SAMPLE_RECOMMENDER_PAYLOAD["recommendations"][0],
                {
                    "rank": 2,
                    "item_type": "repository",
                    "repository_full_name": "example/runtime-cache",
                    "title": "example/runtime-cache",
                    "abstract": "Runtime cache for LLM serving.",
                    "authors": ["Repo Owner"],
                    "repository_url": "https://github.com/example/runtime-cache",
                    "repository_topics": ["runtime", "llm", "inference"],
                    "categories": ["github", "Python", "runtime", "llm", "inference"],
                    "repository_language": "Python",
                    "sections": [],
                },
            ],
        },
        feedback_config={
            "supabase_url": "https://example.supabase.co",
            "supabase_anon_key": "anon-key",
        },
    )


class DailyIntegrationTests(unittest.TestCase):
    def test_daily_page_hides_feedback_controls_when_upload_session_is_absent(self):
        with patch.object(pages, "_build_daily_payload", return_value=sample_daily_page_payload()):
            response = TestClient(app).get("/daily")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("PDF", html)
        self.assertIn("Code", html)
        self.assertNotIn('id="dailyFeedbackConfig"', html)
        self.assertNotIn("data-feedback-payload", html)
        self.assertNotIn("daily-feedback-button", html)
        self.assertNotIn('data-feedback-rating="like"', html)
        self.assertNotIn('data-feedback-rating="dislike"', html)
        self.assertNotIn(">Like<", html)
        self.assertNotIn(">Dislike<", html)

    def test_daily_page_titles_link_to_generated_article_pages(self):
        payload = sample_daily_page_payload()
        with patch.object(pages, "_build_daily_payload", return_value=payload):
            response = TestClient(app).get("/daily")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('href="/daily/articles/2026-06-14-2606-00001"', html)
        self.assertIn('href="/daily/articles/2026-06-14-repo-example-runtime-cache"', html)
        self.assertNotIn('<a href="https://arxiv.org/abs/2606.00001" target="_blank" rel="noreferrer">Agentic AI-Driven Microarchitecture Exploration</a>', html)
        self.assertNotIn('<a href="https://github.com/example/runtime-cache" target="_blank" rel="noreferrer">example/runtime-cache</a>', html)

    def test_daily_page_shows_feedback_controls_when_upload_session_is_active(self):
        with patch.object(pages, "_build_daily_payload", return_value=sample_daily_page_payload()):
            with patch("app.routers.pages.get_current_user", return_value=True, create=True):
                response = TestClient(app).get("/daily")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="dailyFeedbackConfig"', html)
        self.assertIn("data-feedback-payload", html)
        self.assertIn("daily-feedback-button", html)
        self.assertIn('data-feedback-rating="like"', html)
        self.assertIn('data-feedback-rating="dislike"', html)
        self.assertIn(">Like<", html)
        self.assertIn(">Dislike<", html)

    def test_daily_page_filter_links_preserve_selected_archive_date(self):
        payload = sample_daily_page_payload()
        payload["run_date"] = "2026-06-13"
        payload["selected_date"] = "2026-06-13"
        payload["current_run_date"] = "2026-06-14"
        payload["archive_dates"] = ["2026-06-13"]

        with patch.object(pages, "_build_daily_payload", return_value=payload):
            response = TestClient(app).get("/daily?date=2026-06-13")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('href="/daily?date=2026-06-13&amp;keywords=Agent"', html)
        self.assertIn('href="/daily?date=2026-06-13&amp;item_type=repository"', html)
        self.assertIn('href="/daily?date=2026-06-13&amp;item_type=paper"', html)

    def test_daily_archive_page_passes_current_run_date_to_calendar(self):
        payload = sample_daily_page_payload()
        payload["run_date"] = "2026-06-15"
        payload["selected_date"] = "2026-06-15"
        payload["current_run_date"] = "2026-06-16"
        payload["archive_dates"] = ["2026-06-15"]

        with patch.object(pages, "_build_daily_payload", return_value=payload):
            response = TestClient(app).get("/daily?date=2026-06-15")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('data-run-date="2026-06-15"', html)
        self.assertIn('data-current-run-date="2026-06-16"', html)

    def test_daily_api_hides_feedback_config_without_upload_session(self):
        with patch.object(pages, "_build_daily_payload", return_value=sample_daily_page_payload()):
            response = TestClient(app).get("/api/site/daily")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["feedback_config"], {})
        self.assertEqual(response.headers["cache-control"], "private, max-age=60")

    def test_daily_api_exposes_feedback_config_with_upload_session(self):
        with patch.object(pages, "_build_daily_payload", return_value=sample_daily_page_payload()):
            with patch("app.routers.pages.get_current_user", return_value=True, create=True):
                response = TestClient(app).get("/api/site/daily")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["feedback_config"]["supabase_url"], "https://example.supabase.co")
        self.assertEqual(response.headers["cache-control"], "private, max-age=60")

    def test_daily_payload_exposes_author_and_ai_keywords_without_affiliations(self):
        payload = build_daily_payload(SAMPLE_RECOMMENDER_PAYLOAD)

        item = payload["items"][0]
        self.assertEqual(item["authors"], ["A. Architect", "B. Builder", "C. Compiler", "D. Designer", "E. Evaluator"])
        self.assertEqual(item["display_authors"], ["A. Architect", "B. Builder", "C. Compiler", "D. Designer"])
        self.assertNotIn("...", ", ".join(item["display_authors"]))
        self.assertNotIn("…", ", ".join(item["display_authors"]))
        self.assertIn("Agent", item["keywords"])
        self.assertIn("Hardware", item["keywords"])
        self.assertIn("Gem5", item["keywords"])
        self.assertNotIn("hardware design agent", item["keywords"])
        self.assertNotIn("cs.AR", item["keywords"])
        for keyword in item["keywords"]:
            self.assertRegex(keyword, r"^[A-Z][A-Za-z0-9]*$")
        self.assertNotIn("affiliations", item)
        self.assertEqual(item["feedback_payload"]["source"], "page")
        self.assertIn("affiliations", item["feedback_payload"])
        self.assertIn("item_type", item["feedback_payload"])
        self.assertIn("paper_links", item["feedback_payload"])
        self.assertIn(("Agent", 1), payload["sorted_keywords"])
        self.assertEqual(item["detail_url"], "/daily/articles/2026-06-14-2606-00001")

    def test_daily_search_entries_include_title_and_keywords(self):
        entries = daily_search_entries(SAMPLE_RECOMMENDER_PAYLOAD)

        self.assertEqual(entries[0]["type"], "Daily")
        self.assertEqual(entries[0]["title"], "Agentic AI-Driven Microarchitecture Exploration")
        self.assertIn("Agent", entries[0]["tags"])
        self.assertIn("Gem5", entries[0]["tags"])
        self.assertNotIn("cs.AR", entries[0]["tags"])
        self.assertEqual(entries[0]["url"], "/daily/articles/2026-06-14-2606-00001")

    def test_daily_article_slug_is_stable_for_papers_and_repositories(self):
        paper = build_daily_payload(SAMPLE_RECOMMENDER_PAYLOAD)["items"][0]
        repo = sample_daily_page_payload()["items"][1]

        self.assertEqual(daily_article_slug(paper, "2026-06-14"), "2026-06-14-2606-00001")
        self.assertEqual(daily_article_slug(repo, "2026-06-14"), "2026-06-14-repo-example-runtime-cache")

    def test_daily_article_markdown_uses_blog_frontmatter_and_readable_sections(self):
        item = build_daily_payload(SAMPLE_RECOMMENDER_PAYLOAD)["items"][0]

        markdown = generate_daily_article_markdown(item, "2026-06-14")

        self.assertIn("# Agentic AI-Driven Microarchitecture Exploration", markdown)
        self.assertIn("Date: 2026-06-14", markdown)
        self.assertIn("Author: Yixun Hong", markdown)
        self.assertIn("Tags: Daily, Paper", markdown)
        self.assertIn("Daily-Article-Version: 2", markdown)
        self.assertIn("Abstract:", markdown)
        self.assertIn("## Core Idea", markdown)
        self.assertIn("## What Is New", markdown)
        self.assertIn("## Methodology", markdown)
        self.assertIn("Read this as a loop:", markdown)
        self.assertNotIn("The daily payload describes the method as:", markdown)
        self.assertIn("## Figure To Read First", markdown)
        self.assertIn("![Paper PDF with figures](https://arxiv.org/pdf/2606.00001.pdf)", markdown)
        self.assertIn("## Minimal Mental Model", markdown)
        self.assertIn("```text", markdown)
        self.assertIn("## Why It Matters", markdown)

    def test_daily_article_cache_regenerates_old_generator_output(self):
        item = build_daily_payload(SAMPLE_RECOMMENDER_PAYLOAD)["items"][0]

        with tempfile.TemporaryDirectory() as tmpdir:
            article_dir = Path(tmpdir)
            slug = daily_article_slug(item, "2026-06-14")
            path = article_dir / f"{slug}.md"
            article_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Old Daily Article\n\n## Core Idea\n\nold cached output\n",
                encoding="utf-8",
            )

            generated_path = ensure_daily_article_markdown(item, "2026-06-14", output_dir=article_dir)
            markdown = generated_path.read_text(encoding="utf-8")

        self.assertEqual(generated_path, path)
        self.assertIn("# Agentic AI-Driven Microarchitecture Exploration", markdown)
        self.assertIn("Daily-Article-Version: 2", markdown)
        self.assertNotIn("old cached output", markdown)

    def test_daily_article_route_renders_generated_markdown_with_article_template(self):
        payload = sample_daily_page_payload()
        with tempfile.TemporaryDirectory() as tmpdir:
            article_dir = Path(tmpdir)
            slug = payload["items"][0]["article_slug"]
            with patch.object(pages, "_build_daily_payload", return_value=payload):
                with patch("app.routers.pages.DAILY_ARTICLES_DIR", article_dir):
                    response = TestClient(app).get(f"/daily/articles/{slug}")

            markdown_path = article_dir / f"{slug}.md"
            markdown_exists = markdown_path.exists()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(markdown_exists)
        html = response.text
        self.assertIn("Table of Contents", html)
        self.assertIn("Core Idea", html)
        self.assertIn("What Is New", html)
        self.assertIn("Methodology", html)
        self.assertIn("Figure To Read First", html)
        self.assertIn("Back to Daily", html)

    def test_daily_article_route_rejects_unknown_slug(self):
        with patch.object(pages, "_build_daily_payload", return_value=sample_daily_page_payload()):
            response = TestClient(app).get("/daily/articles/unknown")

        self.assertEqual(response.status_code, 404)

    def test_daily_search_entries_can_be_built_from_cached_daily_payload(self):
        payload = build_daily_payload(SAMPLE_RECOMMENDER_PAYLOAD)

        entries = daily_payload_search_entries(payload)

        self.assertEqual(entries[0]["type"], "Daily")
        self.assertEqual(entries[0]["title"], "Agentic AI-Driven Microarchitecture Exploration")
        self.assertIn("Agent", entries[0]["tags"])

    def test_daily_keywords_fallback_to_english_title_terms_without_arxiv_tags(self):
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "paper_id": "2606.00003",
                    "title": "Arbor: Tree Search as a Cognition Layer for Autonomous Agents",
                    "abstract": "Autonomous agents use tree search and cognition layers.",
                    "authors": ["A. Author"],
                    "categories": ["cs.AI", "cs.LG"],
                    "sections": ["exploratory"],
                    "url": "https://arxiv.org/abs/2606.00003",
                }
            ],
        })

        keywords = payload["items"][0]["keywords"]
        self.assertIn("Search", keywords)
        self.assertIn("Agents", keywords)
        self.assertNotIn("Arbor", keywords)
        self.assertNotIn("cs.AI", keywords)
        self.assertNotIn("cs.LG", keywords)
        for keyword in keywords:
            self.assertRegex(keyword, r"^[A-Z][A-Za-z0-9]*$")

    def test_daily_sidebar_keywords_are_packed_before_lower_fit_rows(self):
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "paper_id": "2606.10001",
                    "title": "Paper One",
                    "abstract": "GPU cache search.",
                    "authors": ["A. Author"],
                    "positive_matches": ["microarchitecture_simulators:microarchitecture", "hpc_cross_over:gpu", "agentic_architecture:ai"],
                    "sections": [],
                    "url": "https://arxiv.org/abs/2606.10001",
                },
                {
                    "paper_id": "2606.10002",
                    "title": "Paper Two",
                    "abstract": "Accelerator cache search.",
                    "authors": ["B. Author"],
                    "positive_matches": ["hpc_cross_over:accelerator"],
                    "sections": [],
                    "url": "https://arxiv.org/abs/2606.10002",
                },
            ],
        })

        ordered = [keyword for keyword, _count in payload["sorted_keywords"][:4]]
        self.assertEqual(ordered[:3], ["Microarchitecture", "GPU", "AI"])
        self.assertEqual(ordered[3], "Accelerator")

    def test_daily_item_type_filter_recomputes_sidebar_keywords(self):
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "rank": 1,
                    "paper_id": "2606.20001",
                    "title": "GPU Cache Simulation",
                    "abstract": "GPU cache simulation.",
                    "authors": ["A. Author"],
                    "positive_matches": ["microarchitecture_simulators:gpu cache simulation"],
                    "sections": [],
                    "url": "https://arxiv.org/abs/2606.20001",
                },
                {
                    "rank": 2,
                    "item_type": "repository",
                    "repository_full_name": "example/runtime-cache",
                    "title": "example/runtime-cache",
                    "abstract": "Runtime cache for LLM serving.",
                    "authors": ["Repo Owner"],
                    "repository_url": "https://github.com/example/runtime-cache",
                    "repository_topics": ["runtime", "llm", "inference"],
                    "categories": ["github", "Python", "runtime", "llm", "inference"],
                    "sections": [],
                },
            ],
        }, item_type="repository")

        self.assertEqual(payload["active_item_type"], "repository")
        self.assertEqual([item["item_type"] for item in payload["items"]], ["repository"])
        sidebar_keywords = [keyword for keyword, _count in payload["sorted_keywords"]]
        self.assertIn("Runtime", sidebar_keywords)
        self.assertIn("LLM", sidebar_keywords)
        self.assertNotIn("GPU", sidebar_keywords)
        self.assertNotIn("Simulation", sidebar_keywords)

    def test_daily_keywords_prefer_research_nouns_over_title_adjectives(self):
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "paper_id": "2606.00004",
                    "title": "Accurate Aging-Aware GPU Cache Simulation for Neural Accelerators",
                    "abstract": "The paper studies GPU cache simulation for neural accelerators.",
                    "authors": ["A. Author"],
                    "categories": ["cs.AR", "cs.LG"],
                    "positive_matches": ["microarchitecture_simulators:GPU cache simulation"],
                    "sections": ["microarchitecture_simulators"],
                    "url": "https://arxiv.org/abs/2606.00004",
                }
            ],
        })

        keywords = payload["items"][0]["keywords"]
        self.assertIn("GPU", keywords)
        self.assertIn("Cache", keywords)
        self.assertIn("Simulation", keywords)
        self.assertIn("Accelerator", keywords)
        self.assertNotIn("Accurate", keywords)
        self.assertNotIn("Aging", keywords)
        self.assertNotIn("Aware", keywords)

    def test_daily_english_tldr_fallback_uses_concise_abstract_summary(self):
        abstract = (
            "Agentic simulator feedback improves architecture search. "
            + " ".join(["Extra evaluation detail should stay out of the card summary"] * 40)
        )
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "paper_id": "2606.00002",
                    "title": "Long Architecture Summary",
                    "abstract": abstract,
                    "authors": ["A. Author"],
                    "tldr": "中文摘要会被英文 abstract 替换。",
                    "url": "https://arxiv.org/abs/2606.00002",
                }
            ],
        })

        self.assertEqual(payload["items"][0]["tldr"], "Agentic simulator feedback improves architecture search.")
        self.assertLess(len(payload["items"][0]["tldr"]), len(abstract))
        self.assertNotIn("Extra evaluation detail", payload["items"][0]["tldr"])
        self.assertNotIn("...", payload["items"][0]["tldr"])
        self.assertNotIn("…", payload["items"][0]["tldr"])

    def test_daily_repository_tldr_fallback_summarizes_metadata_not_readme(self):
        readme_excerpt = "Runtime cache for LLM serving. Install with pip and follow the README examples."
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "rank": 2,
                    "item_type": "repository",
                    "repository_full_name": "example/runtime-cache",
                    "title": "example/runtime-cache",
                    "abstract": readme_excerpt,
                    "authors": ["Repo Owner"],
                    "repository_url": "https://github.com/example/runtime-cache",
                    "repository_topics": ["runtime", "llm", "inference"],
                    "categories": ["github", "Python", "runtime", "llm", "inference"],
                    "repository_language": "Python",
                    "repository_stars_today": 9,
                    "sections": [],
                }
            ],
        })

        tldr = payload["items"][0]["tldr"]
        self.assertEqual(tldr, "Runtime cache for LLM serving.")
        self.assertNotIn("Problem:", tldr)
        self.assertNotIn("Method:", tldr)
        self.assertNotIn("Why it matters:", tldr)
        self.assertIn("Runtime", tldr)
        self.assertNotIn("README examples", tldr)
        self.assertNotIn("stars today", tldr)
        self.assertNotIn("...", tldr)
        self.assertNotIn("…", tldr)

    def test_daily_repository_payload_exposes_github_source_card_fields(self):
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "rank": 2,
                    "item_type": "repository",
                    "repository_full_name": "example/runtime-cache",
                    "title": "example/runtime-cache",
                    "abstract": "Runtime cache for LLM serving.",
                    "authors": ["Repo Owner"],
                    "repository_url": "https://github.com/example/runtime-cache",
                    "repository_homepage": "https://runtime-cache.example",
                    "repository_topics": ["runtime", "llm", "inference"],
                    "categories": ["github", "Python", "runtime", "llm", "inference"],
                    "repository_language": "Python",
                    "repository_stars": 12345,
                    "repository_forks": 678,
                    "repository_stars_today": 9,
                    "sections": [],
                }
            ],
        })

        repo = payload["items"][0]
        self.assertEqual(repo["repository_full_name"], "example/runtime-cache")
        self.assertEqual(repo["repository_description"], "Runtime cache for LLM serving.")
        self.assertEqual(repo["repository_stars"], 12345)
        self.assertEqual(repo["display_repository_stars"], "12,345")
        self.assertEqual(repo["repository_forks"], 678)
        self.assertEqual(repo["repository_homepage"], "https://runtime-cache.example")
        self.assertEqual(repo["repository_topics"][:3], ["runtime", "llm", "inference"])

    def test_daily_loader_degrades_to_empty_payload_when_remote_fetch_fails(self):
        def failing_fetcher():
            raise OSError("network reset")

        with tempfile.TemporaryDirectory() as tmpdir:
            payload = load_daily_payload(
                payload_fetcher=failing_fetcher,
                config_fetcher=lambda: {},
                cache_path=Path(tmpdir) / "missing.json",
                config_cache_path=Path(tmpdir) / "missing-feedback-config.json",
            )

        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["sorted_keywords"], [])
        self.assertEqual(payload["feedback_config"], {})

    def test_daily_loader_uses_cached_payload_when_remote_fetch_fails(self):
        def failing_fetcher():
            raise OSError("network reset")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "recommendations.json"
            cache_path.write_text(json.dumps(SAMPLE_RECOMMENDER_PAYLOAD), encoding="utf-8")

            payload = load_daily_payload(payload_fetcher=failing_fetcher, config_fetcher=lambda: {}, cache_path=cache_path)

        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["title"], "Agentic AI-Driven Microarchitecture Exploration")

    def test_daily_loader_uses_favorites_archive_dates_for_calendar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            payload = load_daily_payload(
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {},
                favorites_fetcher=lambda: {
                    "records": [
                        {
                            "paper_id": "2606.12563",
                            "rating": "like",
                            "title": "Arbor: Tree Search as a Cognition Layer for Autonomous Agents",
                            "abstract": "Tree search coordinates autonomous agents for systems optimization.",
                            "categories": ["cs.AI"],
                            "section": "exploratory",
                            "created_at": "2026-06-14T06:53:27Z",
                        },
                        {
                            "paper_id": "repo:LMCache/LMCache",
                            "rating": "like",
                            "item_type": "repository",
                            "title": "LMCache/LMCache",
                            "abstract": "KV cache management layer for LLM inference.",
                            "categories": ["github", "Python", "kv-cache", "llm"],
                            "repository_url": "https://github.com/LMCache/LMCache",
                            "section": "hpc_cross_over",
                            "created_at": "2026-06-15T06:53:27Z",
                        },
                    ]
                },
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=tmp_path / "feedback-config.json",
                favorites_cache_path=tmp_path / "favorites.json",
                expected_run_date="2026-06-14",
            )

        self.assertEqual(payload["selected_date"], "2026-06-14")
        self.assertEqual(payload["archive_dates"], ["2026-06-15", "2026-06-14"])
        self.assertEqual(payload["archive_counts"]["2026-06-14"], {"papers": 1, "code": 0})
        self.assertEqual(payload["archive_counts"]["2026-06-15"], {"papers": 0, "code": 1})

    def test_daily_loader_filters_liked_archive_by_keyword_on_selected_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            payload = load_daily_payload(
                date="2026-06-13",
                keywords="GPU",
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {},
                favorites_fetcher=lambda: {
                    "records": [
                        {
                            "paper_id": "2606.13000",
                            "rating": "like",
                            "title": "Cache Archive",
                            "abstract": "This liked paper studies GPU cache simulation.",
                            "created_at": "2026-06-13T12:00:00Z",
                        },
                        {
                            "paper_id": "2606.13001",
                            "rating": "like",
                            "title": "Unrelated Archive",
                            "abstract": "This liked paper studies database indexing.",
                            "created_at": "2026-06-13T13:00:00Z",
                        },
                    ]
                },
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=tmp_path / "feedback-config.json",
                favorites_cache_path=tmp_path / "favorites.json",
            )

        self.assertEqual([item["title"] for item in payload["items"]], ["Cache Archive"])
        self.assertEqual(payload["filter_keywords"], ["GPU"])
        self.assertIn("GPU", payload["items"][0]["keywords"])
        self.assertIn("This liked paper studies GPU cache simulation.", payload["items"][0]["tldr"])
        self.assertIn("GPU", payload["items"][0]["tldr"])
        self.assertGreater(payload["items"][0]["tldr"].count("."), 1)

    def test_daily_loader_can_show_liked_archive_for_selected_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            payload = load_daily_payload(
                date="2026-06-13",
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {},
                favorites_fetcher=lambda: {
                    "records": [
                        {
                            "paper_id": "2606.13000",
                            "rating": "like",
                            "title": "Archived Liked Paper",
                            "abstract": "An older recommendation snapshot about GPU cache simulation. It includes a second sentence that should not become a full abstract dump.",
                            "authors": ["Archive Author"],
                            "categories": ["cs.AR"],
                            "section": "microarchitecture_simulators",
                            "created_at": "2026-06-13T12:00:00Z",
                            "arxiv_url": "https://arxiv.org/abs/2606.13000",
                        },
                        {
                            "paper_id": "2606.14000",
                            "rating": "like",
                            "title": "Other Day Liked Paper",
                            "abstract": "This item belongs to another day.",
                            "created_at": "2026-06-14T12:00:00Z",
                        },
                    ]
                },
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=tmp_path / "feedback-config.json",
                favorites_cache_path=tmp_path / "favorites.json",
            )

        self.assertEqual(payload["selected_date"], "2026-06-13")
        self.assertEqual(payload["run_date"], "2026-06-13")
        self.assertEqual([item["title"] for item in payload["items"]], ["Archived Liked Paper"])
        self.assertIn("Microarchitecture", payload["items"][0]["keywords"])
        self.assertIn("Simulation", payload["items"][0]["keywords"])
        self.assertLess(len(payload["items"][0]["tldr"]), 360)
        self.assertEqual(
            payload["items"][0]["tldr"],
            "An older recommendation snapshot about GPU cache simulation. It includes a second sentence that should not become a full abstract dump.",
        )
        self.assertNotIn("It is most relevant here", payload["items"][0]["tldr"])
        self.assertIn("2026-06-13", payload["archive_dates"])

    def test_daily_loader_keeps_current_run_when_current_date_is_selected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            payload = load_daily_payload(
                date="2026-06-14",
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {},
                favorites_fetcher=lambda: {
                    "records": [
                        {
                            "paper_id": "2606.13000",
                            "rating": "like",
                            "title": "Yesterday Liked Paper",
                            "abstract": "This belongs to yesterday.",
                            "created_at": "2026-06-13T12:00:00Z",
                        }
                    ]
                },
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=tmp_path / "feedback-config.json",
                favorites_cache_path=tmp_path / "favorites.json",
                expected_run_date="2026-06-14",
            )

        self.assertEqual(payload["selected_date"], "2026-06-14")
        self.assertEqual(payload["run_date"], "2026-06-14")
        self.assertEqual([item["title"] for item in payload["items"]], ["Agentic AI-Driven Microarchitecture Exploration"])
        self.assertEqual(payload["archive_dates"], ["2026-06-13"])
        self.assertEqual(payload["archive_counts"]["2026-06-14"], {"papers": 1, "code": 0})

    def test_daily_loader_builds_interest_profile_from_all_liked_archive_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            payload = load_daily_payload(
                date="2026-06-13",
                keywords="GPU",
                payload_fetcher=lambda: {
                    "run_date": "2026-06-16",
                    "recommendations": [
                        {
                            "paper_id": "2606.current",
                            "title": "Current Runtime LLM Paper",
                            "abstract": "Runtime LLM inference that is not part of the long term liked profile.",
                            "authors": ["Current Author"],
                            "positive_matches": ["hpc_cross_over:runtime llm inference"],
                            "sections": [],
                        },
                    ],
                },
                config_fetcher=lambda: {},
                favorites_fetcher=lambda: {
                    "records": [
                        {
                            "paper_id": "2606.13000",
                            "rating": "like",
                            "title": "Cache Archive",
                            "abstract": "This liked paper studies GPU cache simulation.",
                            "created_at": "2026-06-13T12:00:00Z",
                        },
                        {
                            "paper_id": "2606.14000",
                            "rating": "like",
                            "title": "Distributed Scheduling Archive",
                            "abstract": "This liked paper studies distributed exascale workload scheduling.",
                            "created_at": "2026-06-14T12:00:00Z",
                        },
                    ]
                },
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=tmp_path / "feedback-config.json",
                favorites_cache_path=tmp_path / "favorites.json",
            )

        radar = payload["profile_radar"]
        labels = [axis["label"] for axis in radar["axes"]]
        self.assertIn("polygon_points", radar)
        self.assertTrue(radar["polygon_points"])
        self.assertEqual([item["title"] for item in payload["items"]], ["Cache Archive"])
        self.assertIn("GPU", labels)
        self.assertIn("Cache", labels)
        self.assertIn("Distributed", labels)
        self.assertNotIn("Runtime", labels)

    def test_daily_payload_uses_recommender_profile_radar_instead_of_current_items(self):
        backend_radar = {
            "source": "feedback_events",
            "total_likes": 12,
            "axes": [
                {"label": "Cache", "value": 7},
                {"label": "Gem5", "value": 5},
                {"label": "HPC", "value": 3},
                {"label": "CUDA", "value": 2},
                {"label": "Simulation", "value": 1},
            ],
        }

        payload = build_daily_payload(
            {
                "run_date": "2026-06-16",
                "profile_radar": backend_radar,
                "recommendations": [
                    {
                        "paper_id": "2606.current",
                        "title": "Current Runtime LLM Paper",
                        "abstract": "Runtime LLM inference appears in today's list only.",
                        "positive_matches": ["hpc_cross_over:runtime llm inference"],
                    }
                ],
            },
            keywords="Runtime",
        )

        values = {axis["label"]: axis["value"] for axis in payload["profile_radar"]["axes"]}
        self.assertEqual(values["Cache"], 7)
        self.assertEqual(values["Gem5"], 5)
        self.assertEqual(values["HPC"], 3)
        self.assertNotIn("Runtime", values)
        self.assertIn("polygon_points", payload["profile_radar"])
        self.assertEqual([item["title"] for item in payload["items"]], ["Current Runtime LLM Paper"])

    def test_daily_profile_radar_side_labels_anchor_inward_to_avoid_card_overflow(self):
        payload = build_daily_payload(
            {
                "run_date": "2026-06-16",
                "profile_radar": {
                    "axes": [
                        {"label": "Cache", "value": 1},
                        {"label": "RightTopTopic", "value": 1},
                        {"label": "RightBottomTopic", "value": 1},
                        {"label": "CUDA", "value": 1},
                        {"label": "LeftBottomTopic", "value": 1},
                        {"label": "LeftTopTopic", "value": 1},
                    ]
                },
                "recommendations": [],
            }
        )

        anchors = {axis["label"]: axis["label_anchor"] for axis in payload["profile_radar"]["axes"]}
        self.assertEqual(anchors["RightTopTopic"], "end")
        self.assertEqual(anchors["RightBottomTopic"], "end")
        self.assertEqual(anchors["LeftBottomTopic"], "start")
        self.assertEqual(anchors["LeftTopTopic"], "start")

    def test_daily_favorites_archive_fetch_preserves_sidecar_path_slashes(self):
        requested_urls = []

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        def fake_urlopen(request, timeout):
            requested_urls.append(request.full_url)
            if request.full_url == "https://api.example/tree":
                return FakeResponse({
                    "tree": [
                        {"type": "blob", "path": "2026-06/exploration/2606.12563.json"},
                        {"type": "blob", "path": "README.md"},
                    ]
                })
            return FakeResponse({
                "paper_id": "2606.12563",
                "rating": "like",
                "created_at": "2026-06-14T06:53:27Z",
            })

        with patch("app.daily.urlopen", side_effect=fake_urlopen):
            payload = fetch_daily_favorites_archive(
                tree_url="https://api.example/tree",
                raw_base_url="https://raw.example/main",
            )

        self.assertEqual(len(payload["records"]), 1)
        self.assertIn("https://raw.example/main/2026-06/exploration/2606.12563.json", requested_urls)
        self.assertNotIn("https://raw.example/main/2026-06%2Fexploration%2F2606.12563.json", requested_urls)

    def test_daily_loader_uses_cached_favorites_when_remote_fetch_fails(self):
        cached_favorites = {
            "records": [
                {
                    "paper_id": "2606.15000",
                    "rating": "like",
                    "title": "Archived Liked Paper",
                    "abstract": "Cached liked paper.",
                    "created_at": "2026-06-15T12:00:00Z",
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            favorites_cache_path = tmp_path / "favorites.json"
            favorites_cache_path.write_text(json.dumps(cached_favorites), encoding="utf-8")

            payload = load_daily_payload(
                date="2026-06-15",
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {},
                favorites_fetcher=lambda: (_ for _ in ()).throw(OSError("github unavailable")),
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=tmp_path / "feedback-config.json",
                favorites_cache_path=favorites_cache_path,
            )

        self.assertEqual(payload["selected_date"], "2026-06-15")
        self.assertEqual(payload["items"][0]["title"], "Archived Liked Paper")
        self.assertEqual(payload["archive_dates"], ["2026-06-15"])

    def test_daily_loader_serves_fresh_cache_without_blocking_on_remote_fetch(self):
        remote_payload = {
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "paper_id": "2606.99999",
                    "title": "Remote Payload Should Not Block Cached Page",
                    "abstract": "This remote payload should not be used while cache is fresh.",
                    "authors": ["Remote Author"],
                    "url": "https://arxiv.org/abs/2606.99999",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "recommendations.json"
            config_cache_path = Path(tmpdir) / "feedback-config.json"
            cache_path.write_text(json.dumps(SAMPLE_RECOMMENDER_PAYLOAD), encoding="utf-8")
            config_cache_path.write_text(json.dumps({
                "supabase_url": "https://cached.supabase.co",
                "supabase_anon_key": "cached-anon-key",
            }), encoding="utf-8")

            calls = {"payload": 0, "config": 0}

            def slow_payload_fetcher():
                calls["payload"] += 1
                time.sleep(0.05)
                return remote_payload

            def slow_config_fetcher():
                calls["config"] += 1
                time.sleep(0.05)
                return {"supabase_url": "https://remote.supabase.co", "supabase_anon_key": "remote-anon-key"}

            payload = load_daily_payload(
                payload_fetcher=slow_payload_fetcher,
                config_fetcher=slow_config_fetcher,
                cache_path=cache_path,
                config_cache_path=config_cache_path,
                remote_cache_ttl_seconds=300,
                refresh_stale_cache_in_background=False,
                expected_run_date="2026-06-14",
            )

        self.assertEqual(calls, {"payload": 0, "config": 0})
        self.assertEqual(payload["items"][0]["title"], "Agentic AI-Driven Microarchitecture Exploration")
        self.assertEqual(payload["feedback_config"]["supabase_url"], "https://cached.supabase.co")

    def test_daily_loader_refreshes_fresh_cache_when_cached_run_date_is_stale(self):
        remote_payload = {
            "run_date": "2026-06-15",
            "recommendations": [
                {
                    "paper_id": "2606.99999",
                    "title": "Fresh Daily Recommendations",
                    "abstract": "The remote payload should replace yesterday's cached daily recommendations.",
                    "authors": ["Remote Author"],
                    "url": "https://arxiv.org/abs/2606.99999",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "recommendations.json"
            config_cache_path = Path(tmpdir) / "feedback-config.json"
            cache_path.write_text(json.dumps(SAMPLE_RECOMMENDER_PAYLOAD), encoding="utf-8")
            config_cache_path.write_text("{}", encoding="utf-8")
            calls = {"payload": 0}

            def payload_fetcher():
                calls["payload"] += 1
                return remote_payload

            payload = load_daily_payload(
                payload_fetcher=payload_fetcher,
                config_fetcher=lambda: {},
                cache_path=cache_path,
                config_cache_path=config_cache_path,
                remote_cache_ttl_seconds=300,
                expected_run_date="2026-06-15",
            )

            cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(calls["payload"], 1)
        self.assertEqual(payload["run_date"], "2026-06-15")
        self.assertEqual(payload["items"][0]["title"], "Fresh Daily Recommendations")
        self.assertEqual(cached_payload["run_date"], "2026-06-15")

    def test_daily_loader_reuses_cached_feedback_config_when_config_fetch_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_cache_path = tmp_path / "feedback-config.json"
            first = load_daily_payload(
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {
                    "supabase_url": "https://example.supabase.co",
                    "supabase_anon_key": "anon-key",
                },
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=config_cache_path,
            )
            second = load_daily_payload(
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: (_ for _ in ()).throw(OSError("network reset")),
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=config_cache_path,
            )

        self.assertEqual(first["feedback_config"]["supabase_url"], "https://example.supabase.co")
        self.assertEqual(second["feedback_config"]["supabase_anon_key"], "anon-key")

    def test_daily_loader_reuses_cached_feedback_config_when_config_fetch_is_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_cache_path = tmp_path / "feedback-config.json"
            config_cache_path.write_text(json.dumps({
                "supabase_url": "https://cached.supabase.co",
                "supabase_anon_key": "cached-anon-key",
            }), encoding="utf-8")

            payload = load_daily_payload(
                payload_fetcher=lambda: SAMPLE_RECOMMENDER_PAYLOAD,
                config_fetcher=lambda: {},
                cache_path=tmp_path / "recommendations.json",
                config_cache_path=config_cache_path,
            )

        self.assertEqual(payload["feedback_config"]["supabase_url"], "https://cached.supabase.co")
        self.assertEqual(payload["feedback_config"]["supabase_anon_key"], "cached-anon-key")

    def test_served_templates_include_daily_nav_and_feedback_actions(self):
        root = Path(__file__).resolve().parents[1]
        base = (root / "app/templates/base.html").read_text(encoding="utf-8")
        daily = (root / "app/templates/pages/daily.html").read_text(encoding="utf-8")

        self.assertIn('href="/daily"', base)
        self.assertIn("Daily", base)
        self.assertIn('href="/static/css/styles.css?v=150"', base)
        self.assertIn("Paper", daily)
        self.assertIn("PDF", daily)
        self.assertIn("Code", daily)
        self.assertIn("article-grid daily-grid", daily)
        self.assertIn("daily-sidebar-heading", daily)
        self.assertIn("daily-type-toggle", daily)
        self.assertIn("active_item_type", daily)
        self.assertIn("archive_dates", daily)
        self.assertIn("archive_counts", daily)
        self.assertIn("profile_radar", daily)
        self.assertIn("selected_date", daily)
        self.assertIn('id="dailyArchiveCalendar"', daily)
        self.assertIn('data-archive-counts', daily)
        self.assertIn("daily-archive-card", daily)
        self.assertIn("dailyProfileRadar", daily)
        self.assertIn("daily-profile-card", daily)
        self.assertIn("daily-profile-polygon", daily)
        self.assertNotIn("daily-profile-values", daily)
        self.assertIn("daily-archive-calendar.js?v=3", daily)
        self.assertIn("daily-card-main-meta", daily)
        self.assertIn("daily-meta-authors", daily)
        self.assertIn("daily-meta-date", daily)
        self.assertNotIn("daily-meta-stars", daily)
        self.assertNotIn("daily-card-fact", daily)
        self.assertIn("display_repository_stars", daily)
        self.assertIn("github-repo-card", daily)
        self.assertIn("github-repo-top", daily)
        self.assertIn("github-repo-desc", daily)
        self.assertIn("github-repo-stats", daily)
        self.assertIn("github-repo-stat", daily)
        self.assertIn("repository_description", daily)
        self.assertIn("repository_full_name", daily)
        self.assertIn("repository_forks", daily)
        self.assertIn("repository_homepage", daily)
        self.assertIn("daily-action-icon", daily)
        self.assertIn("daily-action-label", daily)
        self.assertIn("daily-action-pdf", daily)
        self.assertIn("daily-action-code", daily)
        self.assertIn("daily-action-like", daily)
        self.assertIn("daily-action-dislike", daily)
        self.assertIn("{% if is_upload_authenticated %}", daily)
        self.assertIn('id="dailyFeedbackConfig"', daily)
        self.assertIn('id="dailyFeedbackConfig"\n             hidden', daily)
        self.assertIn('data-feedback-enabled="true"', daily)
        self.assertIn('data-run-date="{{ run_date or', daily)
        self.assertIn('data-feedback-rating="like"', daily)
        self.assertIn('data-feedback-rating="dislike"', daily)
        self.assertIn('daily-feedback.js?v=5', daily)
        self.assertIn("item.display_authors", daily)
        self.assertNotIn("item.authors|join", daily)
        self.assertNotIn("daily-sidebar-meta", daily)
        self.assertNotIn("Run {{ run_date }}", daily)
        self.assertNotIn("shown", daily)
        self.assertNotIn("Code Search", daily)
        self.assertNotIn("item.type_label }} #{{ item.rank", daily)
        self.assertNotIn("AI {{ item.ai_score", daily)
        self.assertNotIn("stars today", daily)
        self.assertNotIn("<span>TLDR</span>", daily)
        self.assertNotIn("affiliations", daily)
        self.assertNotIn("作者单位", daily)

        styles = (root / "static/css/styles.css").read_text(encoding="utf-8")
        self.assertIn(".daily-grid", styles)
        self.assertIn("300px", styles)
        self.assertIn(".daily-filter-chips {\n    justify-content: flex-start;", styles)
        self.assertIn(".daily-keyword-list {\n    justify-content: flex-start;", styles)
        self.assertIn("gap: 8px", styles)
        self.assertIn(".github-repo-card", styles)
        self.assertIn(".daily-action-button.action-glass", styles)
        self.assertIn(".daily-action-button.daily-action-dislike", styles)
        self.assertIn(".daily-action-button.daily-action-like:hover", styles)
        self.assertIn("--daily-action-blue-gradient: linear-gradient(135deg, #93c5fd, #2563eb);", styles)
        self.assertNotIn(".daily-action-button.action-glass:not(.daily-action-dislike),\n.daily-action-button.feedback.daily-action-like", styles)
        self.assertIn(".daily-action-button.action-glass:not(.daily-action-dislike):hover,\n.daily-action-button.action-glass:not(.daily-action-dislike):active", styles)
        self.assertIn(".daily-action-button.daily-action-like:hover,\n.daily-action-button.feedback.is-active", styles)
        self.assertIn("background: var(--daily-action-blue-gradient);", styles)
        self.assertIn("border-color: rgba(37, 99, 235, 0.42);", styles)
        self.assertIn(".daily-archive-card", styles)
        self.assertIn(".daily-archive-card {\n    --anniv-grad: linear-gradient(135deg, #93c5fd, #2563eb);", styles)
        self.assertIn(".daily-grid .sidebar {\n    gap: 24px;", styles)
        self.assertIn(".daily-profile-card", styles)
        self.assertIn(".daily-profile-polygon", styles)
        self.assertNotIn(".daily-profile-values", styles)
        self.assertNotIn(".daily-archive-card {\n    --anniv-grad: linear-gradient(135deg, #93c5fd, #2563eb);\n    margin-top: 24px;", styles)
        self.assertNotIn(".daily-archive-day.is-liked::after", styles)
        self.assertNotIn("linear-gradient(135deg, #10b981, #2563eb)", styles)
        self.assertIn("#f97316", styles)
        self.assertNotIn(".daily-filter-chips .chip {\n    width: 100%;", styles)
        self.assertNotIn(".daily-keyword-list .chip {\n    width: 100%;", styles)

        feedback_js = (root / "static/js/components/daily-feedback.js").read_text(encoding="utf-8")
        self.assertIn("homepage_daily_feedback_ui_state", feedback_js)
        self.assertIn('data-feedback-enabled") !== "true"', feedback_js)
        self.assertIn("feedback_events", feedback_js)
        self.assertIn('source = "page"', feedback_js)
        self.assertIn("item_type", feedback_js)
        self.assertIn("repository_url", feedback_js)
        self.assertIn("paper_links", feedback_js)
        self.assertIn("legacyFeedbackPayload", feedback_js)
        self.assertIn("applyStoredFeedbackState", feedback_js)
        self.assertIn("setFeedbackButtonLabel", feedback_js)
        self.assertIn("hideCard", feedback_js)
        self.assertIn("daily-feedback-state-change", feedback_js)

        archive_js = (root / "static/js/components/daily-archive-calendar.js").read_text(encoding="utf-8")
        self.assertIn("homepage_daily_feedback_ui_state", archive_js)
        self.assertIn("daily-archive-day", archive_js)
        self.assertIn("is-liked", archive_js)
        self.assertIn("date=", archive_js)
        self.assertIn("archiveCounts", archive_js)
        self.assertIn("runDate", archive_js)
        self.assertIn("showTooltip", archive_js)
        self.assertIn("anniversary-tooltip", archive_js)
        self.assertIn("Papers", archive_js)
        self.assertIn("daily-feedback-state-change", archive_js)


if __name__ == "__main__":
    unittest.main()
