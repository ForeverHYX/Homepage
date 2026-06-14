import re
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
LIGHTFIELD_JS = ROOT / "static" / "js" / "effects" / "lightfield.js"
LIQUID_GLASS_JS = ROOT / "static" / "js" / "effects" / "liquid-glass.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"
BASE_HTML = ROOT / "app" / "templates" / "base.html"


class HomepageEffectsPerformanceTests(TestCase):
    def test_lightfield_uses_low_frequency_css_driven_motion(self) -> None:
        source = LIGHTFIELD_JS.read_text()
        styles = STYLES_CSS.read_text()

        self.assertIn("LIGHTFIELD_UPDATE_INTERVAL", source)
        self.assertNotIn("nextChangeAt", source)
        self.assertNotIn("requestAnimationFrame(frame)", source)

        spot_block = re.search(r"\.home-lightspot\s*\{(?P<body>.*?)\n\}", styles, re.S)
        self.assertIsNotNone(spot_block)
        self.assertIn("transition:", spot_block.group("body"))
        self.assertIn("--spot-motion-duration", spot_block.group("body"))

    def test_liquid_glass_throttles_pointer_target_sync(self) -> None:
        source = LIQUID_GLASS_JS.read_text()

        self.assertIn("POINTER_SYNC_INTERVAL", source)
        self.assertIn("targetSyncTimeoutId", source)

    def test_nav_island_uses_dedicated_optical_material(self) -> None:
        source = LIQUID_GLASS_JS.read_text()
        styles = STYLES_CSS.read_text()

        nav_block = re.search(r"\.nav-island\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S)
        self.assertIsNotNone(nav_block)
        nav_body = nav_block.group("body")
        self.assertIn("--liquid-nav-hover-glow", nav_body)
        self.assertIn("--liquid-nav-caustic-opacity", nav_body)
        self.assertIn("--liquid-nav-refraction", nav_body)

        self.assertIn(".nav-island .home-liquid-warp::before", styles)
        self.assertIn(".nav-island .home-liquid-warp::after", styles)
        self.assertIn(".nav-island.home-liquid-card:hover", styles)
        self.assertNotIn(".nav-island:hover {\n    transform:", styles)

        self.assertIn("navAmbient", source)
        self.assertIn("navHoverGlow", source)
        self.assertIn("hasPagePointer", source)

    def test_profile_name_uses_handwritten_font_stack(self) -> None:
        styles = STYLES_CSS.read_text()
        base = BASE_HTML.read_text()

        self.assertIn("Dancing+Script", base)
        self.assertNotIn("Allura", base)
        self.assertRegex(base, r"/static/css/styles\.css\?v=\d+")
        self.assertIn("Zhi+Mang+Xing", base)
        self.assertIn("--font-hand-en", styles)
        self.assertIn("--font-hand-cn", styles)

        en_block = re.search(r"\.profile-name\s*\{(?P<body>.*?)\n\}", styles, re.S)
        cn_block = re.search(r"\.profile-name-cn\s*\{(?P<body>.*?)\n\}", styles, re.S)
        self.assertIsNotNone(en_block)
        self.assertIsNotNone(cn_block)
        en_body = en_block.group("body")
        self.assertIn("var(--font-hand-en)", en_body)
        self.assertIn("display: block", en_body)
        self.assertIn("width: fit-content", en_body)
        self.assertIn("margin: 0 auto", en_body)
        self.assertIn("var(--font-hand-cn)", cn_block.group("body"))
        self.assertIn("Dancing Script", styles)
        self.assertNotIn("Allura", styles)
        self.assertIn("Zhi Mang Xing", styles)
        self.assertIn("STXingkai", styles)

    def test_google_fonts_load_without_blocking_first_render(self) -> None:
        base = BASE_HTML.read_text()

        self.assertIn('rel="preload"', base)
        self.assertIn('as="style"', base)
        self.assertIn("this.rel='stylesheet'", base)
        self.assertIn("<noscript>", base)
        blocking_head = re.sub(r"<noscript>.*?</noscript>", "", base, flags=re.S)
        self.assertNotIn('rel="stylesheet" href="https://fonts.googleapis.com', blocking_head)
