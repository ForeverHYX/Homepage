import re
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
LIGHTFIELD_JS = ROOT / "static" / "js" / "effects" / "lightfield.js"
LIQUID_GLASS_JS = ROOT / "static" / "js" / "effects" / "liquid-glass.js"
SITE_HEADER_JS = ROOT / "static" / "js" / "components" / "site-header.js"
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

    def test_lightfield_and_card_shadows_stay_subtle(self) -> None:
        styles = STYLES_CSS.read_text()

        lightfield_block = re.search(r"\.home-lightfield\s*\{(?P<body>.*?)\n\}", styles, re.S)
        lightfield_before = re.search(r"\.home-lightfield::before\s*\{(?P<body>.*?)\n\}", styles, re.S)
        lightfield_after_blocks = re.findall(r"\.home-lightfield::after\s*\{(?P<body>.*?)\n\}", styles, re.S)
        spot_block = re.search(r"\.home-lightspot\s*\{(?P<body>.*?)\n\}", styles, re.S)
        card_block = re.search(r"^\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)

        self.assertIsNotNone(lightfield_block)
        self.assertIsNotNone(lightfield_before)
        self.assertTrue(lightfield_after_blocks)
        self.assertIsNotNone(spot_block)
        self.assertIsNotNone(card_block)

        self.assertIn("contain: paint", lightfield_block.group("body"))
        self.assertIn("filter: blur(86px)", lightfield_before.group("body"))
        self.assertIn("opacity: 0.42", lightfield_before.group("body"))
        lightfield_after = next((body for body in lightfield_after_blocks if "background:" in body), "")
        self.assertIn("opacity: 0.34", lightfield_after)
        self.assertIn("blur(calc(var(--spot-blur, 54px) * 0.72))", spot_block.group("body"))
        self.assertIn("opacity: calc(var(--spot-opacity, 0.3) * 0.32)", spot_block.group("body"))
        self.assertIn("0 14px 28px rgba(99, 112, 158, 0.075)", card_block.group("body"))
        self.assertNotIn("0 24px 52px rgba(99, 112, 158, 0.135)", card_block.group("body"))

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

    def test_education_logo_overrides_generic_prose_image_style(self) -> None:
        styles = STYLES_CSS.read_text()
        base = BASE_HTML.read_text()

        prose_img = re.search(r"\.prose img\s*\{(?P<body>.*?)\n\}", styles, re.S)
        edu_logo = re.search(r"\.prose \.edu-logo\s*\{(?P<body>.*?)\n\}", styles, re.S)

        self.assertIsNotNone(prose_img)
        self.assertIsNotNone(edu_logo)
        self.assertLess(prose_img.start(), edu_logo.start())

        edu_logo_body = edu_logo.group("body")
        self.assertIn("height: 52px", edu_logo_body)
        self.assertIn("width: auto", edu_logo_body)
        self.assertIn("max-width: none", edu_logo_body)
        self.assertIn("margin: 0", edu_logo_body)
        self.assertIn("border-radius: 0", edu_logo_body)
        self.assertIn('href="/static/css/styles.css?v=127"', base)

    def test_inline_code_avoids_backdrop_filter_line_artifacts(self) -> None:
        styles = STYLES_CSS.read_text()

        inline_code = re.search(r"\.prose code\s*\{(?P<body>[^}]*)\}", styles, re.S)

        self.assertIsNotNone(inline_code)
        inline_code_body = inline_code.group("body")
        self.assertNotIn("backdrop-filter", inline_code_body)
        self.assertIn("box-decoration-break: clone", inline_code_body)
        self.assertIn("-webkit-box-decoration-break: clone", inline_code_body)

    def test_news_modal_uses_dedicated_layout_instead_of_generic_lightbox_card(self) -> None:
        source = SITE_HEADER_JS.read_text()
        styles = STYLES_CSS.read_text()

        self.assertIn('overlay.className = "news-modal-overlay"', source)
        self.assertIn('card.className = "news-modal-card"', source)
        self.assertIn('wrap.className = "home-news-modal-content"', source)
        self.assertNotIn('card.className = "card home-liquid-card lightbox-content"', source)

        self.assertIn(".news-modal-overlay", styles)
        self.assertIn(".news-modal-card", styles)
        self.assertIn(".home-news-modal-content", styles)
        modal_card = re.search(r"\.news-modal-card\s*\{(?P<body>.*?)\n\}", styles, re.S)
        self.assertIsNotNone(modal_card)
        self.assertIn("overflow: auto", modal_card.group("body"))
        self.assertIn("max-height: min(82vh, 760px)", modal_card.group("body"))
