from __future__ import annotations

import copy
import json
import math
import os
import re
import tempfile
import threading
import time
from collections import Counter, OrderedDict
from itertools import combinations
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, TypeVar
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.daily_articles import daily_article_slug


DEFAULT_DAILY_BASE_URL = "https://foreverhyx.github.io/agentic-arch-paper-recommender"
REQUEST_TIMEOUT = 12
REMOTE_CACHE_TTL_SECONDS = int(os.getenv("HOMEPAGE_DAILY_REMOTE_CACHE_SECONDS", "900"))
FEEDBACK_CONFIG_CACHE_TTL_SECONDS = int(
    os.getenv("HOMEPAGE_DAILY_FEEDBACK_CONFIG_CACHE_SECONDS", "3600")
)
FAVORITES_CACHE_TTL_SECONDS = int(os.getenv("HOMEPAGE_DAILY_FAVORITES_CACHE_SECONDS", "7200"))
DAILY_RUN_READY_HOUR_UTC = int(os.getenv("HOMEPAGE_DAILY_RUN_READY_HOUR_UTC", "4"))
DISPLAY_AUTHOR_LIMIT = 4
DISPLAY_KEYWORD_LIMIT = 10
MAX_FILTER_KEYWORDS = 10
FILTER_KEYWORD_ROW_WIDTH = 252
FILTER_KEYWORD_GAP = 8
PROFILE_RADAR_CENTER = 100
PROFILE_RADAR_RADIUS = 58
PROFILE_RADAR_LABEL_RADIUS = 80
PROFILE_RADAR_AXIS_LIMIT = 8
PROFILE_RADAR_LABEL_MAX_LENGTH = 18
SECTION_KEYWORDS = {
    "agentic_architecture": ["Agentic", "Architecture"],
    "full_stack_codesign": ["Codesign", "Compiler", "Runtime"],
    "microarchitecture_simulators": ["Microarchitecture", "Simulation"],
    "hpc_cross_over": ["HPC", "Compiler", "Runtime"],
    "exploratory": [],
}
KEYWORD_LABELS = {
    "accelerator": "Accelerator",
    "accelerators": "Accelerator",
    "ai": "AI",
    "agent": "Agent",
    "agents": "Agents",
    "agentic": "Agentic",
    "amd": "AMD",
    "architecture": "Architecture",
    "architectures": "Architecture",
    "autonomous": "Autonomy",
    "cache": "Cache",
    "caches": "Cache",
    "compiler": "Compiler",
    "compilers": "Compiler",
    "codesign": "Codesign",
    "co-design": "Codesign",
    "cuda": "CUDA",
    "cpu": "CPU",
    "cpus": "CPU",
    "cognition": "Cognition",
    "communication": "Communication",
    "communications": "Communication",
    "design": "Design",
    "distributed": "Distributed",
    "gem5": "Gem5",
    "gpu": "GPU",
    "gpus": "GPU",
    "hardware": "Hardware",
    "hpc": "HPC",
    "inference": "Inference",
    "interconnect": "Interconnect",
    "kv": "Cache",
    "llm": "LLM",
    "llms": "LLM",
    "maestro": "Maestro",
    "microarchitecture": "Microarchitecture",
    "network": "Network",
    "networks": "Network",
    "neural": "Neural",
    "openmp": "OpenMP",
    "pytorch": "PyTorch",
    "rocm": "ROCm",
    "runtime": "Runtime",
    "runtimes": "Runtime",
    "scheduler": "Scheduling",
    "schedulers": "Scheduling",
    "scheduling": "Scheduling",
    "search": "Search",
    "simulator": "Simulation",
    "simulators": "Simulation",
    "sparse": "Sparsity",
    "sparsity": "Sparsity",
    "tree": "Search",
    "vllm": "VLLM",
    "workload": "Workload",
    "workloads": "Workload",
}
TITLE_KEYWORD_ALLOWLIST = {
    "Accelerator",
    "Agent",
    "Agents",
    "Agentic",
    "AI",
    "Architecture",
    "Autonomy",
    "Cache",
    "CUDA",
    "Cognition",
    "Codesign",
    "Communication",
    "Compiler",
    "Data",
    "Design",
    "Distributed",
    "Gem5",
    "GPU",
    "Hardware",
    "HPC",
    "Inference",
    "Interconnect",
    "LLM",
    "Maestro",
    "Microarchitecture",
    "Network",
    "Neural",
    "OpenMP",
    "Parallelism",
    "PyTorch",
    "ROCm",
    "Runtime",
    "Scheduling",
    "Search",
    "Serving",
    "Simulation",
    "Sparsity",
    "VLLM",
    "Workload",
}
KEYWORD_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "based",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "layer",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "x",
    "arxiv",
    "aware",
    "cross",
    "driven",
    "fast",
    "github",
    "modeling",
    "multi",
    "paper",
    "papers",
    "star",
    "stars",
    "system",
    "systems",
    "today",
}
DEFAULT_DAILY_CACHE_PATH = Path(
    os.getenv(
        "HOMEPAGE_DAILY_CACHE_FILE",
        Path(__file__).resolve().parent.parent / "content" / "daily" / "recommendations.json",
    )
)
DEFAULT_FEEDBACK_CONFIG_CACHE_PATH = Path(
    os.getenv(
        "HOMEPAGE_DAILY_FEEDBACK_CONFIG_CACHE_FILE",
        DEFAULT_DAILY_CACHE_PATH.with_name("feedback-config.json"),
    )
)
DEFAULT_DAILY_ARCHIVE_DIR = Path(
    os.getenv(
        "HOMEPAGE_DAILY_ARCHIVE_DIR",
        DEFAULT_DAILY_CACHE_PATH.parent / "archive",
    )
)
DEFAULT_FAVORITES_REPO_TREE_URL = os.getenv(
    "HOMEPAGE_DAILY_FAVORITES_TREE_URL",
    "https://api.github.com/repos/ForeverHYX/daily-recommender-paper-favorites/git/trees/main?recursive=1",
)
DEFAULT_FAVORITES_RAW_BASE_URL = os.getenv(
    "HOMEPAGE_DAILY_FAVORITES_RAW_BASE_URL",
    "https://raw.githubusercontent.com/ForeverHYX/daily-recommender-paper-favorites/main",
)
DEFAULT_DAILY_FAVORITES_CACHE_PATH = Path(
    os.getenv(
        "HOMEPAGE_DAILY_FAVORITES_CACHE_FILE",
        DEFAULT_DAILY_CACHE_PATH.parent / "favorites-archive.json",
    )
)
_REFRESHING_CACHE_PATHS: set[Path] = set()
_REFRESH_LOCK = threading.Lock()
_JSON_CACHE_MAX_ENTRIES = 32
_JSON_CACHE: OrderedDict[tuple[Path, int, int], dict[str, Any]] = OrderedDict()
_JSON_CACHE_LOCK = threading.RLock()
_DERIVED_CACHE_MAX_ENTRIES = 32
_DERIVED_CACHE: OrderedDict[tuple[Any, ...], Any] = OrderedDict()
_DERIVED_CACHE_LOCK = threading.RLock()
_DerivedValue = TypeVar("_DerivedValue")


