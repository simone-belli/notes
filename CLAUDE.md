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
| `RESTRUCTURE` (or `RESTRUCTURE DEEP`) | `/restructure` | Survey structure (`DEEP`: whole taxonomy top-down), propose reorganisation, execute after approval |
| `AUDIT` | `/audit` | Check notes for stale claims, fix after approval |
| `QUIZ` | `/quiz` | Create/update question banks in `quiz/banks/`, rebuild web quiz data |

## Autonomy

This repo is a personal knowledge base, not production code — reading and writing files locally is cheap and reversible via git. Work autonomously and don't ask for confirmation to:

- Read, search, or list any file in the repo.
- Create, write, or edit notes, `README.md` tables, and `_explain.md` files.
- Run read-only commands (`mkdocs build --strict`, `git status`, `git diff`, etc.).

Only pause to ask when the action is genuinely hard to undo or outward-facing: pushing to the remote, deleting many files at once, or a structural change (`RESTRUCTURE`, large `AUDIT` fix) where the skill calls for approval before executing. Commit when a skill says to. Before any commit that touches `docs/`, run `mkdocs build --strict` — it must exit 0.

## File organisation

All notes live under `docs/`; the repo root contains only tooling files (`mkdocs.yml`, `CLAUDE.md`, `README.md`, `.gitignore`, `.github/`, `.claude/`). Top-level areas: `data/` (numpy, pandas), `dsa/`, `finance/`, `git/`, `python/` (`language/` and `tooling/`), and `tools/`. Subfolders evolve — consult the `README.md` files for the current layout rather than assuming it.

Each subdirectory has a `README.md` listing its children, sorted alphabetically by filename. Entries carry a **type**:

- `note` — narrative explanation of a concept (the "why" and "how")
- `ref` — command/syntax quick-reference meant for lookup

Every entry links to a child page (or subdirectory) by its **title**, not its filename, and the icon encodes the type: `:material-folder-outline:` for a subdirectory, `:material-text-box-outline:` for a `note`, `:material-card-bulleted-outline:` for a `ref`. The title is the child's H1; for a subdirectory use the short last segment of its breadcrumb H1 (e.g. `Python — Language / Concurrency` → **Concurrency**), and trim any leading breadcrumb prefix that just repeats the current page's context (on the Pandas page, `Pandas — Iteration` → **Iteration**). The link target is still the file/directory path.

Two layouts are used, both without a `## Structure` section (the MkDocs sidebar handles navigation):

- **Section hubs** — `docs/index.md` and the seven top-level area READMEs (`data/`, `dsa/`, `finance/`, `git/`, `python/`, `sql/`, `tools/`) use a Material **grid of cards** (requires the `attr_list`, `md_in_html`, and `pymdownx.emoji` extensions). One card per child: `icon + linked title + one-line description`, separated by a `---` divider.
- **Deeper subdirectory READMEs** use a **description list** (requires the `def_list` extension): each entry is a term line `icon + **[title](path)**` followed by a `:   one-line description` line, entries separated by a blank line.

When adding a new file, add an entry to the parent `README.md` in whichever layout that page uses (a card on a section hub, a description-list entry deeper down), keeping entries sorted alphabetically by filename. When adding a new top-level area under `docs/`, add a card to `docs/index.md`.

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
- Expand every acronym in full on its first use in each document (including `_explain.md`), e.g. "Abstract Syntax Tree (AST)". Exempt (never need expansion — expanding them is noise): `API`, `CLI`, `CPU`, `CSV`, `GPU`, `HTML`, `HTTP`, `HTTPS`, `ID`, `JSON`, `OS`, `RAM`, `SQL`, `TSV`, `URL`, `UTF`, `YAML`. Everything else — especially domain- or library-specific initialisms like `ORM`, `ASGI`, `GIL`, `AST`, `ADT` — gets expanded on first use. The rule targets substantive page content; skip terse navigation contexts — `README` card/description/title lines and *Related* / *See also* link lists — where the acronym is only a pointer and the linked page carries the expansion.
- The repo and site are public: never include personal identifiers, real credentials, real account data, or local filesystem paths in notes — use placeholder values in examples.
