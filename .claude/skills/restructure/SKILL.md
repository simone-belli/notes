---
name: restructure
description: Survey the knowledge base for oversized files and folders, propose a reorganisation, and execute it after approval. RESTRUCTURE DEEP instead reviews the whole taxonomy top-down. Use when the user starts a query with RESTRUCTURE or asks to reorganise the notes.
argument-hint: "[DEEP]"
disable-model-invocation: true
---

Reorganise the knowledge base. This skill has two phases: a proposal (always stops for approval) and execution (only after explicit approval).

There are two survey modes. The default mode (below) is bottom-up: it finds local size problems. `RESTRUCTURE DEEP` is top-down: it reviews the whole taxonomy regardless of size — see **DEEP mode** after Phase 1.

## Phase 1 — Survey and propose

1. **Survey cheaply**: read only the `README.md` files in each directory and run `wc -l` on every `.md` file. Do **not** open individual note files unless their line count exceeds ~200 and you need their section headings (`grep '^## '`) to propose a sensible split.
2. **Identify problems**: flag any file >200 lines, any folder with >10 files (excluding `README.md`), and any folder holding more files than its own parent.
3. **Propose a new structure** that resolves the problems:
   - Group topics by logical criteria (language feature area, tool category) — never by arbitrary criteria like alphabetical order or file size alone.
   - Only introduce a subfolder when it will contain at least 3 files; keep new folders minimal.
   - Files >200 lines *may* be split into two focused files — propose each split with a one-line rationale, and explicitly list oversized files you recommend leaving intact (e.g. coherent single-topic refs) with a reason.
4. **Output both the old and proposed structures as directory-tree diagrams** (tree-style ASCII). Annotate files with line counts and folders with file counts. Unchanged subtrees may be collapsed to one annotated line.
5. **Do not move, rename, or create anything yet.** End the turn awaiting explicit approval.
6. **Ask for clarification** if a grouping decision is genuinely ambiguous (a file that belongs equally well in two places) — fold the question into the proposal.

## DEEP mode (`RESTRUCTURE DEEP`)

Replaces steps 1–3 of Phase 1; steps 4–6 and Phase 2 apply unchanged.

1. **Survey the taxonomy cheaply**: read `docs/index.md` and every `README.md` (file descriptions). Open individual notes only where a file's right category is genuinely ambiguous from its description.
2. **Evaluate top-down**, in order: (a) are the top-level areas right? (b) is each subcategory boundary principled — grouped consistently by concept, by library, or by activity, not a mix? (c) does each nesting level earn its depth? (d) do sibling names form a coherent, non-overlapping set? (e) **has a subject outgrown its shelf?** A folder holding more files than its own parent, or ≥8 files while nested below the top level, has usually stopped being a sub-topic and become an area in its own right. Check whether its contents span several categories (a concept *and* a tool *and* a library); if so, promote it one level up rather than leaving it as an oversized leaf.
3. **Design the ideal tree from a blank slate** for the current content, then diff it against the actual tree. Propose only moves whose clarity benefit outweighs the churn (link updates, quiz-history resets). Explicitly list structures you considered and deliberately left alone, with reasons.
4. In the proposal output, additionally **list the quiz banks that would move** — each move resets that note's review-scheduling history, so the user must be able to veto individual moves.

## Phase 2 — Execute (after approval only)

7. Use `git mv` for moves so history is preserved. For splits, keep a short pointer or link in the source file to the extracted note.
8. **Mirror every docs move into `quiz/banks/`**: `git mv` the bank at the same relative path, and update its `note:` frontmatter field to the new docs-relative path. The first path segment of a bank is the quiz app's area filter, and moving a bank resets its cards' scheduling history (state is keyed by bank path).
9. **Update all README files**: rows for new files/folders, remove rows for moved ones, fix changed paths. New folders get their own `README.md` table.
10. **Update all cross-file links** in every `.md` file — both inbound links to moved files and outbound links inside them (relative depth changes).
11. **Sort all README table rows alphabetically** by filename within each directory.
12. **Rebuild the quiz web data** if any bank moved (see `quiz/README.md` for the build command).
13. **Verify** with `mkdocs build --strict` (must exit 0), then **commit** without prompting.
