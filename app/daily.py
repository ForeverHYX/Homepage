from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.request import Request, urlopen


DEFAULT_DAILY_BASE_URL = "https://foreverhyx.github.io/agentic-arch-paper-recommender"
REQUEST_TIMEOUT = 12
REMOTE_CACHE_TTL_SECONDS = int(os.getenv("HOMEPAGE_DAILY_REMOTE_CACHE_SECONDS", "900"))
DAILY_RUN_READY_HOUR_UTC = int(os.getenv("HOMEPAGE_DAILY_RUN_READY_HOUR_UTC", "4"))
DISPLAY_AUTHOR_LIMIT = 4
DISPLAY_KEYWORD_LIMIT = 10
FILTER_KEYWORD_ROW_WIDTH = 252
FILTER_KEYWORD_GAP = 8
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
    "Accelerator", "Agent", "Agents", "Agentic", "AI", "Architecture", "Autonomy",
    "Cache", "CUDA", "Cognition", "Codesign", "Communication", "Compiler",
    "Data", "Design", "Distributed", "Gem5", "GPU", "Hardware", "HPC",
    "Inference", "Interconnect", "LLM", "Maestro", "Microarchitecture", "Network",
    "Neural", "OpenMP", "Parallelism", "PyTorch", "ROCm", "Runtime", "Scheduling",
    "Search", "Serving", "Simulation", "Sparsity", "VLLM", "Workload",
}
KEYWORD_STOPWORDS = {
    "a", "an", "and", "as", "at", "based", "by", "for", "from", "in", "into", "is",
    "layer", "of", "on", "or", "the", "this", "to", "with", "x",
    "arxiv", "aware", "cross", "driven", "fast", "github", "modeling", "multi",
    "paper", "papers", "star", "stars", "system", "systems", "today",
}
DEFAULT_DAILY_CACHE_PATH = Path(os.getenv(
    "HOMEPAGE_DAILY_CACHE_FILE",
    Path(__file__).resolve().parent.parent / "content" / "daily" / "recommendations.json",
))
DEFAULT_FEEDBACK_CONFIG_CACHE_PATH = Path(os.getenv(
    "HOMEPAGE_DAILY_FEEDBACK_CONFIG_CACHE_FILE",
    DEFAULT_DAILY_CACHE_PATH.with_name("feedback-config.json"),
))
_REFRESHING_CACHE_PATHS: set[Path] = set()
_REFRESH_LOCK = threading.Lock()


