# Quiz banks

Question banks generated from the notes under `docs/`, reviewed with spaced
repetition in the web quiz app at
[`/quiz/`](https://bellinquente-a11y.github.io/notes/quiz/) on the published
site (works in any browser — add it to the phone home screen for an app-like
experience). No Anki or paid apps involved.

## Layout

- `banks/` — one YAML file per note, mirroring the `docs/` tree. These are the
  source of truth and are committed.
- `build_web.py` — validates all banks and compiles them into
  `docs/quiz/data.json` (gitignored artifact, consumed by the app).
- `../docs/quiz/index.html` — the quiz app: a single self-contained HTML file
  with SM-2 spaced-repetition scheduling; progress lives in the browser's
  `localStorage`, with export/import buttons for backup. Sessions are capped by
  a "Questions per session" setting (0 = no limit) and ordered
  recently-wrong → unseen → previously-correct, so the cap trims already-known
  cards first.
- `requirements.txt` — build dependency (`pyyaml`).

## Bank format

```yaml
note: python/tooling/testing/fixtures.md   # source note, relative to docs/
tier: core                                 # core | detail
questions:
  - id: fixture-scope-module               # stable slug — NEVER rename once created
    type: mcq                              # mcq | recall
    q: What does `scope="module"` mean?
    options:                               # 3-5 entries; FIRST one is the correct
      - Shared within a file               # answer (the app shuffles display order)
      - New per test
      - Shared across the run
    explain: One-line reinforcement shown after answering.
  - id: why-yield-fixtures
    type: recall
    q: Why are yield fixtures preferred over addfinalizer?
    answer: Short model answer shown on reveal.
```

Only backtick `code` markup is supported in text fields.

## Build and review

```bash
pip3 install -r quiz/requirements.txt   # once
python3 quiz/build_web.py               # writes docs/quiz/data.json
```

The GitHub Actions docs workflow runs the same build before `mkdocs build`, so
pushing to `main` publishes the updated questions automatically — nothing to
sync or re-import.

Card identity is stable across rebuilds (scheduling state is keyed by
`bank path + question id`), so editing question text in place **preserves
scheduling history**. Renaming a question `id` or moving a bank file creates a
new card — don't do it to existing questions.

Review progress is stored per browser in `localStorage`; use the app's
Export/Import buttons to back it up or move it between devices.

## Conventions

- Question volume: ≤8 per `core` note, ≤4 per `detail` note; roughly 70% mcq / 30% recall.
- Questions test understanding, not trivia; distractors must be plausible.
- Cards inherit their tier (`core`/`detail`) and top-level area (`python`,
  `data`, …) from the bank; the app filters on both, plus on question type
  (MCQ / open).
- The `QUIZ` workflow (see `.claude/skills/quiz/`) maintains these banks.
