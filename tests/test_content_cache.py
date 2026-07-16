import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from unittest import TestCase
from unittest.mock import patch

from app import content_utils, news
from app.cache import (
    CACHE_MAX_ENTRIES,
    _cache,
    cache_by_mtime,
    cache_by_signature,
    clear,
)


class UnifiedContentCacheTests(TestCase):
    def setUp(self) -> None:
        clear()

    def tearDown(self) -> None:
        clear()

    def test_one_file_can_cache_multiple_namespaced_derivations(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "content.md"
            path.write_text("# Intro\nHello", encoding="utf-8")

            sections = cache_by_mtime(
                path,
                lambda: [("Intro", "<p>Hello</p>")],
                namespace="sections",
            )
            rendered = cache_by_mtime(
                path,
                lambda: "<h1>Intro</h1><p>Hello</p>",
                namespace="rendered",
            )

            self.assertIsInstance(sections, list)
            self.assertIsInstance(rendered, str)
            self.assertEqual(len(_cache), 2)

    def test_size_change_invalidates_even_when_mtime_is_preserved(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.txt"
            path.write_text("one", encoding="utf-8")
            original_stat = path.stat()
            calls = 0

            def load() -> str:
                nonlocal calls
                calls += 1
                return path.read_text(encoding="utf-8")

            self.assertEqual(cache_by_mtime(path, load), "one")
            path.write_text("a longer value", encoding="utf-8")
            os.utime(
                path,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )
            self.assertEqual(cache_by_mtime(path, load), "a longer value")
            self.assertEqual(calls, 2)

    def test_concurrent_cold_load_is_single_flight(self) -> None:
        counter_lock = Lock()
        calls = 0

        def load() -> object:
            nonlocal calls
            with counter_lock:
                calls += 1
            time.sleep(0.02)
            return object()

        def cached_load(_: int) -> object:
            return cache_by_signature(
                "shared",
                "v1",
                load,
                namespace="concurrent-test",
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(cached_load, range(16)))

        self.assertEqual(calls, 1)
        self.assertTrue(all(value is values[0] for value in values))

    def test_cache_has_a_hard_entry_bound(self) -> None:
        for index in range(CACHE_MAX_ENTRIES + 12):
            cache_by_signature(
                f"key-{index}",
                index,
                lambda index=index: index,
                namespace="bounded-test",
            )

        self.assertEqual(len(_cache), CACHE_MAX_ENTRIES)


class HomepageDerivedCacheTests(TestCase):
    def setUp(self) -> None:
        clear()
        content_utils.parse_education_timeline.cache_clear()

    def tearDown(self) -> None:
        clear()
        content_utils.parse_education_timeline.cache_clear()

    def test_raw_home_sections_are_read_and_split_once(self) -> None:
        with TemporaryDirectory() as temp_dir:
            content_dir = Path(temp_dir)
            (content_dir / "content.md").write_text(
                "# Introduction\nHello\n# Education\nDegree\n",
                encoding="utf-8",
            )
            parser = content_utils._parse_raw_sections
            with patch.object(content_utils, "CONTENT_DIR", content_dir), patch.object(
                content_utils,
                "_parse_raw_sections",
                wraps=parser,
            ) as parse_mock:
                self.assertEqual(
                    content_utils.get_raw_section_body("content.md", "Education"),
                    "Degree",
                )
                self.assertEqual(
                    content_utils.get_raw_section_body("content.md", "Introduction"),
                    "Hello",
                )

            parse_mock.assert_called_once()

    def test_education_renderer_reuses_identical_input(self) -> None:
        with patch.object(
            content_utils,
            "_parse_education_timeline",
            return_value='<div class="edu-timeline"></div>',
        ) as render_mock:
            first = content_utils.parse_education_timeline("same markdown")
            second = content_utils.parse_education_timeline("same markdown")

        self.assertEqual(first, second)
        render_mock.assert_called_once_with("same markdown")


class NewsCacheTests(TestCase):
    def setUp(self) -> None:
        clear()

    def tearDown(self) -> None:
        clear()

    def test_different_limits_share_one_source_parse(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_dir = root / "content"
            content_dir.mkdir()
            (content_dir / "news.md").write_text(
                "- **2026-07**: First item.\n- **2026-06**: Second item.\n",
                encoding="utf-8",
            )
            config_file = root / "gallery_config.json"
            original_builder = news._build_news_items

            with patch.object(news, "CONTENT_DIR", content_dir), patch.object(
                news,
                "GALLERY_CONFIG_FILE",
                config_file,
            ), patch.object(news, "get_gallery_folders", return_value=[]), patch.object(
                news,
                "_build_news_items",
                wraps=original_builder,
            ) as build_mock:
                short_feed = news.parse_and_merge_news(limit=1)
                full_feed = news.parse_and_merge_news(limit=100)

            self.assertIn("First item.", short_feed)
            self.assertNotIn("Second item.", short_feed)
            self.assertIn("Second item.", full_feed)
            build_mock.assert_called_once()

    def test_input_edits_replace_the_stable_news_entry(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_dir = root / "content"
            content_dir.mkdir()
            news_path = content_dir / "news.md"
            news_path.write_text("- **2026-07**: One.\n", encoding="utf-8")
            config_file = root / "gallery_config.json"

            with patch.object(news, "CONTENT_DIR", content_dir), patch.object(
                news,
                "GALLERY_CONFIG_FILE",
                config_file,
            ), patch.object(news, "get_gallery_folders", return_value=[]):
                self.assertIn("One.", news.parse_and_merge_news())
                self.assertEqual(len(_cache), 1)

                news_path.write_text(
                    "- **2026-07**: A longer replacement.\n",
                    encoding="utf-8",
                )
                self.assertIn("A longer replacement.", news.parse_and_merge_news())

            self.assertEqual(len(_cache), 1)

