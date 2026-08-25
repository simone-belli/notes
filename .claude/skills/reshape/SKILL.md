---
name: reshape
description: Break a note's wall-of-text prose into sections and subsections without rewriting its content. Use when the user starts a query with RESHAPE, or says a page has large blocks of text.
argument-hint: "[path or topic — default: scan docs/ for the worst offenders]"
disable-model-invocation: true
---

Fix the *layout* of an existing note: long prose runs become `##`/`###`
sections, digressions become admonitions, fact-lists become bullets. This is a
structural pass over one page's body — for moving files between folders or
splitting a file in two, use `/restructure` instead.

**Reshape, don't rewrite.** The wording is already approved; the diff should be
almost entirely added headings, moved blocks, and prose→bullet conversions. If
a sentence has to change to survive the move (a "this" that no longer has an
antecedent, a transition like "the same goes for…" stranded under a new
heading), change just that sentence. Resist the urge to improve prose you were
not asked to touch — an unreviewable diff is the failure mode here.

## Scope

- If the user gives a path or topic, reshape those notes.
- Otherwise scan and report the worst offenders, then reshape the top few:

```bash
awk -f .claude/skills/reshape/find-walls.awk \
  $(find docs -name '*.md' -not -name 'README.md' -not -name 'index.md' | sort)
```

The helper flags a page with a run of ≥3 prose paragraphs spanning ≥12 lines
and no visual break, or any page over 40 lines with no `##`. Add `-v verbose=1`
to see every file's numbers rather than only the hits. It measures layout, not
quality — always read a flagged page before deciding it needs work, and say so
when a flagged page is fine as it stands.

## How to section a page

1. **Leave the lead alone.** The paragraph before the first heading says what
   the thing is and why it matters. Never put a heading above it, and never
   let it grow past ~5 lines — surplus material moves down into a section or
   into an admonition, it doesn't stay up top.
2. **Cut where the subject changes**, not every N lines. Each `##` should be
   answerable as "what is this section about?" in one noun phrase.
3. **Name the heading after the thing**, matching how the reader would search
   for it: `## dvc.lock`, `## Anatomy of a stage`, `## Where the file goes`.
   Short — a concept name, never an enumeration of what's inside.
4. **A section needs substance**: two-plus sentences, or a code block, or a
   list. A heading over a single sentence adds navigation noise, so merge it
   into a neighbour instead.
5. **Add `###` only for genuinely parallel parts** — two or more siblings of
   comparable weight under one `##`. One `###` alone under a `##` means the
   `##` was mis-drawn.
6. **Keep `## Related` last.**

## What to convert while you're there

- **A paragraph that is really a list of facts** → bullets. Prose is for
  conceptual explanation; enumerated behaviour reads better as a list
  (CLAUDE.md note style).
- **An aside, analogy, or mental model padding out a paragraph** → a
  `!!! note` / `!!! tip` / `!!! warning`. This is usually the single biggest
  win: the digression stays available but stops interrupting the argument.
  Target 2–3 admonitions per page, per CLAUDE.md — count what's already there
  before adding more.
- **A paragraph explaining a code block that follows it** → keep it adjacent to
  the block; don't let a heading separate them.

## Finish

1. **New headings mean new anchors.** Existing deep links keep pointing at the
   old ones, so check for inbound anchor links to any page you reshaped and fix
   them: `grep -rn "<basename>\.md#" docs/`.
2. **Update the parent `README.md` description** if the reshape changed what the
   page visibly covers (it usually doesn't — the content is the same).
3. **Verify** with `mkdocs build --strict` (must exit 0). Its output also lists
   links pointing at anchors that don't exist — read those lines for the pages
   you touched.
4. **Commit** without prompting. Reshaping is cheap and git-reversible; don't
   ask for approval to lay out a page.
