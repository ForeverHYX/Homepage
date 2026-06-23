# Compiler Exams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public exam bank page with one Markdown file per compiler final or mock exam, each question followed by a collapsible reference answer.

**Architecture:** Reuse the existing FastAPI + Jinja2 + Markdown article pipeline. Add a focused `app/exams.py` content loader, list/detail routes under `/exams`, templates that mirror the article cards, and content files under `content/exams/`.

**Tech Stack:** FastAPI, Jinja2, Python-Markdown, vanilla HTML `<details>`, unittest/TestClient.

---

### Task 1: Exam Route Tests

**Files:**
- Create: `tests/test_exam_pages.py`
- Modify later: `app/config.py`, `app/exams.py`, `app/routers/pages.py`, `app/templates/base.html`, `app/templates/pages/exams.html`

- [ ] Write failing tests for `/exams`, `/exams/{slug}`, search index, sitemap, nav, Markdown file count, and `<details>` answers.
- [ ] Run `python -m unittest tests.test_exam_pages` and confirm failure because routes/content do not exist.

### Task 2: Exam Loader And Routes

**Files:**
- Modify: `app/config.py`
- Create: `app/exams.py`
- Modify: `app/routers/pages.py`
- Create: `app/templates/pages/exams.html`

- [ ] Add `EXAMS_DIR = CONTENT_DIR / "exams"`.
- [ ] Implement Markdown metadata parsing and detail rendering in `app/exams.py`.
- [ ] Add `/exams`, `/exams/{slug}`, `/api/site/exams`, and `/api/site/exams/{slug}`.
- [ ] Add exams to sitemap and search index.

### Task 3: Content And Navigation

**Files:**
- Create: `content/exams/compiler-2023-2024-final-recall.md`
- Create: `content/exams/compiler-final-big-question-recall.md`
- Create: `content/exams/compiler-mock-final-a.md`
- Create: `content/exams/compiler-mock-final-b.md`
- Create: `content/exams/compiler-mock-final-c.md`
- Modify: `app/templates/base.html`

- [ ] Add one Markdown file per exam.
- [ ] Use `<details><summary>参考答案</summary>...</details>` below questions.
- [ ] Add `Exams` to desktop and mobile navigation.

### Task 4: Verification And Deployment

**Files:**
- All modified files.

- [ ] Run targeted tests with the reusable venv Python.
- [ ] Run full server test suite after deployment.
- [ ] If browser verification is needed, run `agent-browser close` immediately after screenshots/checks and confirm the CDP port is gone.
