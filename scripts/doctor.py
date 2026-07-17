"""Check whether a homepage checkout is ready to run or deploy."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_RUNTIME_MODULES = (
    "fastapi",
    "gunicorn",
    "jinja2",
    "markdown",
    "multipart",
    "passlib",
    "PIL",
    "slowapi",
    "uvicorn",
)
REQUIRED_PATHS = (
    ROOT / "app" / "templates" / "base.html",
    ROOT / "content",
    ROOT / "uploads",
    ROOT / "static" / "asset-manifest.json",
    ROOT / "static" / "css" / "styles.min.css",
    ROOT / "static" / "js" / "components" / "site-header.min.js",
)
BCRYPT_PATTERN = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def ok(self, message: str) -> None:
        print(f"[ok]   {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[warn] {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"[fail] {message}")


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _check_python(report: Report) -> None:
    if sys.version_info >= (3, 11):
        report.ok(f"Python {sys.version.split()[0]} (minimum 3.11)")
    else:
        report.fail(f"Python 3.11+ is required; found {sys.version.split()[0]}")


def _check_imports(report: Report) -> None:
    missing: list[str] = []
    for module in REQUIRED_RUNTIME_MODULES:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        report.fail(f"missing runtime modules: {', '.join(missing)}")
    else:
        report.ok("runtime dependencies import successfully")


def _check_paths(report: Report) -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_PATHS if not path.exists()]
    if missing:
        report.fail(f"missing required paths: {', '.join(missing)}")
    else:
        report.ok("required application and generated files exist")
    for directory in (ROOT / "content", ROOT / "uploads"):
        if directory.is_dir() and not os.access(directory, os.R_OK | os.W_OK):
            report.fail(f"{directory.relative_to(ROOT)} must be readable and writable")


def _check_manifest(report: Report) -> None:
    manifest_path = ROOT / "static" / "asset-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.fail(f"invalid asset manifest: {exc}")
        return
    if not isinstance(manifest, dict) or not manifest:
        report.fail("asset manifest must be a non-empty JSON object")
        return
    missing = [relative for relative in manifest if not (ROOT / "static" / relative).is_file()]
    if missing:
        report.fail(f"manifest points to missing files: {', '.join(missing[:5])}")
    else:
        report.ok(f"asset manifest resolves {len(manifest)} files")


def _check_environment(report: Report, *, production: bool) -> None:
    env_path = ROOT / ".env"
    values = _read_env(env_path)
    if not values:
        message = ".env is absent; public pages work, but upload login stays disabled"
        report.fail(message) if production else report.warn(message)
        return

    password_hash = values.get("HOMEPAGE_UPLOAD_PASS_HASH", "")
    hash_is_valid = bool(BCRYPT_PATTERN.fullmatch(password_hash)) and "xxxx" not in password_hash
    if hash_is_valid:
        report.ok("upload password is configured as a bcrypt hash")
    else:
        message = "HOMEPAGE_UPLOAD_PASS_HASH is missing or still a placeholder"
        report.fail(message) if production else report.warn(message)

    cookie_secure = values.get("HOMEPAGE_COOKIE_SECURE", "true").casefold()
    if production and cookie_secure not in {"1", "true", "yes", "on"}:
        report.fail("production requires HOMEPAGE_COOKIE_SECURE=true")
    else:
        report.ok(f"secure-cookie setting is {cookie_secure or 'true'}")

    session_file = Path(values.get("HOMEPAGE_SESSION_FILE", ROOT / ".sessions.json"))
    if not session_file.is_absolute():
        session_file = ROOT / session_file
    if session_file.exists() and (session_file.stat().st_mode & 0o077):
        report.fail(f"session file permissions are too broad: {session_file}")
    elif session_file.exists():
        report.ok("session file is owner-only")

    share_file = Path(
        os.getenv(
            "HOMEPAGE_SHARE_LINK_FILE",
            values.get("HOMEPAGE_SHARE_LINK_FILE", ROOT / ".share-links.json"),
        )
    )
    if not share_file.is_absolute():
        share_file = ROOT / share_file
    if share_file.exists() and (share_file.stat().st_mode & 0o077):
        report.fail(f"share-link file permissions are too broad: {share_file}")
    elif share_file.exists():
        report.ok("share-link file is owner-only")
    else:
        report.ok("share-link file will be created owner-only on first use")


def _check_build(report: Report) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_frontend.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stdout + result.stderr).strip()
        report.fail(f"generated frontend assets are stale: {detail}")
    else:
        report.ok("frontend build is deterministic and current")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--production",
        action="store_true",
        help="treat missing credentials and insecure cookies as failures",
    )
    parser.add_argument(
        "--check-build",
        action="store_true",
        help="rebuild in check mode (requires requirements-dev.txt)",
    )
    args = parser.parse_args()

    report = Report()
    _check_python(report)
    _check_imports(report)
    _check_paths(report)
    _check_manifest(report)
    _check_environment(report, production=args.production)
    if args.check_build:
        _check_build(report)

    print(
        f"\nDoctor finished: {len(report.failures)} failure(s), {len(report.warnings)} warning(s)."
    )
    raise SystemExit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
