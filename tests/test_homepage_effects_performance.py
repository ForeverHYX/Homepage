import re
import struct
from pathlib import Path
from unittest import TestCase

from app.education import parse_education_timeline


ROOT = Path(__file__).resolve().parents[1]
LIGHTFIELD_JS = ROOT / "static" / "js" / "effects" / "lightfield.js"
LIQUID_GLASS_JS = ROOT / "static" / "js" / "effects" / "liquid-glass.js"
SITE_HEADER_JS = ROOT / "static" / "js" / "components" / "site-header.js"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"
BASE_HTML = ROOT / "app" / "templates" / "base.html"
HOME_HTML = ROOT / "app" / "templates" / "pages" / "home.html"
GALLERY_HTML = ROOT / "app" / "templates" / "pages" / "gallery.html"
EDUCATION_PY = ROOT / "app" / "education.py"
FAVICON_32 = ROOT / "static" / "images" / "site" / "favicon-32.png"
FAVICON_64 = ROOT / "static" / "images" / "site" / "favicon-64.png"
ZJU_LOGO_52 = ROOT / "static" / "images" / "site" / "zju-logo-52.png"
ZJU_LOGO_104 = ROOT / "static" / "images" / "site" / "zju-logo-104.png"
ZJU_LOGO_156 = ROOT / "static" / "images" / "site" / "zju-logo-156.png"


