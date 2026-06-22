from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]


class DeploymentHygieneTests(TestCase):
    def test_legacy_frontend_source_is_not_kept_in_runtime_repo(self) -> None:
        self.assertFalse((ROOT / "frontend").exists())

    def test_saved_systemd_unit_uses_single_worker_without_app_access_log(self) -> None:
        service = (ROOT / "deploy" / "foreverhyx-homepage.service").read_text(encoding="utf-8")

        self.assertIn("--workers 1", service)
        self.assertNotIn("--access-logfile", service)
        self.assertNotIn("homepage_access.log", service)

    def test_saved_nginx_config_disables_homepage_access_log(self) -> None:
        nginx = (ROOT / "deploy" / "nginx-foreverhyx.conf").read_text(encoding="utf-8")

        self.assertIn("client_max_body_size 100M;\n    access_log off;", nginx)
        self.assertNotIn("/_next/", nginx)
