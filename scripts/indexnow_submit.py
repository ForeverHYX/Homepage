#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.routers.pages import INDEXNOW_KEY, SITE_URL


HOST = urllib.parse.urlparse(SITE_URL).netloc
INDEXNOW_ENDPOINT = "https://www.bing.com/indexnow"


def parse_sitemap_urls(xml_text: str) -> list[str]:
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(xml_text)
    urls = [
        loc.text.strip()
        for loc in root.findall(".//sm:loc", namespace)
        if loc.text and loc.text.strip().startswith(SITE_URL)
    ]
    return list(dict.fromkeys(urls))


def build_payload(urls: list[str]) -> dict[str, object]:
    return {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }


def fetch_sitemap(url: str = f"{SITE_URL}/sitemap.xml") -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "foreverhyx-indexnow-submit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def submit_payload(payload: dict[str, object], endpoint: str = INDEXNOW_ENDPOINT) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "foreverhyx-indexnow-submit/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        return error.code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit foreverhyx.top URLs to IndexNow.")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without submitting.")
    args = parser.parse_args()

    sitemap_xml = fetch_sitemap()
    urls = parse_sitemap_urls(sitemap_xml)
    if not urls:
        print("No URLs found in sitemap.", file=sys.stderr)
        return 1

    payload = build_payload(urls)
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    status, body = submit_payload(payload)
    print(f"IndexNow status: {status}")
    if body:
        print(body)
    return 0 if status in {200, 202} else 1


if __name__ == "__main__":
    raise SystemExit(main())
