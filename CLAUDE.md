# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo is a personal knowledge base. The user asks Claude to explain topics; Claude writes a detailed explanation to a temporary file for immediate reading, and a concise `.md` file capturing the key points for permanent reference.

## Workflows

The workflows live as project skills in `.claude/skills/`. When a query starts with one of these uppercase keywords, invoke the corresponding skill:

| Keyword | Skill | What it does |
|---------|-------|--------------|
| `EXPLAIN` (or `EXPLAIN BRIEFLY`) | `/explain` | Deep dive to `_explain.md` + permanent note |
| `ADD TOPIC` | `/add-topic` | Concise note only, no `_explain.md` |
| `RESTRUCTURE` | `/restructure` | Survey structure, propose reorganisation, execute after approval |
| `AUDIT` | `/audit` | Check notes for stale claims, fix after approval |
| `QUIZ` | `/quiz` | Create/update Anki question banks in `quiz/banks/`, rebuild deck |

During these workflows, write and edit files without prompting for confirmation, and commit when the skill says to. Before any commit that touches `docs/`, run `mkdocs build --strict` — it must exit 0.

## File organisation

All notes live under `docs/`; the repo root contains only tooling files (`mkdocs.yml`, `CLAUDE.md`, `README.md`, `.gitignore`, `.github/`, `.claude/`). Top-level areas: `data/` (numpy, pandas), `dsa/`, `finance/`, `git/`, `python/` (`language/` and `tooling/`), and `tools/`. Subfolders evolve — consult the `README.md` files for the current layout rather than assuming it.

Each subdirectory has a `README.md` with a table of three columns: **file**, **type** (`note` or `ref`), **one-line description**, sorted alphabetically by filename. Do not include a `## Structure` section — the MkDocs sidebar handles navigation.

- `note` — narrative explanation of a concept (the "why" and "how")
- `ref` — command/syntax quick-reference meant for lookup

When adding a new file, add a row to the subdirectory `README.md`. When adding a new directory under `docs/`, add a row to `docs/index.md`.

## Cross-linking

Link related files using relative markdown links. Prefer linking on the first meaningful mention of a topic (e.g. if `mypy.md` mentions Poetry, link it). Don't link every occurrence — once per file is enough.

## Tags

Notes carry frontmatter tags for cross-cutting themes (rendered by the Material tags plugin; index at `docs/tags.md`):

```yaml
---
tags:
  - testing
---
```

- Controlled vocabulary — use only: `cli`, `concurrency`, `config`, `design-patterns`, `errors`, `logging`, `packaging`, `performance`, `testing`, `typing`.
- 0–3 tags per note; only where the theme genuinely applies. Many notes need no tags.
- Extend the vocabulary only when at least 3 notes would carry the new tag; update this list when you do.

## Note style

- Lead with what the thing is and why it matters, then how to use it.
- Short code examples are preferred over long ones.
- Use bullet points for lists of facts; use prose only for conceptual explanations.
- No multi-paragraph docstrings or wall-of-text sections.
- Use MkDocs admonition boxes (`!!! note`, `!!! tip`, `!!! warning`) to highlight key concepts — mental models, common pitfalls, or non-obvious distinctions worth calling out. Aim for 2–3 per page; don't use them for routine information that flows naturally as prose or bullets.
- Expand every acronym in full on its first use in each document (including `_explain.md`), e.g. "Abstract Syntax Tree (AST)".
- The repo and site are public: never include personal identifiers, real credentials, real account data, or local filesystem paths in notes — use placeholder values in examples.
