import json
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app import auth


class AuthenticationTests(TestCase):
    def test_missing_password_hash_never_authenticates(self) -> None:
        with (
            patch.object(auth, "UPLOAD_USERNAME", "admin"),
            patch.object(
                auth,
                "UPLOAD_PASSWORD_HASH",
                "",
            ),
        ):
            self.assertFalse(auth.verify_credentials("admin", "anything"))

    def test_password_whitespace_is_not_silently_discarded(self) -> None:
        password_hash = auth.pwd_context.hash(" secret with spaces ")
        with (
            patch.object(auth, "UPLOAD_USERNAME", "admin"),
            patch.object(auth, "UPLOAD_PASSWORD_HASH", password_hash),
        ):
            self.assertTrue(auth.verify_credentials("admin", " secret with spaces "))
            self.assertFalse(auth.verify_credentials("admin", "secret with spaces"))

    def test_configuration_has_no_plaintext_password_fallback(self) -> None:
        config_source = (Path(auth.__file__).with_name("config.py")).read_text(encoding="utf-8")
        env_example = (Path(auth.__file__).parents[1] / ".env.example").read_text(encoding="utf-8")

        self.assertNotIn('os.getenv("HOMEPAGE_UPLOAD_PASS",', config_source)
        self.assertNotIn("HOMEPAGE_UPLOAD_PASS=", env_example)

    def test_session_file_is_private_and_atomically_replaceable(self) -> None:
        with TemporaryDirectory() as temp_dir:
            session_file = Path(temp_dir) / ".sessions.json"
            with patch.object(auth, "SESSION_FILE", session_file):
                auth._save_sessions({"token": 4_102_444_800.0})
                first = json.loads(session_file.read_text(encoding="utf-8"))
                auth._save_sessions({"next": 4_102_444_801.0})
                second = json.loads(session_file.read_text(encoding="utf-8"))

            self.assertEqual(first, {"token": 4_102_444_800.0})
            self.assertEqual(second, {"next": 4_102_444_801.0})
            self.assertEqual(stat.S_IMODE(session_file.stat().st_mode), 0o600)
            self.assertEqual(list(session_file.parent.glob(".*.tmp")), [])
