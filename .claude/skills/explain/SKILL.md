---
name: explain
description: Deep-dive a topic into _explain.md and capture a concise permanent note under docs/. Use when the user starts a query with EXPLAIN, or asks for a topic to be explained and added to the knowledge base. EXPLAIN BRIEFLY means keep both outputs short.
argument-hint: <topic> [BRIEFLY]
---

Explain the given topic and capture it in the knowledge base. Follow the note style, cross-linking, and tag rules in CLAUDE.md throughout. Write and edit files without prompting for confirmation.

Keep the explanation general and conceptual — describe the topic itself, not how it happens to be used in any of the user's local projects. Do not read files from other local repositories or codebases for context; work from general knowledge. Only look at another local project if the user explicitly asks you to.

## Steps

1. **Write the detailed explanation to `_explain.md`** at the repo root — more depth than the permanent file, including intuition and context. Then immediately open it with `open _explain.md`. This file is gitignored and never committed. If the query says `BRIEFLY`, keep it concise.
2. **Review folder structure** (read the `README.md` files only) to decide whether the information belongs in an existing file or a new one. Keep the number of files limited: prefer adding a section to an existing file; otherwise merge related information into one new file. Never create a file that overlaps an existing note — extend or restructure the existing one instead.
3. **Write the `.md` note** in the appropriate directory — more succinct than `_explain.md` but still informative: bullet points and short code examples over prose. Short title. Add frontmatter `tags:` from the controlled vocabulary in CLAUDE.md (0–3, only where they genuinely apply).
4. **Update `README.md`** in the relevant subdirectory (add a row, keep the table alphabetical by filename). If a new directory was created, add a row to `docs/index.md`.
5. **Update other `.md` files** with relative links where a conceptual connection exists — first meaningful mention only.
6. **Verify** with `mkdocs build --strict` (must exit 0).
7. **Commit** with an appropriate message — do not prompt for confirmation.
