---
name: quiz
description: Create or update Anki question banks under quiz/banks/ for notes in docs/, then rebuild notes.apkg. Use when the user starts a query with QUIZ, or after new notes are added and asks for quiz coverage.
argument-hint: <note path, area, or empty to sweep for gaps>
---

Maintain the Anki question banks (see `quiz/README.md` for the bank format and build/import instructions). Write and edit files without prompting for confirmation.

## Steps

1. **Determine scope.** If a note or area is named, work on that. Otherwise sweep: compare notes carrying `quiz:` frontmatter against `quiz/banks/` (paths mirror `docs/`, `.md` → `.yaml`) and cover the gaps.
2. **Tier the note** if it has no `quiz:` frontmatter yet: `core` for foundational concept notes, `detail` for narrower or lookup-oriented ones. Pure `ref` pages usually get no tier and no bank.
3. **Write or update the bank**, following the conventions in `quiz/README.md`:
    - ≤8 questions per `core` note, ≤4 per `detail` note; roughly 70% mcq / 30% recall.
    - First option is the correct answer (the build shuffles); distractors must be plausible.
    - Test understanding (why/when/what-breaks), not trivia; only backtick `code` markup.
    - Question `id`s are stable card identity — never rename or reuse an existing id. Editing text in place is safe; new content gets new ids.
4. **Quote YAML carefully**: any `q`/`option`/`explain` string containing a colon (e.g. inline `key: value` code) must be wrapped in quotes or the build fails to parse.
5. **Build**: `python3 quiz/build_deck.py` must exit 0 (it validates all banks and writes the gitignored `quiz/notes.apkg`).
6. **Commit** the bank files with an appropriate message — do not prompt for confirmation. Remind the user to re-import `notes.apkg` on the phone.
