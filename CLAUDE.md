# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo is a personal knowledge base. The user asks Claude to explain topics; Claude writes a detailed explanation to a temporary file for immediate reading, and a concise `.md` file capturing the key points for permanent reference.

## Workflow

I will ask you to explain a topic by starting the query with the uppercase string `EXPLAIN`. When asked to explain a topic:
1. **Write the detailed explanation to `_explain.md`** at the repo root — more depth than the permanent file, including intuition and context. Then immediately open it with `open _explain.md`. This file is gitignored and never committed.
2. **Review folder structure** (read the `README.md` files only) to understand whether a change in an existing file is needed vs. the creation of a new file or folder. Try to keep the number of files limited. That means either:
    a. Add the information to an exisitng file if makes sense; otherwise,
    b. Merge the new information with existing information into a new file.
   It is imperative to keep good logic in structuring the information.
3. **Write an `.md` file** in the appropriate directory. The file should be more succinct than the terminal explanation but still informative: prefer bullet points and short code examples over prose.
4. **Update `README.md`** in the relevant subdirectory and the root `README.md` if a new directory is created.
5. **Update other .md files** with appropriate links, only if needed. The aim is to maintain conceptual links between different topics.
6. **Commit changes** with an appropriate message — do not prompt for confirmation before committing.

During the EXPLAIN workflow, write new files, edit existing files, and save all changes without prompting for confirmation.

## File organisation

```
notes/
├── python/
│   ├── language/   — Core Python: data model, iterators, generators, exceptions, stdlib
│   └── tooling/    — pyenv, poetry, ruff, mypy, pydantic, pytest, testing strategy
├── git/            — Git workflows, commands, tags, releases, GitHub Actions
└── tools/          — Language-agnostic tools and notation (Mermaid, etc.)
```

Each subdirectory has a `README.md` table with three columns: **file**, **type** (`note` or `ref`), **one-line description**.

- `note` — narrative explanation of a concept (the "why" and "how")
- `ref` — command/syntax quick-reference meant for lookup

When adding a new file, add a row to the subdirectory `README.md`. When adding a new directory, add a row to the root `README.md`.

## Cross-linking

Link related files using relative markdown links. Prefer linking on the first meaningful mention of a topic (e.g. if `mypy.md` mentions Poetry, link it). Don't link every occurrence — once per file is enough.

## Note style

- Lead with what the thing is and why it matters, then how to use it.
- Short code examples are preferred over long ones.
- Use bullet points for lists of facts; use prose only for conceptual explanations.
- No multi-paragraph docstrings or wall-of-text sections.

## RESTRUCTURE workflow

I will ask you to restructure the project by starting the query with the uppercase string `RESTRUCTURE`. When asked to restructure:

1. **Survey the current structure cheaply**: read only the `README.md` files in each directory and run `wc -l` on every `.md` file to get line counts. Do **not** open individual note files unless their line count exceeds ~200 and you need to understand their content to split them sensibly.
2. **Identify problems**: flag any file with >200 lines and any folder with >10 files (excluding `README.md`).
3. **Propose a new structure** that resolves the problems by introducing subfolders. Requirements:
   - Group topics by logical criteria (e.g. language feature area, tool category) — never by arbitrary criteria like alphabetical order or file size alone.
   - Keep the total number of new folders minimal — only introduce a subfolder when it contains at least 3 files.
   - Files >200 lines may be split into two focused files; propose the split with a one-line rationale.
4. **Output both the old and the proposed structure as directory-tree diagrams in the terminal** (use `tree`-style ASCII art). Annotate each file with its line count and each folder with its file count.
5. **Do not move, rename, or create any file or folder yet.** Wait for explicit approval before acting.
6. **Ask for clarification** if a grouping decision is genuinely ambiguous (e.g. a file that belongs equally well in two places).

Once approved and the restructuring is executed:

7. **Update all README files** to reflect the new folder structure: add rows for new files/folders, remove rows for moved ones, and fix any table entries whose paths have changed.
8. **Update all cross-file hyperlinks** in every `.md` file to point to the new paths.
9. **Sort all README table rows alphabetically** by filename within each directory.
