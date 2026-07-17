"""Run repeatable Lighthouse profiles and report median category scores."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
METRICS = (
    "first-contentful-paint",
    "largest-contentful-paint",
    "cumulative-layout-shift",
    "total-blocking-time",
    "speed-index",
)


def _discover_chrome(explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path.expanduser().resolve()
    configured = os.getenv("CHROME_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        executable = shutil.which(command)
        if executable:
            return Path(executable).resolve()
    mac_candidates = (
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    )
    for candidate in mac_candidates:
        if candidate.is_file():
            return candidate
    agent_browser_candidates = sorted(
        (Path.home() / ".agent-browser" / "browsers").glob(
            "chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
        reverse=True,
    )
    return agent_browser_candidates[0] if agent_browser_candidates else None


def _run_lighthouse(
    url: str,
    device: str,
    output_path: Path,
    chrome_path: Path | None,
) -> dict:
    command = [
        "npx",
        "--yes",
        "lighthouse",
        url,
        "--quiet",
        "--output=json",
        f"--output-path={output_path}",
        "--only-categories=" + ",".join(CATEGORIES),
        "--chrome-flags=--headless=new --no-sandbox",
    ]
    if device == "desktop":
        command.append("--preset=desktop")
    environment = os.environ.copy()
    if chrome_path is not None:
        environment["CHROME_PATH"] = str(chrome_path)
    result = subprocess.run(command, check=False, env=environment)
    if result.returncode:
        raise SystemExit(f"Lighthouse failed for {device}: exit {result.returncode}")
    return json.loads(output_path.read_text(encoding="utf-8"))


def _summary(reports: list[dict]) -> dict:
    summary: dict[str, object] = {
        "categories": {},
        "metrics": {},
    }
    for category in CATEGORIES:
        scores = [report["categories"][category]["score"] * 100 for report in reports]
        summary["categories"][category] = round(statistics.median(scores), 1)
    for metric in METRICS:
        values = [report["audits"][metric].get("numericValue", 0) for report in reports]
        median_value = statistics.median(values)
        representative = min(
            reports,
            key=lambda report: abs(report["audits"][metric].get("numericValue", 0) - median_value),
        )
        summary["metrics"][metric] = {
            "median_numeric_value": median_value,
            "median_display_value": representative["audits"][metric].get(
                "displayValue",
                "",
            ),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--chrome-path", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    parsed_url = urlparse(args.url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        parser.error("url must be an absolute http(s) URL")
    if shutil.which("npx") is None:
        raise SystemExit("npx is required; install current Node.js before profiling")
    chrome_path = _discover_chrome(args.chrome_path)
    if chrome_path is not None and not chrome_path.is_file():
        raise SystemExit(f"Chrome executable does not exist: {chrome_path}")
    if chrome_path is not None:
        print(f"Chrome: {chrome_path}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or Path("artifacts") / "lighthouse" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    combined = {
        "url": args.url,
        "runs": args.runs,
        "generated_at": timestamp,
        "devices": {},
    }
    for device in ("mobile", "desktop"):
        reports: list[dict] = []
        for run_number in range(1, args.runs + 1):
            output_path = output_dir / f"{device}-{run_number}.json"
            print(f"Profiling {device} run {run_number}/{args.runs} ...", flush=True)
            reports.append(_run_lighthouse(args.url, device, output_path, chrome_path))
        combined["devices"][device] = _summary(reports)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("\nMedian Lighthouse scores")
    for device, device_summary in combined["devices"].items():
        scores = device_summary["categories"]
        rendered = ", ".join(f"{name}={score:g}" for name, score in scores.items())
        print(f"- {device}: {rendered}")
    print(f"Reports: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
