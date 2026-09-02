from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import markdown_utils
from app.cache import _cache
from app.main import app
from app.publication_badges import resolve_conference_style


class PublicationBadgeTests(TestCase):
    def test_mainstream_architecture_conference_styles_are_auto_selected(self) -> None:
        cases = {
            "MICRO59": "micro",
            "ISCA 2027": "isca",
            "HPCA-33": "hpca",
            "ASPLOS 2028": "asplos",
            "CGO 2027": "cgo",
        }
        for venue, expected in cases.items():
            with self.subTest(venue=venue):
                self.assertEqual(resolve_conference_style(venue), expected)

    def test_structured_parser_exposes_canonical_artifact_badges(self) -> None:
        with TemporaryDirectory() as temp_dir:
            content_dir = Path(temp_dir)
            (content_dir / "content.md").write_text(
                """# Selected Publication

:::publication
type: conference
title: Reproducible Architecture
venue: International Symposium on Microarchitecture
venue_short: MICRO59
badges: Artifact Available | Artifact Functional | Results Reproduced
authors: **Y. Hong**
:::
""",
                encoding="utf-8",
            )
            _cache.clear()
            with patch.object(markdown_utils, "CONTENT_DIR", content_dir):
                publication = markdown_utils.get_publications()[0]

        self.assertEqual(publication["conference_style"], "micro")
        self.assertEqual(
            [badge["label"] for badge in publication["artifact_badges"]],
            ["Artifact Available", "Artifact Functional", "Results Reproduced"],
        )
        self.assertIn("publication-conference-micro", publication["html"])
        self.assertIn("publication-artifact-badges", publication["html"])
        self.assertIn("publication-artifact-badge-official", publication["html"])
        self.assertIn("images/publication-badges/artifacts_available.jpg", publication["html"])
        self.assertNotIn("<svg", publication["html"])

    def test_micro_artifact_badges_render_on_home_and_publications_pages(self) -> None:
        _cache.clear()
        client = TestClient(app)
        for path in ("/", "/publications"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("publication-conference-micro", response.text)
            self.assertIn("Artifact Available", response.text)
            self.assertIn("Artifact Functional", response.text)
            self.assertIn("Results Reproduced", response.text)
            self.assertIn("publication-artifact-badge-official", response.text)
            self.assertIn("images/publication-badges/artifacts_available.jpg", response.text)

    def test_official_artifact_badges_are_horizontal_without_recoloring_venues(self) -> None:
        root = Path(__file__).resolve().parents[1]
        styles = (root / "static/css/src/35-publication-badges.css").read_text(encoding="utf-8")

        badge_row = styles.split(".publication-artifact-badges {", 1)[1].split("}", 1)[0]
        self.assertIn("flex-direction: row", badge_row)
        self.assertIn("flex-wrap: nowrap", badge_row)
        self.assertIn("--conference-badge-accent: #b42346", styles)
        self.assertIn("--conference-badge-accent: #4338ca", styles)
        self.assertIn("--conference-badge-accent: #047857", styles)
        self.assertIn("--conference-badge-accent: #7e22ce", styles)
        self.assertIn("--conference-badge-accent: #c2410c", styles)
