from __future__ import annotations

import re
from pathlib import Path
from typing import Any


DAILY_ARTICLES_DIR = Path(__file__).resolve().parent.parent / "content" / "daily" / "articles"
# Version 5 = version 4 plus abs-page furniture filtering in section
# summaries (Submission history / BibTeX / Bookmark ... never appear).
# Version 4 rendered Chinese guides from bilingual brief fields, version 3
# was English-only quick-read briefs, version 2 is the legacy format. Items
# without the newer fields keep their previously cached article version.
ARTICLE_GENERATOR_VERSION = "5"
ARTICLE_GENERATOR_MARKER = f"Daily-Article-Version: {ARTICLE_GENERATOR_VERSION}"
LEGACY_ARTICLE_MARKER = "Daily-Article-Version: 2"
REQUIRED_SECTIONS = (
    "## Core Idea",
    "## What Is New",
    "## Methodology",
    "## Figure To Read First",
    "## Minimal Mental Model",
    "## Why It Matters",
)
ZH_POINT_LABELS = {"问题": "Problem", "方法": "Method", "证据": "Evidence", "意义": "Impact", "局限": "Limitation"}


def daily_article_slug(item: dict[str, Any], run_date: str) -> str:
    date = _safe_date(run_date)
    identifier = str(
        item.get("id")
        or item.get("paper_id")
        or item.get("repository_full_name")
        or item.get("title")
        or "daily-item"
    )
    if str(item.get("item_type") or "").lower() == "repository" and not identifier.startswith(
        "repo-"
    ):
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
    if _is_current_daily_article(path, _required_article_version(item)):
        return path

    markdown_text = generate_daily_article_markdown(item, run_date)
    markdown_text = _ensure_generator_marker(markdown_text, _required_article_version(item))
    path.write_text(markdown_text, encoding="utf-8")
    return path


def _required_article_version(item: dict[str, Any]) -> str:
    if _has_chinese_brief(item):
        return "5"
    if _has_brief(item):
        return "3"
    return "2"


def _has_brief(item: dict[str, Any]) -> bool:
    return bool(_clean_text(item.get("headline")) or _brief_points(item.get("key_points")))


def _has_chinese_brief(item: dict[str, Any]) -> bool:
    return bool(_clean_text(item.get("headline_zh")) or _brief_points(item.get("key_points_zh")))