class HomepageEffectsPerformanceTests(TestCase):
    def test_lightfield_uses_low_frequency_css_driven_motion(self) -> None:
        source = LIGHTFIELD_JS.read_text()
        styles = STYLES_CSS.read_text()

        self.assertIn("LIGHTFIELD_UPDATE_INTERVAL", source)
        self.assertNotIn("nextChangeAt", source)
        self.assertNotIn("requestAnimationFrame(frame)", source)
        self.assertIn("spot.renderedMotionDuration !== motionDuration", source)
        self.assertIn("spot.renderedOpacity !== opacity", source)
        self.assertIn("spot.renderedTransform !== transform", source)
        self.assertIn('src="/static/js/effects/lightfield.js?v=99"', BASE_HTML.read_text())

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
        self.assertIn("filter: blur(108px)", lightfield_before.group("body"))
        self.assertIn("opacity: 0.82", lightfield_before.group("body"))
        lightfield_after = next((body for body in lightfield_after_blocks if "background:" in body), "")
        self.assertIn("opacity: 0.68", lightfield_after)
        self.assertIn("blur(var(--spot-blur, 54px))", spot_block.group("body"))
        self.assertIn("opacity: var(--spot-opacity, 0.3)", spot_block.group("body"))
        self.assertIn("0 14px 28px rgba(99, 112, 158, 0.075)", card_block.group("body"))
        self.assertNotIn("0 24px 52px rgba(99, 112, 158, 0.135)", card_block.group("body"))

    def test_liquid_glass_throttles_pointer_target_sync(self) -> None:
        source = LIQUID_GLASS_JS.read_text()

        self.assertIn("POINTER_SYNC_INTERVAL", source)
        self.assertIn("targetSyncTimeoutId", source)

    def test_static_liquid_cards_do_not_load_unused_runtime(self) -> None:
        source = LIQUID_GLASS_JS.read_text()
        base = BASE_HTML.read_text()

        self.assertIn("card.classList.contains(\"ambient-liquid-card\")", source)
        self.assertNotIn("card.classList.contains(\"home-profile-card\") || card.classList.contains(\"home-news-card\")", source)
        self.assertNotIn('/static/js/effects/liquid-glass.js', base)
        self.assertNotIn('ambient-liquid-card', base)

    def test_runtime_liquid_filter_requires_explicit_opt_in(self) -> None:
        source = LIQUID_GLASS_JS.read_text()

        self.assertIn("runtimeLiquid", source)
        self.assertIn('const runtimeLiquid = card.classList.contains("ambient-liquid-card")', source)
        self.assertIn("const runtimeEnabled = enabled && state.runtimeLiquid", source)
        self.assertNotIn("const globalAmbient = navAmbient || card.classList.contains(\"ambient-liquid-card\")", source)

    def test_liquid_card_material_avoids_edge_blur_artifacts(self) -> None:
        styles = STYLES_CSS.read_text()

        card_edge = re.search(r"^\.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        dark_card_edge = re.search(r"^\[data-theme=\"dark\"\] \.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        nav_edge = re.search(r"^\.nav-island\.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        nav_warp = re.search(r"^\.nav-island \.nav-island-warp\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)

        self.assertIsNotNone(card_edge)
        self.assertIsNotNone(dark_card_edge)
        self.assertIsNotNone(nav_edge)
        self.assertIsNotNone(nav_warp)
        self.assertNotIn("blur(", card_edge.group("body"))
        self.assertNotIn("blur(", dark_card_edge.group("body"))
        self.assertNotIn("blur(", nav_edge.group("body"))
        self.assertNotIn("blur(", nav_warp.group("body"))
        self.assertNotIn("filter:", card_edge.group("body"))
        self.assertNotIn("filter:", dark_card_edge.group("body"))
        self.assertNotIn("filter:", nav_edge.group("body"))
        self.assertIn("backdrop-filter: none", nav_warp.group("body"))
        self.assertIn("-webkit-backdrop-filter: none", nav_warp.group("body"))

    def test_liquid_cards_frost_background_like_document_card(self) -> None:
        """Both the functional sidebar card and the document card must carry a
        real backdrop-filter blur so they read as one frosted-liquid material
        (the sidebar card is no longer a flat, un-blurred transparent sliver).
        The generic .card backdrop blur is overridden in favor of a card-type
        specific blur."""
        styles = STYLES_CSS.read_text()

        card_block = re.search(r"^\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        mobile_card_block = re.search(
            r"\.home-liquid-card,\n\s*\.nav-mobile-panel\s*\{(?P<body>.*?)\n\s*\}",
            styles,
            re.S,
        )
        nav_block = re.search(r"^\.nav-island\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)

        self.assertIsNotNone(card_block)
        self.assertIsNotNone(mobile_card_block)
        self.assertIsNotNone(nav_block)

        card_body = card_block.group("body")
        self.assertIn("backdrop-filter: blur(30px)", card_body)
        self.assertIn("-webkit-backdrop-filter: blur(30px)", card_body)
        self.assertNotIn("backdrop-filter: none", card_body)

        # Mobile breakpoint keeps a blur on the sidebar / mobile panel too.
        self.assertIn("backdrop-filter: blur(18px)", mobile_card_block.group("body"))
        self.assertIn("-webkit-backdrop-filter: blur(18px)", mobile_card_block.group("body"))

        nav_body = nav_block.group("body")
        self.assertIn("backdrop-filter: blur(22px)", nav_body)
        self.assertIn("-webkit-backdrop-filter: blur(22px)", nav_body)
        self.assertIn("saturate(168%)", nav_body)

    def test_liquid_card_hover_lifts_like_document_card(self) -> None:
        """The functional sidebar card must hover-lift the same way as the
        document .home-glass card (translateY(-4px) + a clean, deeper shadow)
        so the two materials read as one system. The old transform:none freeze
        is gone; no dirty halo (no oversized far blur) is allowed."""
        styles = STYLES_CSS.read_text()

        hover_block = re.search(r"^\.home-liquid-card:hover\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        self.assertIsNotNone(hover_block)
        hover_body = hover_block.group("body")

        self.assertIn("transform: translateY(-4px)", hover_body)
        # Clean shadow: a closer + a softer layer, both modest, no giant blur.
        self.assertIn("0 22px 48px rgba(73, 92, 138, 0.16)", hover_body)
        self.assertIn("0 10px 22px rgba(73, 92, 138, 0.08)", hover_body)
        # No mouse-follow sheen var mutations on hover.
        self.assertNotIn("var(--liquid-sheen-opacity)", hover_body)
        self.assertNotIn("var(--liquid-rim-opacity)", hover_body)

    def test_nav_island_has_modest_drop_shadow_without_dirty_halo(self) -> None:
        """The top nav pill must carry a modest bottom drop shadow at rest so
        it doesn't float flat against the background, but no oversized far blur
        (no dirty halo). It does not lift on hover (transform: none)."""
        styles = STYLES_CSS.read_text()

        nav_block = re.search(r"^\.nav-island\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        nav_hover = re.search(r"^\.nav-island\.home-liquid-card:hover\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)

        self.assertIsNotNone(nav_block)
        self.assertIsNotNone(nav_hover)
        nav_body = nav_block.group("body")
        nav_hover_body = nav_hover.group("body")

        # A soft grounded shadow, bright top catch-light, and darker lower rim
        # create depth without reintroducing the old oversized dirty halo.
        self.assertIn("0 12px 32px rgba(55, 65, 95, 0.12)", nav_body)
        self.assertIn("0 3px 8px rgba(55, 65, 95, 0.055)", nav_body)
        self.assertIn("inset 0 1px 0 var(--liquid-inner-highlight)", nav_body)
        self.assertIn("inset 0 -1px 0 rgba(51, 65, 85, 0.14)", nav_body)
        self.assertNotIn("0 24px 50px", nav_body)
        self.assertNotIn("0 24px 50px", nav_hover_body)
        # The pill does not lift.
        self.assertNotIn("translateY", nav_hover_body)

    def test_liquid_material_restores_crystalline_layering(self) -> None:
        styles = STYLES_CSS.read_text()
        base = BASE_HTML.read_text()

        card_block = re.search(r"^\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        warp_block = re.search(r"^\.home-liquid-warp\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        warp_before_blocks = re.findall(r"^\.home-liquid-warp::before\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        warp_after_blocks = re.findall(r"^\.home-liquid-warp::after\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        nav_block = re.search(r"^\.nav-island\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)

        self.assertIsNotNone(card_block)
        self.assertIsNotNone(warp_block)
        self.assertTrue(warp_before_blocks)
        self.assertTrue(warp_after_blocks)
        self.assertIsNotNone(nav_block)

        card_body = card_block.group("body")
        self.assertIn("--liquid-content-tint", card_body)
        self.assertIn("--liquid-inner-shadow", card_body)
        self.assertIn("inset 0 1px 0 var(--liquid-inner-highlight)", card_body)
        self.assertIn("href=\"/static/css/styles.css?v=151\"", base)

        warp_body = warp_block.group("body")
        self.assertIn("background-blend-mode: screen, overlay, normal", warp_body)
        self.assertIn("contain: paint", warp_body)
        self.assertIn("will-change: transform, opacity", warp_body)

        # Sheen layers now use fixed opacities (no var(--liquid-sheen-opacity)
        # / var(--liquid-rim-opacity)) so no highlight tracks the pointer.
        warp_before_body = next((body for body in warp_before_blocks if "mix-blend-mode: screen" in body), "")
        warp_after_body = next((body for body in warp_after_blocks if "mix-blend-mode: soft-light" in body), "")
        self.assertIn("mix-blend-mode: screen", warp_before_body)
        self.assertIn("mix-blend-mode: soft-light", warp_after_body)
        self.assertNotIn("var(--liquid-sheen-opacity)", warp_before_body)
        self.assertNotIn("var(--liquid-rim-opacity)", warp_after_body)
        self.assertIn("--liquid-clear-layer", nav_block.group("body"))

    def test_liquid_material_keeps_runtime_cost_low(self) -> None:
        source = LIQUID_GLASS_JS.read_text()
        styles = STYLES_CSS.read_text()
        warp_block = re.search(r"^\.home-liquid-warp\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        nav_warp = re.search(r"^\.nav-island \.nav-island-warp\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)

        self.assertIsNotNone(warp_block)
        self.assertIsNotNone(nav_warp)
        self.assertIn("POINTER_SYNC_INTERVAL = 80", source)
        self.assertNotIn("backdrop-filter: blur", warp_block.group("body"))
        self.assertNotIn("backdrop-filter: blur", nav_warp.group("body"))
        self.assertNotIn("state.focused || state.globalAmbient", source)

    def test_sidebar_cards_have_no_mouse_following_floating_spot(self) -> None:
        """The .home-liquid-card / ::before / ::after / .home-liquid-warp /
        ::before/::after layers must not USE any pointer-driven CSS variable
        (--liquid-light-x/y for the radial anchor, --liquid-glow for the
        opacity calc, --liquid-angle for the gradient angle, --liquid-sheen/
        rim-opacity for the sheen strength) in a property value, since
        liquid-glass.js keeps updating those on pointermove and produces a
        floating spot artefact. We strip CSS comments before matching so that
        explanatory comments mentioning these tokens do not trip the check."""
        styles = STYLES_CSS.read_text()
        styles_no_comments = re.sub(r"/\*.*?\*/", "", styles, flags=re.S)

        candidates = [
            (r"^\.home-liquid-card\s*\{(?P<body>.*?)\n\}", ".home-liquid-card"),
            (r"^\.home-liquid-card::before\s*\{(?P<body>.*?)\n\}", ".home-liquid-card::before"),
            (r"^\.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", ".home-liquid-card::after"),
            (r"^\.home-liquid-warp\s*\{(?P<body>.*?)\n\}", ".home-liquid-warp"),
            (r"^\.home-liquid-warp::before\s*\{(?P<body>.*?)\n\}", ".home-liquid-warp::before"),
            (r"^\.home-liquid-warp::after\s*\{(?P<body>.*?)\n\}", ".home-liquid-warp::after"),
            (r"^\[data-theme=\"dark\"\] \.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", "[data-theme=\"dark\"] .home-liquid-card::after"),
            (r"^\[data-theme=\"dark\"\] \.home-liquid-warp::before\s*\{(?P<body>.*?)\n\}", "[data-theme=\"dark\"] .home-liquid-warp::before"),
        ]

        forbidden = (
            "var(--liquid-light-x)",
            "var(--liquid-light-y)",
            "var(--liquid-glow)",
            "var(--liquid-angle)",
            "var(--liquid-sheen-opacity)",
            "var(--liquid-rim-opacity)",
        )

        for pattern, label in candidates:
            match = re.search(pattern, styles_no_comments, re.S | re.M)
            self.assertIsNotNone(match, f"missing rule for {label}")
            body = match.group("body")
            for token in forbidden:
                self.assertNotIn(
                    token,
                    body,
                    f"{label} still references {token}, which tracks the pointer",
                )

    def test_nav_island_layers_have_no_mouse_following_floating_spot(self) -> None:
        """Top island layers must also not USE any pointer-driven CSS variable
        in a property value so Edge does not paint a dirty halo around the
        pill and no highlight tracks the mouse. CSS comments are stripped
        before matching so explanatory comments do not trip the check."""
        styles = STYLES_CSS.read_text()
        styles_no_comments = re.sub(r"/\*.*?\*/", "", styles, flags=re.S)

        candidates = [
            (r"^\.nav-island\.home-liquid-card\s*\{(?P<body>.*?)\n\}", ".nav-island.home-liquid-card"),
            (r"^\.nav-island\.home-liquid-card::before\s*\{(?P<body>.*?)\n\}", ".nav-island.home-liquid-card::before"),
            (r"^\.nav-island\.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", ".nav-island.home-liquid-card::after"),
            (r"^\.nav-island \.nav-island-warp\s*\{(?P<body>.*?)\n\}", ".nav-island .nav-island-warp"),
            (r"^\.nav-island \.home-liquid-warp::before\s*\{(?P<body>.*?)\n\}", ".nav-island .home-liquid-warp::before"),
            (r"^\.nav-island \.home-liquid-warp::after\s*\{(?P<body>.*?)\n\}", ".nav-island .home-liquid-warp::after"),
            (r"^\[data-theme=\"dark\"\] \.nav-island\.home-liquid-card::after\s*\{(?P<body>.*?)\n\}", "[data-theme=\"dark\"] .nav-island.home-liquid-card::after"),
        ]

        forbidden = (
            "var(--liquid-light-x)",
            "var(--liquid-light-y)",
            "var(--liquid-glow)",
            "var(--liquid-angle)",
            "var(--liquid-sheen-opacity)",
            "var(--liquid-rim-opacity)",
        )

        for pattern, label in candidates:
            match = re.search(pattern, styles_no_comments, re.S | re.M)
            self.assertIsNotNone(match, f"missing rule for {label}")
            body = match.group("body")
            for token in forbidden:
                self.assertNotIn(token, body, f"{label} still tracks {token}")

    def test_functional_and_doc_cards_share_unified_material_tokens(self) -> None:
        """Both the sidebar functional card (.home-liquid-card) and the document
        card (.home-content / .home-glass) must draw from the unified
        --home-material-* token family so they read as one frosted-liquid
        system instead of two unrelated materials."""
        styles = STYLES_CSS.read_text()
        base = BASE_HTML.read_text()

        # Root exposes the shared material tokens.
        root_block = re.search(r"^:root\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        self.assertIsNotNone(root_block)
        root_body = root_block.group("body")
        for token in (
            "--home-material-face-top",
            "--home-material-face-mid",
            "--home-material-face-bottom",
            "--home-material-tint",
            "--home-material-edge",
            "--home-material-inner-top",
            "--home-material-inner-bottom",
            "--home-material-blur",
        ):
            self.assertIn(token, root_body, f":root must declare {token}")

        # Functional card references the shared tokens instead of hard-coded alphas.
        card_block = re.search(r"^\.home-liquid-card\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        self.assertIsNotNone(card_block)
        card_body = card_block.group("body")
        self.assertIn("var(--home-material-tint)", card_body)
        self.assertIn("var(--home-material-inner-top)", card_body)
        self.assertIn("var(--home-material-inner-bottom)", card_body)
        self.assertIn("var(--home-material-edge)", card_body)
        self.assertIn("var(--home-material-face-top)", card_body)
        self.assertIn("var(--home-material-face-mid)", card_body)
        self.assertIn("var(--home-material-face-bottom)", card_body)

        # Document card references the shared tokens too.
        content_block = re.search(r"^\.home-content\s*\{(?P<body>.*?)\n\}", styles, re.S | re.M)
        self.assertIsNotNone(content_block)
        content_body = content_block.group("body")
        self.assertIn("var(--home-material-face-top)", content_body)
        self.assertIn("var(--home-material-face-mid)", content_body)
        self.assertIn("var(--home-material-face-bottom)", content_body)
        self.assertIn("var(--home-material-shadow)", content_body)

        # Functional card sits at higher transparency (lower face-top alpha)
        # than the document card so the doc area stays steadier for text.
        card_face_alpha = re.search(
            r"--home-material-face-top:\s*rgba\(255, 255, 255, ([\d.]+)\)",
            card_body,
        )
        content_face_alpha = re.search(
            r"--home-material-face-top:\s*rgba\(255, 255, 255, ([\d.]+)\)",
            content_body,
        )
        self.assertIsNotNone(card_face_alpha)
        self.assertIsNotNone(content_face_alpha)
        self.assertLess(
            float(card_face_alpha.group(1)),
            float(content_face_alpha.group(1)),
            "functional card face should be more transparent (lower alpha) than doc card",
        )

        # Cache-buster bumps when CSS material changes so clients refetch it.
        self.assertIn('href="/static/css/styles.css?v=151"', base)

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
        self.assertEqual(
            base.count('rel="preload" as="style" href="https://fonts.googleapis.com'),
            1,
        )
        self.assertIn("Dancing+Script:wght@500", base)
        self.assertIn("JetBrains+Mono:wght@400;500", base)
        self.assertNotIn("Noto+Serif+SC", base)
        blocking_head = re.sub(r"<noscript>.*?</noscript>", "", base, flags=re.S)
        self.assertNotIn('rel="stylesheet" href="https://fonts.googleapis.com', blocking_head)

    def test_favicon_uses_right_sized_static_assets(self) -> None:
        base = BASE_HTML.read_text()

        self.assertIn('/static/images/site/favicon-32.png?v=1', base)
        self.assertIn('/static/images/site/favicon-64.png?v=1', base)
        self.assertNotIn('/uploads/favicon.png', base)

        for path, expected_size in ((FAVICON_32, 32), (FAVICON_64, 64)):
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (expected_size, expected_size))

    def test_page_images_reserve_layout_and_decode_asynchronously(self) -> None:
        home = HOME_HTML.read_text()
        gallery = GALLERY_HTML.read_text()
        education = EDUCATION_PY.read_text()

        self.assertIn('width="240" height="240" decoding="async"', home)
        self.assertEqual(gallery.count('loading="lazy" decoding="async"'), 2)
        self.assertIn('width="52" height="52" decoding="async"', education)

    def test_education_logo_uses_density_matched_static_assets(self) -> None:
        html = parse_education_timeline(
            "- **Zhejiang University** | 2023 - Present\n"
            "  *Bachelor of Engineering*\n"
            "  ![ZJU](/uploads/zju.png)"
        )

        self.assertIn('/static/images/site/zju-logo-52.png?v=1', html)
        self.assertIn('/static/images/site/zju-logo-104.png?v=1 2x', html)
        self.assertIn('/static/images/site/zju-logo-156.png?v=1 3x', html)
        self.assertNotIn('src="/uploads/zju.png"', html)
        self.assertLess(html.index(" srcset="), html.index(" src="))

        for path, expected_size in (
            (ZJU_LOGO_52, 52),
            (ZJU_LOGO_104, 104),
            (ZJU_LOGO_156, 156),
        ):
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (expected_size, expected_size))

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
        self.assertIn('href="/static/css/styles.css?v=151"', base)

    def test_inline_code_avoids_backdrop_filter_line_artifacts(self) -> None:
        styles = STYLES_CSS.read_text()

        inline_code = re.search(r"\.prose code\s*\{(?P<body>[^}]*)\}", styles, re.S)

        self.assertIsNotNone(inline_code)
        inline_code_body = inline_code.group("body")
        self.assertNotIn("backdrop-filter", inline_code_body)
        self.assertIn("box-decoration-break: clone", inline_code_body)
        self.assertIn("-webkit-box-decoration-break: clone", inline_code_body)

    def test_daily_cards_avoid_nested_backdrop_repaint_cost(self) -> None:
        styles = STYLES_CSS.read_text()

        daily_card = re.search(r"\.daily-card\.home-glass\s*\{(?P<body>.*?)\n\}", styles, re.S)
        daily_action = re.search(r"\.daily-action-button\s*\{(?P<body>.*?)\n\}", styles, re.S)

        self.assertIsNotNone(daily_card)
        self.assertIsNotNone(daily_action)
        self.assertIn("--home-glass-blur: 18px", daily_card.group("body"))
        self.assertIn("backdrop-filter: none", daily_action.group("body"))
        self.assertIn("-webkit-backdrop-filter: none", daily_action.group("body"))
        self.assertNotIn("backdrop-filter: blur", daily_action.group("body"))

    def test_news_modal_uses_dedicated_layout_instead_of_generic_lightbox_card(self) -> None:
        source = SITE_HEADER_JS.read_text()
        styles = STYLES_CSS.read_text()

        self.assertIn('fetch("/api/site/news"', source)
        self.assertNotIn('fetch("/api/site/home"', source)
        self.assertIn('src="/static/js/components/site-header.js?v=101"', BASE_HTML.read_text())
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

    def test_navigation_details_cover_keyboard_touch_and_mobile_search(self) -> None:
        source = SITE_HEADER_JS.read_text()
        styles = STYLES_CSS.read_text()

        self.assertIn('link.setAttribute("aria-current", "page")', source)
        self.assertIn('if (!intendedPath || intendedPath === "/upload")', source)
        self.assertIn("searchTrigger.inert = hidden", source)
        self.assertIn("navMobilePanel.inert = true", source)
        self.assertIn('window.matchMedia("(max-width: 820px)")', source)
        self.assertIn("(useIsland ? navIsland : input).getBoundingClientRect()", source)
        self.assertIn("window.visualViewport", source)
        self.assertIn("touch-action: manipulation", styles)
        self.assertIn("transform: scale(0.97)", styles)
        self.assertIn(".search-bar-container:focus-within", styles)

    def test_homepage_honors_apple_accessibility_preferences(self) -> None:
        source = SITE_HEADER_JS.read_text()
        liquid_source = LIQUID_GLASS_JS.read_text()
        styles = STYLES_CSS.read_text()

        self.assertIn('card.setAttribute("role", "dialog")', source)
        self.assertIn('card.setAttribute("aria-modal", "true")', source)
        self.assertIn("prefers-reduced-transparency: reduce", styles)
        self.assertIn("prefers-contrast: more", styles)
        self.assertIn("forced-colors: active", styles)
        self.assertIn(
            "@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))",
            styles,
        )
        self.assertIn(".nav-mobile-panel .home-liquid-warp", styles)
        self.assertIn("(hover: hover) and (pointer: fine)", liquid_source)

    def test_floating_navigation_keeps_sticky_positioning(self) -> None:
        styles = STYLES_CSS.read_text()

        self.assertIn("@supports (overflow: clip)", styles)
        self.assertIn("html, body { overflow-x: clip; }", styles)
