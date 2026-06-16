from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


DAILY_ARTICLES_DIR = Path(__file__).resolve().parent.parent / "content" / "daily" / "articles"
DEFAULT_OPENAI_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_OPENAI_MODEL = "deepseek-v4-flash"
ARTICLE_GENERATOR_VERSION = "2"
ARTICLE_GENERATOR_MARKER = f"Daily-Article-Version: {ARTICLE_GENERATOR_VERSION}"
REQUIRED_SECTIONS = (
    "## Core Idea",
    "## What Is New",
    "## Methodology",
    "## Figure To Read First",
    "## Minimal Mental Model",
    "## Why It Matters",
)


def daily_article_slug(item: dict[str, Any], run_date: str) -> str:
    date = _safe_date(run_date)
    identifier = str(item.get("id") or item.get("paper_id") or item.get("repository_full_name") or item.get("title") or "daily-item")
    if str(item.get("item_type") or "").lower() == "repository" and not identifier.startswith("repo-"):
        identifier = f"repo-{identifier}"
    return f"{date}-{_slugify(identifier)}"


def ensure_daily_article_markdown(
    item: dict[str, Any],
    run_date: str,
    output_dir: Path = DAILY_ARTICLES_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = daily_article_slug(item, run_date)
    path = output_dir / f"{slug}.md"
    if _is_current_daily_article(path):
        return path

    markdown_text = _llm_daily_article_markdown(item, run_date) or generate_daily_article_markdown(item, run_date)
    markdown_text = _ensure_generator_marker(markdown_text)
    path.write_text(markdown_text, encoding="utf-8")
    return path


def generate_daily_article_markdown(item: dict[str, Any], run_date: str) -> str:
    title = _clean_text(item.get("title")) or "Daily Recommendation"
    item_type = "Repository" if item.get("item_type") == "repository" else "Paper"
    tags = _unique(["Daily", item_type, *_string_list(item.get("keywords"))[:5]])
    abstract = _clean_text(item.get("abstract")) or _clean_text(item.get("tldr")) or "No abstract is available in the daily payload."
    tldr = _clean_text(item.get("tldr")) or abstract
    source_url = _source_url(item)
    figure_markdown = _figure_markdown(item)
    code_markdown = _code_markdown(item)
    formula = _formula_for(item)

    return "\n".join([
        f"# {title}",
        "",
        f"Date: {_safe_date(run_date)}",
        "Author: Yixun Hong",
        f"Tags: {', '.join(tags)}",
        f"Abstract: {_single_line(_abstract_line(tldr, abstract))}",
        f"<!-- {ARTICLE_GENERATOR_MARKER} -->",
        "",
        source_url,
        "",
        "## Core Idea",
        "",
        _core_idea_text(item, tldr),
        "",
        _profile_relevance_text(item),
        "",
        "## What Is New",
        "",
        _innovation_text(item),
        "",
        "## Methodology",
        "",
        _methodology_text(item),
        "",
        formula,
        "",
        "## Figure To Read First",
        "",
        figure_markdown,
        "",
        "## Minimal Mental Model",
        "",
        code_markdown,
        "",
        "## Why It Matters",
        "",
        _why_it_matters(item),
        "",
    ])


def _llm_daily_article_markdown(item: dict[str, Any], run_date: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return ""
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    endpoint = f"{base_url}/chat/completions"
    prompt = _llm_prompt(item, run_date)
    request = Request(
        endpoint,
        data=json.dumps({
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write concise English research notes for a personal academic homepage. "
                        "Return Markdown only. Follow the requested frontmatter-like format exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=35) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = str(payload["choices"][0]["message"]["content"]).strip()
    except Exception:
        return ""
    if not content.startswith("# "):
        return ""
    if not all(marker in content for marker in REQUIRED_SECTIONS):
        return ""
    return _ensure_generator_marker(content.rstrip() + "\n")


def _llm_prompt(item: dict[str, Any], run_date: str) -> str:
    return (
        "Generate a short Markdown article for this daily recommendation. "
        "It must be readable in a few minutes and use this homepage format:\n"
        "# Title\n\nDate: YYYY-MM-DD\nAuthor: Yixun Hong\nTags: Daily, Paper-or-Repository, ...\nAbstract: one sentence\n\n"
        "Then include exactly these sections: Core Idea, What Is New, Methodology, Figure To Read First, Minimal Mental Model, Why It Matters.\n"
        "The article must explain the core idea, innovation, methodology, and why it matters for computer architecture or systems research. "
        "Include one compact formula or text code block. Include a figure callout using the provided PDF/repository/paper links when actual figure images are not available. "
        "Do not be long.\n\n"
        f"Run date: {run_date}\n"
        f"Payload:\n{json.dumps(item, ensure_ascii=False, indent=2)}"
    )


def _figure_markdown(item: dict[str, Any]) -> str:
    figure_urls = _string_list(item.get("figure_urls"))
    if figure_urls:
        return f"![Selected figure]({figure_urls[0]})\n\nStart with this figure because it is the fastest way to connect the method description to the paper's claimed mechanism."

    if item.get("item_type") == "repository":
        repo_url = _clean_text(item.get("repository_url")) or _source_url(item)
        return (
            f"[Repository diagram or README figures]({repo_url}) are the right visual entry point. "
            "Read the top-level architecture diagram or workflow image first, then map it to the method summary above."
        )

    pdf_url = _clean_text(item.get("pdf_url")) or _pdf_url_from_id(_clean_text(item.get("id")))
    if pdf_url:
        if not pdf_url.endswith(".pdf"):
            pdf_url = pdf_url.rstrip("/") + ".pdf"
        return (
            f"![Paper PDF with figures]({pdf_url})\n\n"
            "Read this visual first: focus on the first architecture, workflow, or pipeline figure before the experiments. It should show what is optimized, what feedback signal is used, and where the system boundary sits."
        )
    return "No figure asset is cached yet. Open the source link and inspect the first method or system overview figure."


def _code_markdown(item: dict[str, Any]) -> str:
    if item.get("item_type") == "repository":
        repo = _clean_text(item.get("repository_full_name")) or _clean_text(item.get("title")) or "repository"
        return "\n".join([
            "```text",
            f"{repo}",
            "  inputs        -> workload / prompt / trace",
            "  core engine   -> scheduling, search, simulation, or runtime policy",
            "  outputs       -> artifact, measurement, or optimized configuration",
            "```",
        ])
    return "\n".join([
        "```text",
        "research artifact",
        "  question      -> what design, runtime, or system boundary changes?",
        "  mechanism     -> model, agent, compiler, simulator, or hardware feedback",
        "  evaluation    -> baseline comparison plus cost / latency / accuracy signal",
        "  reusable idea -> what should carry into the next architecture experiment?",
        "```",
    ])


def _formula_for(item: dict[str, Any]) -> str:
    if item.get("item_type") == "repository":
        return "`utility(repo) = relevance_to_profile + reproducibility_signal + maintenance_signal`"
    return "`score(design) = quality_metric(design) - cost_to_evaluate(design) + feedback_gain(design)`"


def _innovation_text(item: dict[str, Any]) -> str:
    keywords = _human_list(_string_list(item.get("keywords"))[:4])
    item_type = item.get("item_type")
    if item_type == "repository":
        return (
            f"The interesting part is not just that this is code. It packages {keywords or 'systems ideas'} into a reusable artifact, "
            "which makes the recommendation actionable: the repository can be inspected, run, forked, and used as feedback for future paper ranking."
        )
    return (
        f"The novelty signal is concentrated around {keywords or 'the method and evaluation loop'}. "
        "For this profile, the important question is whether the paper changes how architecture ideas are generated, evaluated, or connected to software and hardware constraints."
    )


def _methodology_text(item: dict[str, Any]) -> str:
    abstract = _clean_text(item.get("abstract"))
    if item.get("item_type") == "repository":
        language = _clean_text(item.get("repository_language"))
        lang_text = f" The implementation language signal is {language}." if language else ""
        return (
            "Read this as an executable artifact: identify its input contract, the core engine, the evaluation path, and the claims implied by examples or linked papers."
            + lang_text
        )
    if abstract:
        sentences = _sentences(abstract)
        mechanism = _clip_text(sentences[0] if sentences else abstract, 280)
        evidence = _evidence_sentence(sentences[1:])
        if evidence:
            return f"Read this as a loop: define the target system, apply the proposed mechanism, measure against a baseline, then use the measured signal to justify the next design choice. Mechanism: {mechanism} Evidence: {_clip_text(evidence, 220)}"
        return f"Read this as a loop: define the target system, apply the proposed mechanism, measure against a baseline, then use the measured signal to justify the next design choice. Mechanism: {mechanism}"
    return "Read this as a loop: identify the search space, the feedback signal, the baseline, and the evaluation cost before trusting the headline result."


def _why_it_matters(item: dict[str, Any]) -> str:
    if item.get("item_type") == "repository":
        return "Repository recommendations matter when they turn a paper idea into something testable. A like on this item also gives the daily recommender a concrete tooling preference to learn from."
    return "Paper recommendations matter when they sharpen the research map: what problem is now easier to study, what methodology becomes reusable, and which architecture assumptions should be questioned next."


def _source_url(item: dict[str, Any]) -> str:
    return _clean_text(item.get("paper_url")) or _clean_text(item.get("repository_url")) or "#"


def _pdf_url_from_id(item_id: str) -> str:
    if re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", item_id):
        return f"https://arxiv.org/pdf/{item_id}.pdf"
    return ""


def _slugify(value: str) -> str:
    normalized = str(value).strip().lower()
    normalized = normalized.replace(":", "-")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "daily-item"


def _safe_date(value: str) -> str:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else "unknown-date"


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _single_line(value: str) -> str:
    return _clean_text(value).replace("\n", " ")


def _paragraph(value: str) -> str:
    return _clean_text(value) or "The daily payload does not include a detailed summary yet."


def _abstract_line(tldr: str, abstract: str) -> str:
    return _clip_text(_first_sentence(tldr) or _first_sentence(abstract) or tldr or abstract, 260)


def _core_idea_text(item: dict[str, Any], tldr: str) -> str:
    summary = _clip_text(_first_sentence(tldr) or _clean_text(tldr), 320)
    if summary:
        return summary
    if item.get("item_type") == "repository":
        return "The core idea is to treat the repository as a runnable systems artifact rather than a passive link."
    return "The core idea is to identify the design mechanism, the feedback signal, and the evaluation boundary before reading the full paper."


def _profile_relevance_text(item: dict[str, Any]) -> str:
    keywords = _human_list(_string_list(item.get("keywords"))[:3])
    if item.get("item_type") == "repository":
        return f"For this daily profile, it is worth opening because it turns {keywords or 'a systems idea'} into code that can be inspected and reused."
    return f"For this daily profile, it is worth opening because it links {keywords or 'the topic'} to a concrete method, not just a broad trend."


def _sentences(value: str) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _first_sentence(value: str) -> str:
    sentences = _sentences(value)
    return sentences[0] if sentences else ""


def _evidence_sentence(sentences: list[str]) -> str:
    for sentence in sentences:
        if re.search(r"\b(achieves?|shows?|validates?|evaluates?|improves?|outperforms?|demonstrates?|results?)\b", sentence, re.I):
            return sentence
    return sentences[0] if sentences else ""


def _clip_text(value: str, limit: int) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(".,;:- ")
    if clipped and not re.search(r"[.!?]$", clipped):
        clipped = f"{clipped}."
    return clipped or text[:limit].rstrip()


def _is_current_daily_article(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size <= 0:
            return False
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return ARTICLE_GENERATOR_MARKER in text and all(section in text for section in REQUIRED_SECTIONS)


def _ensure_generator_marker(markdown_text: str) -> str:
    text = markdown_text.rstrip() + "\n"
    if ARTICLE_GENERATOR_MARKER in text:
        return text
    lines = text.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("abstract:"):
            insert_at = index + 1
            break
    marker = f"<!-- {ARTICLE_GENERATOR_MARKER} -->"
    if insert_at:
        lines.insert(insert_at, marker)
        return "\n".join(lines).rstrip() + "\n"
    return f"{marker}\n{text}"


def _human_list(values: list[str]) -> str:
    clean = [value for value in values if value]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"
