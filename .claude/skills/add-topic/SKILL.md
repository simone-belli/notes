---
name: add-topic
description: Capture an already-understood topic as a concise note in the knowledge base — no _explain.md deep dive. Use when the user starts a query with ADD TOPIC.
argument-hint: <topic>
---

Capture the given topic directly in the knowledge base — the user already understands it broadly; no `_explain.md` is generated. Follow the note style, cross-linking, and tag rules in CLAUDE.md. Write and edit files without prompting for confirmation.

Keep the note general and conceptual — describe the topic itself, not how it happens to be used in any of the user's local projects. Do not read files from other local repositories or codebases for context; work from general knowledge. Only look at another local project if the user explicitly asks you to.

## Steps

1. **Review folder structure** (read the `README.md` files only) to find the right location. Prefer adding a section to an existing file over creating a new one.
2. **Write a concise `.md` note** (or extend an existing file): bullet points and short code examples, no prose explanations. Add frontmatter `tags:` from the controlled vocabulary in CLAUDE.md (0–3, only where they genuinely apply).
3. **Update `README.md`** in the relevant subdirectory (add a row, keep the table alphabetical by filename). If a new directory was created, add a row to `docs/index.md`.
4. **Update other `.md` files** with relative links, only where a conceptual connection exists.
5. **Verify** with `mkdocs build --strict` (must exit 0).
6. **Commit** with an appropriate message — do not prompt for confirmation.
