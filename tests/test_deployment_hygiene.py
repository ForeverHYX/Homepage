import runpy
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class DeploymentHygieneTests(TestCase):
    def test_legacy_frontend_source_is_not_kept_in_runtime_repo(self) -> None:
        self.assertFalse((ROOT / "frontend").exists())

    def test_saved_systemd_unit_uses_single_worker_without_app_access_log(self) -> None:
        service = (ROOT / "deploy" / "foreverhyx-homepage.service").read_text(encoding="utf-8")

        self.assertIn("--workers 1", service)
        self.assertIn("ExecReload=/bin/kill -s HUP $MAINPID", service)
        self.assertNotIn("--access-logfile", service)
        self.assertNotIn("homepage_access.log", service)

    def test_saved_nginx_config_disables_homepage_access_log(self) -> None:
        nginx = (ROOT / "deploy" / "nginx-foreverhyx.conf").read_text(encoding="utf-8")

        self.assertIn("client_max_body_size 100M;\n    access_log off;", nginx)
        self.assertNotIn("/_next/", nginx)

    def test_saved_nginx_config_canonicalizes_https_www_with_permanent_redirect(self) -> None:
        nginx = (ROOT / "deploy" / "nginx-foreverhyx.conf").read_text(encoding="utf-8")

        self.assertIn("server_name www.foreverhyx.top;", nginx)
        self.assertIn("return 308 https://foreverhyx.top$request_uri;", nginx)
        self.assertIn("server_name foreverhyx.top;", nginx)
        self.assertEqual(nginx.count("server_name foreverhyx.top www.foreverhyx.top;"), 1)

    def test_saved_nginx_config_rate_limits_only_proxied_requests(self) -> None:
        nginx = (ROOT / "deploy" / "nginx-foreverhyx.conf").read_text(encoding="utf-8")

        self.assertIn(
            "limit_req_zone $binary_remote_addr zone=homepage_html:10m rate=5r/s;",
            nginx,
        )
        self.assertIn("limit_req zone=homepage_html burst=20 nodelay;", nginx)
        self.assertGreaterEqual(nginx.count("limit_req_status 429;"), 2)

        static_location = nginx.split("location /static/ {", 1)[1].split("}", 1)[0]
        uploads_location = nginx.split("location /uploads/ {", 1)[1].split("}", 1)[0]
        self.assertNotIn("limit_req", static_location)
        self.assertNotIn("limit_req", uploads_location)

    def test_production_css_is_reproducibly_minified_without_reordering(self) -> None:
        script = ROOT / "scripts" / "build_static_css.py"
        source = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
        production = (ROOT / "static" / "css" / "styles.min.css").read_text(encoding="utf-8")
        build_helpers = runpy.run_path(str(script))
        minify_css = build_helpers["minify_css"]
        strip_comments = build_helpers["strip_css_comments"]

        self.assertEqual(production, minify_css(source))
        self.assertLess(len(production), len(strip_comments(source)))
        self.assertEqual(
            strip_comments('a::before { content: "/* visible */"; } /* remove */'),
            'a::before { content: "/* visible */"; } ',
        )
        self.assertEqual(
            minify_css('a::before {\n  content: "a  b /* visible */";\n}\n'),
            'a::before { content: "a  b /* visible */"; }\n',
        )
        self.assertIn("calc(100% - 2px)", minify_css("a { width: calc(100% - 2px); }"))
        self.assertIn("article a", minify_css("article\n  a { color: blue; }"))
