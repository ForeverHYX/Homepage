import unittest
import json
import tempfile
import time
from pathlib import Path

from app.daily import build_daily_payload, daily_payload_search_entries, daily_search_entries, load_daily_payload


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


class DailyIntegrationTests(unittest.TestCase):
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

    def test_daily_search_entries_include_title_and_keywords(self):
        entries = daily_search_entries(SAMPLE_RECOMMENDER_PAYLOAD)

        self.assertEqual(entries[0]["type"], "Daily")
        self.assertEqual(entries[0]["title"], "Agentic AI-Driven Microarchitecture Exploration")
        self.assertIn("Agent", entries[0]["tags"])
        self.assertIn("Gem5", entries[0]["tags"])
        self.assertNotIn("cs.AR", entries[0]["tags"])
        self.assertEqual(entries[0]["url"], "/daily?paper_id=2606.00001")

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

    def test_daily_english_tldr_fallback_keeps_full_text_without_ellipsis(self):
        long_abstract = " ".join(["Agentic simulator feedback improves architecture search"] * 80)
        payload = build_daily_payload({
            "run_date": "2026-06-14",
            "recommendations": [
                {
                    "paper_id": "2606.00002",
                    "title": "Long Architecture Summary",
                    "abstract": long_abstract,
                    "authors": ["A. Author"],
                    "tldr": "中文摘要会被英文 abstract 替换。",
                    "url": "https://arxiv.org/abs/2606.00002",
                }
            ],
        })

        self.assertEqual(payload["items"][0]["tldr"], long_abstract)
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
        self.assertNotEqual(tldr, readme_excerpt)
        self.assertIn("Problem:", tldr)
        self.assertIn("Why it matters:", tldr)
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
        self.assertIn("Paper", daily)
        self.assertIn("PDF", daily)
        self.assertIn("Code", daily)
        self.assertIn("article-grid daily-grid", daily)
        self.assertIn("daily-sidebar-heading", daily)
        self.assertIn("daily-type-toggle", daily)
        self.assertIn("active_item_type", daily)
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
        self.assertIn('id="dailyFeedbackConfig"', daily)
        self.assertIn('id="dailyFeedbackConfig"\n             hidden', daily)
        self.assertIn('data-run-date="{{ run_date or', daily)
        self.assertIn('data-feedback-rating="like"', daily)
        self.assertIn('data-feedback-rating="dislike"', daily)
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
        self.assertIn(".daily-action-button.action-glass:not(.daily-action-dislike):hover,\n.daily-action-button.action-glass:not(.daily-action-dislike):active", styles)
        self.assertIn(".daily-action-button.daily-action-like:hover,\n.daily-action-button.feedback.is-active", styles)
        self.assertIn("background: var(--daily-action-blue-gradient);", styles)
        self.assertNotIn("linear-gradient(135deg, #10b981, #2563eb)", styles)
        self.assertIn("#f97316", styles)
        self.assertNotIn(".daily-filter-chips .chip {\n    width: 100%;", styles)
        self.assertNotIn(".daily-keyword-list .chip {\n    width: 100%;", styles)

        feedback_js = (root / "static/js/components/daily-feedback.js").read_text(encoding="utf-8")
        self.assertIn("homepage_daily_feedback_ui_state", feedback_js)
        self.assertIn("feedback_events", feedback_js)
        self.assertIn('source = "page"', feedback_js)
        self.assertIn("item_type", feedback_js)
        self.assertIn("repository_url", feedback_js)
        self.assertIn("paper_links", feedback_js)
        self.assertIn("legacyFeedbackPayload", feedback_js)
        self.assertIn("applyStoredFeedbackState", feedback_js)
        self.assertIn("setFeedbackButtonLabel", feedback_js)
        self.assertIn("hideCard", feedback_js)


if __name__ == "__main__":
    unittest.main()