def fetch_daily_recommender_payload(
    base_url: str = DEFAULT_DAILY_BASE_URL,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/recommendations.json"
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "foreverhyx-homepage/1.0"},
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_daily_feedback_config(
    base_url: str = DEFAULT_DAILY_BASE_URL,
) -> dict[str, str]:
    url = f"{base_url.rstrip('/')}/config.js"
    request = Request(
        url,
        headers={
            "Accept": "application/javascript",
            "User-Agent": "foreverhyx-homepage/1.0",
        },
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            text = response.read().decode("utf-8")
    except Exception:
        return {}
    return {
        "supabase_url": _extract_js_string(text, "supabaseUrl"),
        "supabase_anon_key": _extract_js_string(text, "supabaseAnonKey"),
    }


def fetch_daily_favorites_archive(
    tree_url: str = DEFAULT_FAVORITES_REPO_TREE_URL,
    raw_base_url: str = DEFAULT_FAVORITES_RAW_BASE_URL,
) -> dict[str, Any]:
    request = Request(
        tree_url,
        headers={"Accept": "application/json", "User-Agent": "foreverhyx-homepage/1.0"},
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        tree_payload = json.loads(response.read().decode("utf-8"))
    records: list[dict[str, Any]] = []
    for entry in tree_payload.get("tree", []):
        path = str(entry.get("path") or "")
        if entry.get("type") != "blob" or not re.fullmatch(r"\d{4}-\d{2}/.+/.+\.json", path):
            continue
        raw_url = f"{raw_base_url.rstrip('/')}/{quote(path, safe='/')}"
        item_request = Request(
            raw_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "foreverhyx-homepage/1.0",
            },
        )
        with urlopen(item_request, timeout=REQUEST_TIMEOUT) as item_response:
            item = json.loads(item_response.read().decode("utf-8"))
        if isinstance(item, dict):
            records.append(item)
    return {"records": records}


def load_daily_payload(
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    date: Optional[str] = None,
    payload_fetcher: Any = fetch_daily_recommender_payload,
    config_fetcher: Any = fetch_daily_feedback_config,
    favorites_fetcher: Any = fetch_daily_favorites_archive,
    cache_path: Path = DEFAULT_DAILY_CACHE_PATH,
    config_cache_path: Path = DEFAULT_FEEDBACK_CONFIG_CACHE_PATH,
    favorites_cache_path: Path = DEFAULT_DAILY_FAVORITES_CACHE_PATH,
    archive_dir: Path = DEFAULT_DAILY_ARCHIVE_DIR,
    remote_cache_ttl_seconds: Optional[int] = None,
    refresh_stale_cache_in_background: bool = True,
    expected_run_date: Optional[str] = None,
) -> dict[str, Any]:
    daily_cache_ttl = (
        REMOTE_CACHE_TTL_SECONDS if remote_cache_ttl_seconds is None else remote_cache_ttl_seconds
    )
    favorites_cache_ttl = (
        FAVORITES_CACHE_TTL_SECONDS
        if remote_cache_ttl_seconds is None
        else remote_cache_ttl_seconds
    )
    config_cache_ttl = (
        FEEDBACK_CONFIG_CACHE_TTL_SECONDS
        if remote_cache_ttl_seconds is None
        else remote_cache_ttl_seconds
    )
    required_run_date = (
        expected_run_date if expected_run_date is not None else _expected_daily_run_date()
    )
    selected_date = _parse_archive_date(date)
    favorites_payload = _load_cache_first(
        fetcher=favorites_fetcher,
        cache_path=favorites_cache_path,
        fallback={"records": []},
        remote_cache_ttl_seconds=favorites_cache_ttl,
        refresh_stale_cache_in_background=refresh_stale_cache_in_background,
        write_empty=False,
        required_run_date=None,
    )
    current_payload = _load_cache_first(
        fetcher=payload_fetcher,
        cache_path=cache_path,
        fallback={"recommendations": [], "run_date": ""},
        remote_cache_ttl_seconds=daily_cache_ttl,
        refresh_stale_cache_in_background=refresh_stale_cache_in_background,
        write_empty=True,
        required_run_date=required_run_date,
    )
    source_snapshot = _daily_source_snapshot(current_payload, favorites_payload)
    favorite_records = source_snapshot["favorite_records"]
    favorite_dates = source_snapshot["favorite_dates"]
    archive_counts = source_snapshot["archive_counts"]
    current_run_date = source_snapshot["current_run_date"]
    if current_run_date:
        archive_counts = {
            **archive_counts,
            current_run_date: source_snapshot["current_counts"],
        }
    if selected_date and selected_date != current_run_date:
        recommender_payload = _favorites_payload_for_date(favorite_records, selected_date)
    else:
        recommender_payload = current_payload
        selected_date = str(recommender_payload.get("run_date") or "")
    feedback_config = _load_cache_first(
        fetcher=config_fetcher,
        cache_path=config_cache_path,
        fallback={},
        remote_cache_ttl_seconds=config_cache_ttl,
        refresh_stale_cache_in_background=refresh_stale_cache_in_background,
        write_empty=False,
        required_run_date=None,
    )
    return build_daily_payload(
        recommender_payload,
        keywords=keywords,
        item_type=item_type,
        feedback_config=feedback_config,
        selected_date=selected_date,
        archive_dates=favorite_dates,
        archive_counts=archive_counts,
        current_run_date=current_run_date,
        profile_radar=source_snapshot["profile_radar"],
    )


def _load_cache_first(
    fetcher: Any,
    cache_path: Path,
    fallback: dict[str, Any],
    remote_cache_ttl_seconds: int,
    refresh_stale_cache_in_background: bool,
    write_empty: bool,
    required_run_date: Optional[str],
) -> dict[str, Any]:
    cached_value = _read_cache(cache_path)
    cached_has_required_run = _matches_required_run_date(cached_value, required_run_date)
    cache_is_fresh = _cache_age_seconds(cache_path) <= remote_cache_ttl_seconds
    if (
        cached_value
        and cache_is_fresh
        and (cached_has_required_run or refresh_stale_cache_in_background)
    ):
        return cached_value
    # A previous run is still a complete, useful page while today's remote
    # payload is being published. Never make navigation wait on that remote
    # edge when stale-while-revalidate is enabled: serve the cached run and
    # refresh it once in the background instead.
    if cached_value and refresh_stale_cache_in_background:
        _refresh_cache_in_background(fetcher, cache_path, write_empty=write_empty)
        return cached_value
    try:
        fresh_value = fetcher()
        if fresh_value or write_empty:
            _write_cache(cache_path, fresh_value)
        return fresh_value or cached_value or fallback
    except Exception:
        return cached_value or fallback


def _refresh_cache_in_background(fetcher: Any, cache_path: Path, write_empty: bool) -> None:
    cache_key = cache_path.resolve()
    with _REFRESH_LOCK:
        if cache_key in _REFRESHING_CACHE_PATHS:
            return
        _REFRESHING_CACHE_PATHS.add(cache_key)

    def refresh() -> None:
        try:
            fresh_value = fetcher()
            if fresh_value or write_empty:
                _write_cache(cache_path, fresh_value)
        except Exception:
            pass
        finally:
            with _REFRESH_LOCK:
                _REFRESHING_CACHE_PATHS.discard(cache_key)

    threading.Thread(target=refresh, name="daily-cache-refresh", daemon=True).start()


def _cache_age_seconds(cache_path: Path) -> float:
    try:
        return max(0.0, time.time() - cache_path.stat().st_mtime)
    except OSError:
        return float("inf")


def _expected_daily_run_date(now: Optional[float] = None) -> str:
    timestamp = time.time() if now is None else now
    utc_now = time.gmtime(timestamp)
    if utc_now.tm_hour < DAILY_RUN_READY_HOUR_UTC:
        timestamp -= 86400
    return time.strftime("%Y-%m-%d", time.gmtime(timestamp))


def _matches_required_run_date(
    cached_value: Optional[dict[str, Any]], required_run_date: Optional[str]
) -> bool:
    if not required_run_date:
        return True
    if not cached_value:
        return False
    return str(cached_value.get("run_date") or "") >= required_run_date


def _parse_archive_date(value: Optional[str]) -> str:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else ""


def _favorite_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("records") if isinstance(payload, dict) else []
    if not isinstance(records, list):
        return []
    result = []
    for record in records:
        if isinstance(record, dict) and str(record.get("rating") or "like").lower() == "like":
            result.append(record)
    return result


def _favorite_dates(records: list[dict[str, Any]]) -> list[str]:
    dates = {
        date
        for date in (
            _parse_archive_date(str(record.get("created_at") or "")[:10]) for record in records
        )
        if date
    }
    return sorted(dates, reverse=True)


def _favorite_date_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for record in records:
        date = _parse_archive_date(str(record.get("created_at") or "")[:10])
        if not date:
            continue
        date_counts = counts.setdefault(date, {"papers": 0, "code": 0})
        if _is_repository_record(record):
            date_counts["code"] += 1
        else:
            date_counts["papers"] += 1
    return counts


def _daily_source_snapshot(
    current_payload: dict[str, Any],
    favorites_payload: dict[str, Any],
) -> dict[str, Any]:
    current_signature = _json_object_signature(current_payload)
    favorites_signature = _json_object_signature(favorites_payload)

    def build_snapshot() -> dict[str, Any]:
        favorite_records = _favorite_records(favorites_payload)
        normalized_current = _normalized_payload_snapshot(current_payload, DEFAULT_DAILY_BASE_URL)
        return {
            "favorite_records": tuple(favorite_records),
            "favorite_dates": tuple(_favorite_dates(favorite_records)),
            "archive_counts": _favorite_date_counts(favorite_records),
            "current_run_date": _parse_archive_date(str(current_payload.get("run_date") or "")),
            "current_counts": dict(normalized_current["counts"]),
            "profile_radar": _profile_radar_for_payload(current_payload, favorite_records),
        }

    if current_signature is None or favorites_signature is None:
        return build_snapshot()
    return _derived_cache_value(
        ("daily-source", current_signature, favorites_signature),
        build_snapshot,
    )


def _recommendation_counts(items: Any) -> dict[str, int]:
    counts = {"papers": 0, "code": 0}
    if not isinstance(items, (list, tuple)):
        return counts
    for item in items:
        if not isinstance(item, dict):
            continue
        if _is_repository_record(item):
            counts["code"] += 1
        else:
            counts["papers"] += 1
    return counts


def _is_repository_record(item: dict[str, Any]) -> bool:
    return str(item.get("item_type") or "").lower() == "repository" or bool(
        item.get("repository_url")
    )


def _favorites_payload_for_date(
    records: list[dict[str, Any]], selected_date: str
) -> dict[str, Any] | None:
    if not selected_date:
        return None
    items = [
        _favorite_record_to_recommendation(record)
        for record in records
        if str(record.get("created_at") or "").startswith(selected_date)
    ]
    if not items:
        return {"run_date": selected_date, "recommendations": []}
    return {
        "run_date": selected_date,
        "section_labels": {},
        "recommendations": items,
    }


def _favorite_record_to_recommendation(record: dict[str, Any]) -> dict[str, Any]:
    item = dict(record)
    item["_favorite_archive_record"] = True
    if item.get("section") and not item.get("sections"):
        item["sections"] = [str(item.get("section"))]
    if item.get("arxiv_url") and not item.get("url"):
        item["url"] = item.get("arxiv_url")
    if item.get("pdf_url") and not str(item.get("pdf_url")).endswith(".pdf"):
        item["pdf_url"] = str(item.get("pdf_url")).rstrip("/") + ".pdf"
    if item.get("repository_url"):
        item["item_type"] = "repository"
        if not item.get("repository_full_name"):
            item["repository_full_name"] = _repository_name_from_url(
                str(item.get("repository_url"))
            ) or str(item.get("title") or "")
    return item


def _repository_name_from_url(url: str) -> str:
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", url)
    return match.group(1) if match else ""


def _archive_snapshot_path(archive_dir: Path, run_date: str) -> Path:
    return archive_dir / f"{run_date}.json"


def _read_archive_snapshot(archive_dir: Path, run_date: str) -> dict[str, Any] | None:
    if not run_date:
        return None
    return _read_cache(_archive_snapshot_path(archive_dir, run_date))


def _write_archive_snapshot(archive_dir: Path, payload: dict[str, Any]) -> None:
    run_date = _parse_archive_date(str(payload.get("run_date") or ""))
    if not run_date or not payload.get("recommendations"):
        return
    _write_cache(_archive_snapshot_path(archive_dir, run_date), payload)


def _archive_dates(
    archive_dir: Path, current_payload: Optional[dict[str, Any]] = None
) -> list[str]:
    dates = set()
    try:
        for path in archive_dir.glob("*.json"):
            if _parse_archive_date(path.stem):
                dates.add(path.stem)
    except OSError:
        pass
    if current_payload:
        run_date = _parse_archive_date(str(current_payload.get("run_date") or ""))
        if run_date:
            dates.add(run_date)
    return sorted(dates, reverse=True)


def build_daily_payload(
    recommender_payload: dict[str, Any],
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    feedback_config: Optional[dict[str, str]] = None,
    source_base_url: str = DEFAULT_DAILY_BASE_URL,
    selected_date: Optional[str] = None,
    archive_dates: Optional[list[str]] = None,
    archive_counts: Optional[dict[str, dict[str, int]]] = None,
    current_run_date: Optional[str] = None,
    profile_radar: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    run_date = str(recommender_payload.get("run_date") or "")
    normalized_snapshot = _normalized_payload_snapshot(recommender_payload, source_base_url)
    active_item_type = _parse_item_type(item_type)
    base_items = normalized_snapshot["items_by_type"][active_item_type]
    selected_keywords = _parse_keywords(
        keywords,
        normalized_snapshot["keywords_by_type"][active_item_type],
    )
    items = base_items
    if selected_keywords:
        items = [item for item in items if _matches_keywords(item, selected_keywords)]

    counts = _normalize_archive_counts(archive_counts)
    if run_date:
        counts.setdefault(run_date, dict(normalized_snapshot["counts"]))

    raw_profile_radar = profile_radar or recommender_payload.get("profile_radar")
    if _is_prepared_profile_radar(raw_profile_radar):
        resolved_profile_radar = copy.deepcopy(raw_profile_radar)
    else:
        resolved_profile_radar = _prepare_profile_radar(raw_profile_radar)

    return {
        "run_date": recommender_payload.get("run_date", ""),
        "source_url": source_base_url.rstrip("/"),
        "items": copy.deepcopy(list(items)) if normalized_snapshot["is_cached"] else list(items),
        "filter_keywords": selected_keywords,
        "active_item_type": active_item_type,
        "sorted_keywords": list(normalized_snapshot["sorted_keywords_by_type"][active_item_type]),
        "feedback_config": dict(feedback_config) if feedback_config else {},
        "selected_date": selected_date or run_date,
        "current_run_date": _parse_archive_date(current_run_date) or run_date,
        "archive_dates": list(archive_dates) if archive_dates else ([run_date] if run_date else []),
        "archive_counts": counts,
        "profile_radar": resolved_profile_radar,
    }


def _normalized_payload_snapshot(
    recommender_payload: dict[str, Any],
    source_base_url: str,
) -> dict[str, Any]:
    signature = _json_object_signature(recommender_payload)

    def build_snapshot() -> dict[str, Any]:
        run_date = str(recommender_payload.get("run_date") or "")
        section_labels = recommender_payload.get("section_labels") or {}
        all_items = tuple(
            _normalize_item(item, section_labels, source_base_url, run_date)
            for item in recommender_payload.get("recommendations", [])
        )
        items_by_type = {
            "": all_items,
            "paper": tuple(item for item in all_items if item["item_type"] == "paper"),
            "repository": tuple(item for item in all_items if item["item_type"] == "repository"),
        }
        keywords_by_type: dict[str, tuple[str, ...]] = {}
        sorted_keywords_by_type: dict[str, tuple[tuple[str, int], ...]] = {}
        for filter_type, filtered_items in items_by_type.items():
            keyword_counts: Counter[str] = Counter()
            for item in filtered_items:
                keyword_counts.update(item["keywords"])
            keywords_by_type[filter_type] = tuple(keyword_counts)
            sorted_keywords_by_type[filter_type] = tuple(_pack_keyword_counts(keyword_counts))
        return {
            "items_by_type": items_by_type,
            "keywords_by_type": keywords_by_type,
            "sorted_keywords_by_type": sorted_keywords_by_type,
            "counts": _recommendation_counts(all_items),
            "is_cached": signature is not None,
        }

    if signature is None:
        return build_snapshot()
    return _derived_cache_value(
        ("normalized-payload", signature, source_base_url.rstrip("/")),
        build_snapshot,
    )


def _normalize_archive_counts(
    value: Optional[dict[str, dict[str, int]]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if not isinstance(value, dict):
        return counts
    for date, raw_counts in value.items():
        parsed_date = _parse_archive_date(str(date))
        if not parsed_date or not isinstance(raw_counts, dict):
            continue
        counts[parsed_date] = {
            "papers": _safe_int(raw_counts.get("papers")),
            "code": _safe_int(raw_counts.get("code")),
        }
    return counts


def daily_search_entries(
    recommender_payload: dict[str, Any], source_base_url: str = DEFAULT_DAILY_BASE_URL
) -> list[dict[str, Any]]:
    payload = build_daily_payload(recommender_payload, source_base_url=source_base_url)
    return daily_payload_search_entries(payload)


def daily_payload_search_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for item in payload["items"]:
        entries.append(
            {
                "type": "Daily",
                "title": item["title"],
                "desc": item["tldr"] or item["abstract"],
                "tags": item["keywords"],
                "date": payload["run_date"],
                "url": item.get("detail_url") or f"/daily?paper_id={item['id']}",
            }
        )
    return entries


def _normalize_item(
    item: dict[str, Any],
    section_labels: dict[str, str],
    source_base_url: str,
    run_date: str,
) -> dict[str, Any]:
    item_id = str(
        item.get("paper_id") or item.get("repository_full_name") or item.get("title") or ""
    )
    is_repository = str(item.get("item_type", "")).lower() == "repository"
    paper_url = (
        (item.get("repository_url") or item.get("url"))
        if is_repository
        else (item.get("url") or item.get("arxiv_url"))
    )
    if not paper_url and item_id and not is_repository:
        paper_url = f"https://arxiv.org/abs/{item_id}"
    pdf_url = (
        ""
        if is_repository
        else (item.get("pdf_url") or (f"https://arxiv.org/pdf/{item_id}" if item_id else ""))
    )
    code_urls = _string_list(item.get("code_urls"))
    if is_repository and item.get("repository_url") and item.get("repository_url") not in code_urls:
        code_urls = [str(item.get("repository_url")), *code_urls]

    sections = _string_list(item.get("sections"))
    if not sections and item.get("section"):
        sections = [str(item.get("section"))]
    section = sections[0] if sections else ""
    keywords = _keywords_for_item(item, section_labels)
    authors = _string_list(item.get("authors"))
    affiliations = _string_list(item.get("affiliations"))

    normalized = {
        "id": item_id,
        "rank": item.get("rank") or 0,
        "item_type": "repository" if is_repository else "paper",
        "type_label": "Repository" if is_repository else "Paper",
        "title": str(item.get("title") or item_id),
        "abstract": str(item.get("abstract") or ""),
        "authors": authors,
        "display_authors": authors[:DISPLAY_AUTHOR_LIMIT],
        "categories": _string_list(item.get("categories")),
        "section": section,
        "section_label": section_labels.get(
            section, section.replace("_", " ").title() if section else "Daily"
        ),
        "keywords": keywords,
        "tldr": _english_tldr(item, is_repository=is_repository, keywords=keywords),
        "paper_url": paper_url or "",
        "pdf_url": pdf_url,
        "code_urls": code_urls,
        "code_search_url": "" if is_repository else str(item.get("code_search_url") or ""),
        "repository_full_name": str(item.get("repository_full_name") or item.get("title") or ""),
        "repository_description": _repository_description(item),
        "repository_url": str(item.get("repository_url") or ""),
        "repository_homepage": str(item.get("repository_homepage") or ""),
        "repository_topics": _string_list(item.get("repository_topics")),
        "repository_stars": _safe_int(item.get("repository_stars")),
        "display_repository_stars": _format_count(_safe_int(item.get("repository_stars"))),
        "repository_forks": _safe_int(item.get("repository_forks")),
        "display_repository_forks": _format_count(_safe_int(item.get("repository_forks"))),
        "repository_stars_today": _safe_int(item.get("repository_stars_today")),
        "repository_language": str(item.get("repository_language") or ""),
        "paper_links": _paper_links(item),
        "score": item.get("score") or 0,
        "ai_score": (item.get("ai_judgement") or {}).get("score", item.get("ai_score")),
    }
    normalized["article_slug"] = daily_article_slug(normalized, run_date)
    normalized["detail_url"] = f"/daily/articles/{normalized['article_slug']}"
    normalized["feedback_payload"] = {
        "paper_id": normalized["id"],
        "source": "page",
        "section": normalized["section"] or None,
        "title": normalized["title"],
        "abstract": normalized["abstract"],
        "authors": normalized["authors"],
        "affiliations": affiliations,
        "categories": normalized["categories"],
        "item_type": normalized["item_type"],
        "repository_url": normalized["repository_url"] or None,
        "paper_links": normalized["paper_links"],
    }
    return normalized


def _keywords_for_item(item: dict[str, Any], section_labels: dict[str, str]) -> list[str]:
    values: list[str] = []
    has_curated_keyword_source = bool(
        _string_list(item.get("keywords"))
        or _string_list(item.get("positive_matches"))
        or _string_list(item.get("repository_topics"))
    )
    values.extend(_string_list(item.get("keywords")))
    for match in _string_list(item.get("positive_matches")):
        values.extend(_keyword_labels(match.split(":", 1)[1].strip() if ":" in match else match))
    for topic in _string_list(item.get("repository_topics")):
        values.extend(_keyword_labels(topic))
    for category in _string_list(item.get("categories")):
        values.extend(_keyword_labels(category))
    sections = _string_list(item.get("sections")) or (
        [str(item.get("section"))] if item.get("section") else []
    )
    for section in sections:
        values.extend(SECTION_KEYWORDS.get(section, []))
    values.extend(
        _keyword_labels(
            _title_keyword_text(str(item.get("title") or "")),
            allowed=TITLE_KEYWORD_ALLOWLIST,
        )
    )
    if not has_curated_keyword_source:
        values.extend(
            _keyword_labels(str(item.get("abstract") or ""), allowed=TITLE_KEYWORD_ALLOWLIST)
        )
    return _unique(value for value in values if _is_display_keyword(value))[:DISPLAY_KEYWORD_LIMIT]


def _title_keyword_text(title: str) -> str:
    return title.split(":", 1)[1] if ":" in title else title


def _keyword_labels(value: str, allowed: set[str] | None = None) -> list[str]:
    text = " ".join(str(value).replace("_", " ").split()).strip()
    if not text or _is_arxiv_category(text) or _is_trend_keyword(text):
        return []
    exact = KEYWORD_LABELS.get(text.lower())
    if exact and (allowed is None or exact in allowed):
        return [exact]

    labels: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9]*", text):
        lowered = token.lower()
        if lowered in KEYWORD_STOPWORDS or len(lowered) <= 1:
            continue
        if _is_arxiv_category(token):
            continue
        label = KEYWORD_LABELS.get(lowered, token[:1].upper() + token[1:])
        if allowed is not None and label not in allowed:
            continue
        labels.append(label)
    return labels


def _is_arxiv_category(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z]+(?:\.[A-Z]{2,})+", value.strip()))


def _is_trend_keyword(value: str) -> bool:
    lowered = value.lower()
    return bool(re.search(r"\d", lowered) and ("star" in lowered or "today" in lowered))


def _is_display_keyword(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*", value))


def _pack_keyword_counts(keyword_counts: Counter[str]) -> list[tuple[str, int]]:
    return _pack_keyword_rows(list(keyword_counts.items()))


def _pack_keyword_rows(
    pairs: list[tuple[str, int]],
    row_width: int = FILTER_KEYWORD_ROW_WIDTH,
    gap: int = FILTER_KEYWORD_GAP,
) -> list[tuple[str, int]]:
    remaining = list(pairs)
    packed: list[tuple[str, int]] = []
    while remaining:
        anchor = remaining.pop(0)
        candidates = remaining[:10]
        best_indexes: tuple[int, ...] = ()
        best_score = (_keyword_row_width([anchor], gap), anchor[1], 0, 0)
        max_size = min(5, len(candidates))
        for size in range(1, max_size + 1):
            for indexes in combinations(range(len(candidates)), size):
                row = [anchor, *[candidates[index] for index in indexes]]
                width = _keyword_row_width(row, gap)
                if width > row_width:
                    continue
                score = (
                    width,
                    sum(pair[1] for pair in row),
                    len(indexes),
                    -sum(indexes),
                )
                if score > best_score:
                    best_score = score
                    best_indexes = indexes
        packed.append(anchor)
        selected = set(best_indexes)
        for index in best_indexes:
            packed.append(candidates[index])
        for index in sorted(selected, reverse=True):
            remaining.pop(index)
    return packed


def _keyword_row_width(row: list[tuple[str, int]], gap: int) -> int:
    if not row:
        return 0
    return sum(_keyword_chip_width(pair) for pair in row) + gap * (len(row) - 1)


def _keyword_chip_width(pair: tuple[str, int]) -> int:
    label, count = pair
    text = f"{label} ({count})"
    return round(20 + len(text) * 5.2)


def _english_tldr(
    item: dict[str, Any], is_repository: bool = False, keywords: list[str] | None = None
) -> str:
    tldr = _strip_trailing_ellipsis(str(item.get("tldr") or "").strip())
    abstract = _strip_trailing_ellipsis(str(item.get("abstract") or "").strip())
    if is_repository:
        if (
            tldr
            and not _contains_cjk(tldr)
            and tldr != abstract
            and not _looks_like_readme_excerpt(tldr)
        ):
            return tldr
        return _repository_tldr(item, keywords or [])
    if tldr and not _contains_cjk(tldr):
        return tldr
    if abstract:
        return _paper_tldr(item, keywords or [])
    return "No English TLDR is available yet; open the linked paper or repository for details."


def _paper_tldr(item: dict[str, Any], keywords: list[str]) -> str:
    abstract = _strip_trailing_ellipsis(str(item.get("abstract") or "").strip())
    if not abstract:
        topic_text = _human_list(keywords[:4]) or "the daily research profile"
        return f"This paper is archived because it matches {topic_text}. Open the source to inspect the method, evaluation, and assumptions."
    if item.get("_favorite_archive_record"):
        return _archive_paper_tldr(abstract, keywords)
    return _concise_summary_from_text(abstract, limit=240)


def _repository_tldr(item: dict[str, Any], keywords: list[str]) -> str:
    for candidate in (
        str(item.get("repository_description") or "").strip(),
        _repository_description(item),
        str(item.get("abstract") or "").strip(),
    ):
        summary = _concise_summary_from_text(candidate, limit=220)
        if summary and not _looks_like_readme_excerpt(summary):
            return summary

    topics = _unique(
        [
            *keywords,
            *_keyword_labels(" ".join(_string_list(item.get("repository_topics")))),
            *_keyword_labels(" ".join(_string_list(item.get("categories")))),
        ]
    )
    topic_text = _human_list(topics[:4]) or "systems research tooling"
    return f"This repository is archived because its metadata matches {topic_text}."


def _archive_paper_tldr(abstract: str, keywords: list[str]) -> str:
    summary = _concise_summary_from_text(abstract, limit=300, max_sentences=2)
    if summary.count(".") + summary.count("!") + summary.count("?") >= 2:
        return summary
    topic_text = _human_list(keywords[:3]) or "the long-term research profile"
    extra = f"It stands out in the archive because it connects to {topic_text}."
    return _clip_text(f"{summary} {extra}", 340)


def _concise_summary_from_text(value: str, limit: int, max_sentences: int = 1) -> str:
    text = _strip_trailing_ellipsis(" ".join(str(value or "").split()))
    if not text:
        return ""
    sentences = _sentences(text)
    summary_parts = sentences[: max(1, max_sentences)] if sentences else [text]
    summary = " ".join(summary_parts)
    if len(summary) > limit:
        summary = _clip_text(summary, limit)
        if summary and not re.search(r"[.!?]$", summary):
            summary = f"{summary}."
    return _strip_trailing_ellipsis(summary)


def _profile_radar_for_payload(
    current_payload: dict[str, Any], favorite_records: list[dict[str, Any]]
) -> dict[str, Any]:
    backend_radar = _prepare_profile_radar(current_payload.get("profile_radar"))
    if backend_radar:
        return backend_radar
    return _profile_radar_from_favorite_records(favorite_records)


def _profile_radar_from_favorite_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    items = []
    for record in records:
        run_date = _parse_archive_date(str(record.get("created_at") or "")[:10])
        recommendation = _favorite_record_to_recommendation(record)
        items.append(_normalize_item(recommendation, {}, DEFAULT_DAILY_BASE_URL, run_date))
    keyword_counts: Counter[str] = Counter()
    for item in items:
        keyword_counts.update(item.get("keywords", []))
    axes = [
        {"label": label, "value": count}
        for label, count in sorted(
            keyword_counts.items(), key=lambda item: (-item[1], item[0].casefold())
        )[:PROFILE_RADAR_AXIS_LIMIT]
        if count > 0
    ]
    return _prepare_profile_radar(
        {
            "source": "favorites_archive",
            "total_likes": len(items),
            "axes": axes,
        }
    )


def _prepare_profile_radar(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    raw_axes = value.get("axes")
    if not isinstance(raw_axes, list):
        return {}
    axes = []
    for raw_axis in raw_axes:
        if not isinstance(raw_axis, dict):
            continue
        label = _profile_axis_label(
            raw_axis.get("label") or raw_axis.get("name") or raw_axis.get("keyword")
        )
        axis_value = _safe_float(
            raw_axis.get("value", raw_axis.get("weight", raw_axis.get("score", 0)))
        )
        if not label or axis_value <= 0:
            continue
        axes.append({"label": label, "value": _profile_axis_value(axis_value)})
        if len(axes) >= PROFILE_RADAR_AXIS_LIMIT:
            break
    if not axes:
        return {}

    max_count = max(float(axis["value"]) for axis in axes)
    polygon_points = []
    total_axes = len(axes)
    for index, axis in enumerate(axes):
        angle = -math.pi / 2 + (2 * math.pi * index / total_axes)
        outer_x, outer_y = _radar_point(angle, PROFILE_RADAR_RADIUS)
        label_x, label_y = _radar_point(angle, PROFILE_RADAR_LABEL_RADIUS)
        ratio = float(axis["value"]) / max_count if max_count else 0
        point_x, point_y = _radar_point(angle, PROFILE_RADAR_RADIUS * ratio)
        polygon_points.append(_svg_point(point_x, point_y))
        axis.update(
            {
                "line_points": f"{PROFILE_RADAR_CENTER},{PROFILE_RADAR_CENTER} {_svg_point(outer_x, outer_y)}",
                "point_x": round(point_x, 1),
                "point_y": round(point_y, 1),
                "label_x": round(label_x, 1),
                "label_y": round(label_y, 1),
                "label_anchor": _profile_label_anchor(label_x),
            }
        )

    rings = []
    for ratio in (1 / 3, 2 / 3, 1):
        ring_points = [
            _svg_point(
                *_radar_point(
                    -math.pi / 2 + (2 * math.pi * index / total_axes),
                    PROFILE_RADAR_RADIUS * ratio,
                )
            )
            for index in range(total_axes)
        ]
        rings.append(" ".join(ring_points))

    return {
        "source": str(value.get("source") or ""),
        "total_likes": _safe_int(value.get("total_likes")),
        "axes": axes,
        "rings": rings,
        "polygon_points": " ".join(polygon_points),
        "max_count": _profile_axis_value(max_count),
        "view_box": "0 0 200 200",
    }


def _is_prepared_profile_radar(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and isinstance(value.get("axes"), list)
        and isinstance(value.get("rings"), list)
        and value.get("polygon_points")
        and value.get("view_box")
    )


def _profile_axis_label(value: Any) -> str:
    label = " ".join(str(value or "").split())
    if len(label) <= PROFILE_RADAR_LABEL_MAX_LENGTH:
        return label
    return f"{label[: PROFILE_RADAR_LABEL_MAX_LENGTH - 3].rstrip()}..."


def _profile_axis_value(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(float(value), 2)


def _profile_label_anchor(label_x: float) -> str:
    if abs(label_x - PROFILE_RADAR_CENTER) < 3:
        return "middle"
    return "end" if label_x > PROFILE_RADAR_CENTER else "start"


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _radar_point(angle: float, radius: float) -> tuple[float, float]:
    return (
        PROFILE_RADAR_CENTER + math.cos(angle) * radius,
        PROFILE_RADAR_CENTER + math.sin(angle) * radius,
    )


def _svg_point(x: float, y: float) -> str:
    return f"{round(x, 1)},{round(y, 1)}"


def _human_list(values: list[str]) -> str:
    clean = [value for value in values if value]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


def _sentences(value: str) -> list[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_count(value: int) -> str:
    return f"{value:,}" if value else ""


def _repository_description(item: dict[str, Any]) -> str:
    description = str(item.get("repository_description") or "").strip()
    if description:
        return _strip_trailing_ellipsis(description)
    abstract = str(item.get("abstract") or "").strip()
    for line in abstract.splitlines():
        text = " ".join(line.split()).strip(" -")
        if not text:
            continue
        if text.lower().startswith(
            ("about ", "key features", "getting started", "contributing", "citation")
        ):
            continue
        return _clip_text(_strip_trailing_ellipsis(text), 180)
    return ""


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].rstrip(".,;:- ")
    return clipped or value[:limit].rstrip()


def _looks_like_readme_excerpt(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "readme",
            "install",
            "pip install",
            "clone",
            "usage",
            "quickstart",
        )
    )


def _strip_trailing_ellipsis(value: str) -> str:
    return re.sub(r"(\s*(?:\.{3}|…))+$", "", value).rstrip()


def _paper_links(item: dict[str, Any]) -> list[dict[str, str]]:
    links = []
    for link in item.get("paper_links") or []:
        if isinstance(link, dict):
            url = str(link.get("url") or "").strip()
            label = str(link.get("label") or "Paper").strip() or "Paper"
        else:
            url = str(link).strip()
            label = "Paper"
        if url:
            links.append({"label": label, "url": url})
    return links


def _matches_keywords(item: dict[str, Any], selected_keywords: Iterable[str]) -> bool:
    keywords = {keyword.casefold() for keyword in item.get("keywords", [])}
    return all(keyword.casefold() in keywords for keyword in selected_keywords)


def _parse_keywords(value: Optional[str], available_keywords: Iterable[str] = ()) -> list[str]:
    if not value:
        return []
    requested_by_key: dict[str, str] = {}
    for part in value[:2048].split(","):
        keyword = part.strip()
        if keyword:
            requested_by_key.setdefault(keyword.casefold(), keyword)
    if not requested_by_key:
        return []

    canonical_keywords = {keyword.casefold(): keyword for keyword in available_keywords if keyword}
    if canonical_keywords:
        return sorted(
            (canonical_keywords[key] for key in requested_by_key if key in canonical_keywords),
            key=lambda keyword: (keyword.casefold(), keyword),
        )[:MAX_FILTER_KEYWORDS]

    return sorted(
        requested_by_key.values(),
        key=lambda keyword: (keyword.casefold(), keyword),
    )[:MAX_FILTER_KEYWORDS]


def _parse_item_type(value: Optional[str]) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in {"paper", "repository"} else ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _unique(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = " ".join(str(value).split())
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _extract_js_string(text: str, key: str) -> str:
    pattern = rf"{re.escape(key)}\s*:\s*[\"']([^\"']*)[\"']"
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def _json_object_signature(value: dict[str, Any]) -> tuple[Path, int, int] | None:
    with _JSON_CACHE_LOCK:
        for cache_key, cached_value in _JSON_CACHE.items():
            if cached_value is value:
                return cache_key
    return None


def _derived_cache_value(
    cache_key: tuple[Any, ...],
    builder: Callable[[], _DerivedValue],
) -> _DerivedValue:
    with _DERIVED_CACHE_LOCK:
        if cache_key in _DERIVED_CACHE:
            _DERIVED_CACHE.move_to_end(cache_key)
            return _DERIVED_CACHE[cache_key]

        value = builder()
        _DERIVED_CACHE[cache_key] = value
        while len(_DERIVED_CACHE) > _DERIVED_CACHE_MAX_ENTRIES:
            _DERIVED_CACHE.popitem(last=False)
        return value


def _read_cache(path: Path) -> dict[str, Any] | None:
    try:
        resolved_path = path.resolve()
        for _ in range(2):
            with _JSON_CACHE_LOCK:
                stat = resolved_path.stat()
                cache_key = (resolved_path, stat.st_mtime_ns, stat.st_size)
                cached_value = _JSON_CACHE.get(cache_key)
                if cached_value is not None:
                    _JSON_CACHE.move_to_end(cache_key)
                    return cached_value

                value = json.loads(resolved_path.read_text(encoding="utf-8"))
                if not isinstance(value, dict):
                    return None

                verified_stat = resolved_path.stat()
                verified_key = (
                    resolved_path,
                    verified_stat.st_mtime_ns,
                    verified_stat.st_size,
                )
                if verified_key != cache_key:
                    continue

                _invalidate_json_cache_locked(resolved_path)
                _JSON_CACHE[cache_key] = value
                while len(_JSON_CACHE) > _JSON_CACHE_MAX_ENTRIES:
                    _JSON_CACHE.popitem(last=False)
                return value
    except Exception:
        pass
    return None


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, ensure_ascii=False)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        resolved_path = path.resolve()
        with _JSON_CACHE_LOCK:
            os.replace(temporary_path, path)
            temporary_path = None
            _invalidate_json_cache_locked(resolved_path)
    except Exception:
        pass
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _invalidate_json_cache_locked(resolved_path: Path) -> None:
    stale_keys = [key for key in _JSON_CACHE if key[0] == resolved_path]
    for key in stale_keys:
        _JSON_CACHE.pop(key, None)