def _brief_points(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    points = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        text = _clean_text(entry.get("text"))
        if text:
            points.append({"label": _clean_text(entry.get("label")) or "Note", "text": text})
    return points


def _point_text(points: list[dict[str, str]], label: str) -> str:
    lowered = label.lower()
    for point in points:
        if point["label"].strip().lower() == lowered:
            return point["text"]
    return ""


def generate_daily_article_markdown(item: dict[str, Any], run_date: str) -> str:
    title = _clean_text(item.get("title")) or "Daily Recommendation"
    item_type = "Repository" if item.get("item_type") == "repository" else "Paper"
    tags = _unique(["Daily", item_type, *_string_list(item.get("keywords"))[:5]])
    abstract = (
        _clean_text(item.get("abstract"))
        or _clean_text(item.get("tldr"))
        or "No abstract is available in the daily payload."
    )
    headline = _clean_text(item.get("headline"))
    headline_zh = _clean_text(item.get("headline_zh"))
    key_points = _brief_points(item.get("key_points"))
    key_points_zh = _brief_points(item.get("key_points_zh"))
    has_zh = bool(headline_zh or key_points_zh)
    tldr = _clean_text(item.get("tldr")) or abstract
    summary_line = headline or tldr
    source_line = _source_line(item)

    brief_sections = [
        entry
        for entry in (item.get("section_summaries") or [])
        if isinstance(entry, dict) and _clean_text(entry.get("title")) and _clean_text(entry.get("summary"))
    ]
    brief_figures = [
        entry
        for entry in (item.get("figure_explanations") or [])
        if isinstance(entry, dict) and _clean_text(entry.get("caption"))
    ]
    key_figure = item.get("key_figure") if isinstance(item.get("key_figure"), dict) else {}

    figure_markdown = _key_figure_markdown(key_figure, has_zh=has_zh) or _figure_markdown(item)
    code_markdown = _code_markdown(item)
    formula = _formula_for(item)

    parts = [
        f"# {title}",
        "",
        f"Date: {_safe_date(run_date)}",
        "Author: Yixun Hong",
        f"Tags: {', '.join(tags)}",
        f"Abstract: {_single_line(_abstract_line(summary_line, abstract))}",
        "",
        source_line,
        "",
        "## Core Idea · 核心思想" if has_zh else "## Core Idea",
        "",
        _core_idea_bilingual(headline_zh, headline, item, tldr),
        "",
        _profile_relevance_text(item, has_zh=has_zh),
        "",
        "## What Is New · 要点速览" if has_zh else "## What Is New",
        "",
        _key_points_markdown(key_points_zh) or _key_points_markdown(key_points) or _innovation_text(item),
        "",
        "## Methodology · 方法与证据" if has_zh else "## Methodology",
        "",
        _methodology_with_brief(item, key_points, key_points_zh, brief_sections, has_zh=has_zh),
        "",
        formula,
        "",
        "## Figure To Read First · 首先看这张图" if has_zh else "## Figure To Read First",
        "",
        figure_markdown,
        "",
        "## Minimal Mental Model · 最小心智模型" if has_zh else "## Minimal Mental Model",
        "",
        code_markdown,
        "",
        "## Why It Matters · 意义与局限" if has_zh else "## Why It Matters",
        "",
        _why_it_matters_with_brief(item, key_points, key_points_zh, has_zh=has_zh),
        "",
    ]
    if brief_sections:
        parts.extend(
            [
                "## Section Map · 分段速览" if has_zh else "## Section Map",
                "",
                _section_map_markdown(brief_sections),
                "",
            ]
        )
    if brief_figures:
        parts.extend(
            [
                "## Figure Notes · 图表速览" if has_zh else "## Figure Notes",
                "",
                _figure_notes_markdown(brief_figures),
                "",
            ]
        )
    markdown = "\n".join(parts)
    return _ensure_generator_marker(markdown, _required_article_version(item))


def _core_idea_bilingual(
    headline_zh: str, headline: str, item: dict[str, Any], tldr: str
) -> str:
    if headline_zh:
        lines = [headline_zh]
        if headline:
            lines.append(f"*{headline}*")
        return "\n\n".join(lines)
    return headline or _core_idea_text(item, tldr)


def _key_points_markdown(points: list[dict[str, str]]) -> str:
    if not points:
        return ""

    def _separator(label: str) -> str:
        return "：" if re.search(r"[\u4e00-\u9fff]", label) else ":"

    return "\n".join(
        f"- **{point['label']}{_separator(point['label'])}** {point['text']}" for point in points
    )


def _point_text_zh(points: list[dict[str, str]], zh_label: str) -> str:
    for point in points:
        if point["label"].strip() == zh_label:
            return point["text"]
    return ""


def _methodology_with_brief(
    item: dict[str, Any],
    key_points: list[dict[str, str]],
    key_points_zh: list[dict[str, str]],
    brief_sections: list[dict[str, Any]],
    has_zh: bool = False,
) -> str:
    lines = []
    if has_zh:
        method = _point_text_zh(key_points_zh, "方法")
        evidence = _point_text_zh(key_points_zh, "证据")
        if method:
            lines.append(f"机制：{method}")
        else:
            method_en = _point_text(key_points, "Method")
            lines.append(f"机制：{method_en}" if method_en else _methodology_text(item))
        if evidence:
            lines.append(f"证据：{evidence}")
        else:
            evidence_en = _point_text(key_points, "Evidence")
            if evidence_en:
                lines.append(f"证据：{evidence_en}")
    else:
        method = _point_text(key_points, "Method")
        evidence = _point_text(key_points, "Evidence")
        if method:
            lines.append(f"Mechanism: {method}")
        else:
            lines.append(_methodology_text(item))
        if evidence:
            lines.append(f"Evidence: {evidence}")
    if brief_sections:
        pointer = (
            "各分段的要点速览见 Section Map，可对照原文逐节深读。"
            if has_zh
            else "Deep-read the paper section by section with the per-section summaries under Section Map."
        )
        lines.append(pointer)
    return "\n\n".join(lines)


def _why_it_matters_with_brief(
    item: dict[str, Any],
    key_points: list[dict[str, str]],
    key_points_zh: list[dict[str, str]],
    has_zh: bool = False,
) -> str:
    lines = []
    if has_zh:
        impact = _point_text_zh(key_points_zh, "意义")
        limitation = _point_text_zh(key_points_zh, "局限")
        if impact:
            lines.append(f"意义：{impact}")
        elif _point_text(key_points, "Impact"):
            lines.append(f"意义：{_point_text(key_points, 'Impact')}")
        if limitation:
            lines.append(f"局限：{limitation}")
        elif _point_text(key_points, "Limitation"):
            lines.append(f"局限：{_point_text(key_points, 'Limitation')}")
    else:
        impact = _point_text(key_points, "Impact")
        limitation = _point_text(key_points, "Limitation")
        if impact:
            lines.append(f"Impact: {impact}")
        if limitation:
            lines.append(f"Limitation: {limitation}")
    if not lines:
        lines.append(_why_it_matters(item))
    return "\n\n".join(lines)


def _key_figure_markdown(figure: dict[str, Any], has_zh: bool = False) -> str:
    label = _clean_text(figure.get("label")) or "Figure"
    caption = _clean_text(figure.get("caption"))
    explanation = _clean_text(figure.get("explanation"))
    explanation_zh = _clean_text(figure.get("explanation_zh"))
    if not caption and not explanation and not explanation_zh:
        return ""
    lines = [f"**{label}** — {caption}" if caption else f"**{label}**"]
    if explanation_zh:
        lines.append(f"解读：{explanation_zh}")
    elif explanation:
        lines.append(f"Why it matters: {explanation}")
    return "\n\n".join(lines)


def _section_map_markdown(sections: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- **{_clean_text(entry.get('title'))}** — {_clean_text(entry.get('summary'))}"
        for entry in sections
    )


def _figure_notes_markdown(figures: list[dict[str, Any]]) -> str:
    lines = []
    for entry in figures:
        label = _clean_text(entry.get("label")) or "Figure"
        caption = _clean_text(entry.get("caption"))
        explanation = _clean_text(entry.get("explanation"))
        line = f"- **{label}** — {caption}" if caption else f"- **{label}**"
        if explanation:
            line = f"{line}: {explanation}"
        lines.append(line)
    return "\n".join(lines)


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
        repo = (
            _clean_text(item.get("repository_full_name"))
            or _clean_text(item.get("title"))
            or "repository"
        )
        return "\n".join(
            [
                "```text",
                f"{repo}",
                "  inputs        -> workload / prompt / trace",
                "  core engine   -> scheduling, search, simulation, or runtime policy",
                "  outputs       -> artifact, measurement, or optimized configuration",
                "```",
            ]
        )
    return "\n".join(
        [
            "```text",
            "research artifact",
            "  question      -> what design, runtime, or system boundary changes?",
            "  mechanism     -> model, agent, compiler, simulator, or hardware feedback",
            "  evaluation    -> baseline comparison plus cost / latency / accuracy signal",
            "  reusable idea -> what should carry into the next architecture experiment?",
            "```",
        ]
    )


def _formula_for(item: dict[str, Any]) -> str:
    if item.get("item_type") == "repository":
        return (
            "`utility(repo) = relevance_to_profile + reproducibility_signal + maintenance_signal`"
        )
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


def _source_line(item: dict[str, Any]) -> str:
    # Explicit markdown links: bare URLs are not auto-linked by the blog renderer.
    source_url = _source_url(item)
    parts = [f"[Open source]({source_url})"] if source_url and source_url != "#" else []
    if item.get("item_type") != "repository":
        pdf_url = _clean_text(item.get("pdf_url")) or _pdf_url_from_id(_clean_text(item.get("id")))
        if pdf_url and not pdf_url.endswith(".pdf"):
            pdf_url = pdf_url.rstrip("/") + ".pdf"
        if pdf_url:
            parts.append(f"[Original PDF]({pdf_url})")
    return " · ".join(parts)


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


def _profile_relevance_text(item: dict[str, Any], has_zh: bool = False) -> str:
    keywords = _human_list(_string_list(item.get("keywords"))[:3])
    if has_zh:
        if item.get("item_type") == "repository":
            return f"结合当前研究画像值得优先关注：它把 {keywords or '相关系统思想'} 做成了可检查、可复用的代码工件。"
        return f"结合当前研究画像值得优先关注：它把 {keywords or '相关主题'} 落到了具体可检验的方法层面。"
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
        if re.search(
            r"\b(achieves?|shows?|validates?|evaluates?|improves?|outperforms?|demonstrates?|results?)\b",
            sentence,
            re.I,
        ):
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


def _is_current_daily_article(path: Path, required_version: str) -> bool:
    try:
        if not path.exists() or path.stat().st_size <= 0:
            return False
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return f"Daily-Article-Version: {required_version}" in text and all(
        section in text for section in REQUIRED_SECTIONS
    )


def _ensure_generator_marker(markdown_text: str, version: str) -> str:
    text = markdown_text.rstrip() + "\n"
    if f"Daily-Article-Version: {version}" in text:
        return text
    lines = text.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("abstract:"):
            insert_at = index + 1
            break
    marker = f"<!-- Daily-Article-Version: {version} -->"
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
