from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
EXAMS_DIR = ROOT / "content" / "exams"


class ExamPagesTests(TestCase):
    def test_exams_page_lists_historical_and_mock_exams(self) -> None:
        response = TestClient(app).get("/exams")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Compiler Exams", response.text)
        self.assertIn("23-24 编译原理期末回忆卷", response.text)
        self.assertIn("大题回忆卷", response.text)
        self.assertIn("模拟期末卷 A", response.text)
        self.assertIn('href="/exams/compiler-2023-2024-final-recall"', response.text)
        self.assertIn('href="/exams/compiler-final-big-question-recall"', response.text)

    def test_exam_detail_renders_markdown_with_collapsible_answers(self) -> None:
        response = TestClient(app).get("/exams/compiler-2023-2024-final-recall")

        self.assertEqual(response.status_code, 200)
        self.assertIn("23-24 编译原理期末回忆卷", response.text)
        self.assertIn("判断题", response.text)
        self.assertIn("有符号数（带浮点带指数）的 DFA", response.text)
        self.assertIn("<details", response.text)
        self.assertIn("<summary>参考答案</summary>", response.text)
        self.assertIn("Back to Exams", response.text)

    def test_exam_markdown_files_are_one_file_per_exam_with_answers(self) -> None:
        expected = {
            "compiler-2023-2024-final-recall.md",
            "compiler-final-big-question-recall.md",
            "compiler-mock-final-a.md",
            "compiler-mock-final-b.md",
            "compiler-mock-final-c.md",
        }

        self.assertTrue(EXAMS_DIR.exists())
        actual = {path.name for path in EXAMS_DIR.glob("*.md")}
        self.assertEqual(expected, actual)
        for filename in expected:
            text = (EXAMS_DIR / filename).read_text(encoding="utf-8")
            self.assertIn("<details>", text)
            self.assertIn("<summary>参考答案</summary>", text)

    def test_exams_are_in_search_index_and_sitemap(self) -> None:
        client = TestClient(app)

        search = client.get("/api/search-index")
        self.assertEqual(search.status_code, 200)
        entries = search.json()
        urls = {entry["url"] for entry in entries}
        self.assertIn("/exams/compiler-2023-2024-final-recall", urls)
        self.assertIn("/exams/compiler-mock-final-a", urls)

        sitemap = client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("<loc>https://foreverhyx.top/exams</loc>", sitemap.text)

    def test_nav_includes_exams_on_desktop_and_mobile(self) -> None:
        base = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")

        self.assertIn('<a href="/exams" class="nav-link" data-route="/exams">Exams</a>', base)
        self.assertIn('<a href="/exams" class="nav-mobile-link" data-route="/exams">Exams</a>', base)
