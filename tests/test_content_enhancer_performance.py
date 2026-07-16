from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ENHANCER = ROOT / "static" / "js" / "components" / "content-enhancer.js"
ARTICLE_TEMPLATE = ROOT / "app" / "templates" / "pages" / "article_detail.html"


class ContentEnhancerPerformanceTests(TestCase):
    def test_highlighter_is_skipped_for_plain_text_blocks(self) -> None:
        source = CONTENT_ENHANCER.read_text(encoding="utf-8")

        self.assertIn("function needsSyntaxHighlighting()", source)
        self.assertIn('["text", "plain", "plaintext"]', source)
        self.assertIn('code.classList.contains("nohighlight")', source)
        self.assertIn("if (!needsSyntaxHighlighting()) return;", source)

    def test_enhancement_does_not_wait_on_remote_highlighter(self) -> None:
        source = CONTENT_ENHANCER.read_text(encoding="utf-8")

        init_body = source.split("function init()", 1)[1]
        self.assertLess(init_body.index("decorateCodeBlocks();"), init_body.index("loadHighlightScript"))
        self.assertLess(init_body.index("enhanceGithubLinks();"), init_body.index("loadHighlightScript"))
        self.assertNotIn("setTimeout", init_body)
        self.assertIn('content-enhancer.js?v=98', ARTICLE_TEMPLATE.read_text(encoding="utf-8"))
