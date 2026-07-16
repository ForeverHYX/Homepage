import json
import inspect
from unittest import TestCase
from unittest.mock import call, patch

from app.routers import pages


class HomepagePayloadTests(TestCase):
    @patch.object(pages, "get_about_info", return_value={"name": "Yixun"})
    @patch.object(
        pages,
        "parse_markdown_sections",
        return_value=[("Introduction", "<p>Hello</p>")],
    )
    @patch.object(pages, "parse_and_merge_news")
    def test_ssr_payload_skips_legacy_html_fields(
        self,
        parse_news,
        _parse_sections,
        _about,
    ) -> None:
        parse_news.side_effect = lambda *, limit: f"<ul data-limit='{limit}'></ul>"

        payload = pages._build_home_payload(include_legacy_fields=False)

        self.assertNotIn("sections_html", payload)
        self.assertNotIn("all_news_html", payload)
        self.assertEqual(payload["news_html"], "<ul data-limit='6'></ul>")
        parse_news.assert_called_once_with(limit=6)
        self.assertIn(
            "_build_home_payload(include_legacy_fields=False)",
            inspect.getsource(pages.home_page),
        )

    @patch.object(pages, "get_about_info", return_value={"name": "Yixun"})
    @patch.object(
        pages,
        "parse_markdown_sections",
        return_value=[("Introduction", "<p>Hello</p>")],
    )
    @patch.object(pages, "parse_and_merge_news")
    def test_legacy_home_api_payload_stays_backward_compatible(
        self,
        parse_news,
        _parse_sections,
        _about,
    ) -> None:
        parse_news.side_effect = lambda *, limit: f"<ul data-limit='{limit}'></ul>"

        payload = pages._build_home_payload()

        self.assertIn("sections_html", payload)
        self.assertEqual(payload["all_news_html"], "<ul data-limit='100'></ul>")
        self.assertEqual(parse_news.call_args_list, [call(limit=6), call(limit=100)])

    @patch.object(pages, "parse_and_merge_news", return_value="<ul><li>News</li></ul>")
    def test_news_api_returns_only_modal_html(self, parse_news) -> None:
        response = pages.news_api()
        payload = json.loads(response.body)

        self.assertEqual(payload, {"all_news_html": "<ul><li>News</li></ul>"})
        self.assertEqual(response.headers["cache-control"], "public, max-age=60")
        parse_news.assert_called_once_with(limit=100)