def fetch_daily_recommender_payload(base_url: str = DEFAULT_DAILY_BASE_URL) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/recommendations.json"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "foreverhyx-homepage/1.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_daily_feedback_config(base_url: str = DEFAULT_DAILY_BASE_URL) -> dict[str, str]:
    url = f"{base_url.rstrip('/')}/config.js"
    request = Request(url, headers={"Accept": "application/javascript", "User-Agent": "foreverhyx-homepage/1.0"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            text = response.read().decode("utf-8")
    except Exception:
        return {}
    return {
        "supabase_url": _extract_js_string(text, "supabaseUrl"),
        "supabase_anon_key": _extract_js_string(text, "supabaseAnonKey"),
    }


def load_daily_payload(
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    payload_fetcher: Any = fetch_daily_recommender_payload,
    config_fetcher: Any = fetch_daily_feedback_config,
    cache_path: Path = DEFAULT_DAILY_CACHE_PATH,
    config_cache_path: Path = DEFAULT_FEEDBACK_CONFIG_CACHE_PATH,
    remote_cache_ttl_seconds: int = REMOTE_CACHE_TTL_SECONDS,
    refresh_stale_cache_in_background: bool = True,
    expected_run_date: Optional[str] = None,
) -> dict[str, Any]:
    required_run_date = expected_run_date if expected_run_date is not None else _expected_daily_run_date()
    recommender_payload = _load_cache_first(
        fetcher=payload_fetcher,
        cache_path=cache_path,
        fallback={"recommendations": [], "run_date": ""},
        remote_cache_ttl_seconds=remote_cache_ttl_seconds,
        refresh_stale_cache_in_background=refresh_stale_cache_in_background,
        write_empty=True,
        required_run_date=required_run_date,
    )
    feedback_config = _load_cache_first(
        fetcher=config_fetcher,
        cache_path=config_cache_path,
        fallback={},
        remote_cache_ttl_seconds=remote_cache_ttl_seconds,
        refresh_stale_cache_in_background=refresh_stale_cache_in_background,
        write_empty=False,
        required_run_date=None,
    )
    return build_daily_payload(recommender_payload, keywords=keywords, item_type=item_type, feedback_config=feedback_config)


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
    if cached_value and cached_has_required_run and _cache_age_seconds(cache_path) <= remote_cache_ttl_seconds:
        return cached_value
    if cached_value and cached_has_required_run and refresh_stale_cache_in_background:
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


def _matches_required_run_date(cached_value: Optional[dict[str, Any]], required_run_date: Optional[str]) -> bool:
    if not required_run_date:
        return True
    if not cached_value:
        return False
    return str(cached_value.get("run_date") or "") >= required_run_date


def build_daily_payload(
    recommender_payload: dict[str, Any],
    keywords: Optional[str] = None,
    item_type: Optional[str] = None,
    feedback_config: Optional[dict[str, str]] = None,
    source_base_url: str = DEFAULT_DAILY_BASE_URL,
) -> dict[str, Any]:
    all_items = [_normalize_item(item, recommender_payload.get("section_labels") or {}, source_base_url) for item in recommender_payload.get("recommendations", [])]
    active_item_type = _parse_item_type(item_type)
    base_items = [item for item in all_items if not active_item_type or item["item_type"] == active_item_type]
    items = base_items
    selected_keywords = _parse_keywords(keywords)
    if selected_keywords:
        items = [item for item in items if _matches_keywords(item, selected_keywords)]

    keyword_counts: Counter[str] = Counter()
    for item in base_items:
        keyword_counts.update(item["keywords"])

    return {
        "run_date": recommender_payload.get("run_date", ""),
        "source_url": source_base_url.rstrip("/"),
        "items": items,
        "filter_keywords": selected_keywords,
        "active_item_type": active_item_type,
        "sorted_keywords": _pack_keyword_counts(keyword_counts),
        "feedback_config": feedback_config or {},
    }


def daily_search_entries(recommender_payload: dict[str, Any], source_base_url: str = DEFAULT_DAILY_BASE_URL) -> list[dict[str, Any]]:
    payload = build_daily_payload(recommender_payload, source_base_url=source_base_url)
    return daily_payload_search_entries(payload)


def daily_payload_search_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for item in payload["items"]:
        entries.append({
            "type": "Daily",
            "title": item["title"],
            "desc": item["tldr"] or item["abstract"],
            "tags": item["keywords"],
            "date": payload["run_date"],
            "url": f"/daily?paper_id={item['id']}",
        })
    return entries


def _normalize_item(item: dict[str, Any], section_labels: dict[str, str], source_base_url: str) -> dict[str, Any]:
    item_id = str(item.get("paper_id") or item.get("repository_full_name") or item.get("title") or "")
    is_repository = str(item.get("item_type", "")).lower() == "repository"
    paper_url = item.get("repository_url") or item.get("url") if is_repository else item.get("url")
    if not paper_url and item_id and not is_repository:
        paper_url = f"https://arxiv.org/abs/{item_id}"
    pdf_url = "" if is_repository else (item.get("pdf_url") or (f"https://arxiv.org/pdf/{item_id}" if item_id else ""))
    code_urls = _string_list(item.get("code_urls"))
    if is_repository and item.get("repository_url") and item.get("repository_url") not in code_urls:
        code_urls = [str(item.get("repository_url")), *code_urls]

    sections = _string_list(item.get("sections"))
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
        "section_label": section_labels.get(section, section.replace("_", " ").title() if section else "Daily"),
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
    for match in _string_list(item.get("positive_matches")):
        values.extend(_keyword_labels(match.split(":", 1)[1].strip() if ":" in match else match))
    for topic in _string_list(item.get("repository_topics")):
        values.extend(_keyword_labels(topic))
    for category in _string_list(item.get("categories")):
        values.extend(_keyword_labels(category))
    for section in _string_list(item.get("sections")):
        values.extend(SECTION_KEYWORDS.get(section, []))
    values.extend(_keyword_labels(_title_keyword_text(str(item.get("title") or "")), allowed=TITLE_KEYWORD_ALLOWLIST))
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
                score = (width, sum(pair[1] for pair in row), len(indexes), -sum(indexes))
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


def _english_tldr(item: dict[str, Any], is_repository: bool = False, keywords: list[str] | None = None) -> str:
    tldr = _strip_trailing_ellipsis(str(item.get("tldr") or "").strip())
    abstract = _strip_trailing_ellipsis(str(item.get("abstract") or "").strip())
    if is_repository:
        if tldr and not _contains_cjk(tldr) and tldr != abstract and not _looks_like_readme_excerpt(tldr):
            return tldr
        return _repository_tldr(item, keywords or [])
    if tldr and not _contains_cjk(tldr):
        return tldr
    if abstract:
        return abstract
    return "No English TLDR is available yet; open the linked paper or repository for details."


def _repository_tldr(item: dict[str, Any], keywords: list[str]) -> str:
    title = str(item.get("title") or item.get("repository_full_name") or "This repository").strip()
    language = str(item.get("repository_language") or "").strip()
    topics = _unique([
        *keywords,
        *_keyword_labels(" ".join(_string_list(item.get("repository_topics")))),
        *_keyword_labels(" ".join(_string_list(item.get("categories")))),
    ])
    topic_text = _human_list(topics[:4]) or "systems research tooling"
    language_text = f"{language} " if language else ""
    return (
        f"Problem: Researchers need reusable code for {topic_text}. "
        f"Method: {title} packages {language_text}implementation artifacts around {topic_text}, so it should be assessed through its code, examples, and linked papers. "
        f"Finding: The available metadata points to {topic_text} as the main relevance signal. "
        f"Why it matters: It gives the recommendation profile concrete repository feedback for future papers, tools, and architecture experiments."
    )


def _human_list(values: list[str]) -> str:
    clean = [value for value in values if value]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


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
        if text.lower().startswith(("about ", "key features", "getting started", "contributing", "citation")):
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
    return any(marker in lowered for marker in ("readme", "install", "pip install", "clone", "usage", "quickstart"))


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
    haystack = " ".join([
        item.get("title", ""),
        item.get("abstract", ""),
        item.get("tldr", ""),
        " ".join(item.get("authors", [])),
        " ".join(item.get("keywords", [])),
    ]).lower()
    return all(keyword.lower() in haystack for keyword in selected_keywords)


def _parse_keywords(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


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


def _read_cache(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
