# Quiz decks

Anki question banks generated from the notes under `docs/`, compiled into a single
`notes.apkg` for spaced-repetition review on the phone (AnkiMobile).

## Layout

- `banks/` — one YAML file per note, mirroring the `docs/` tree. These are the
  source of truth and are committed.
- `build_deck.py` — compiles all banks into `notes.apkg` (gitignored artifact).
- `requirements.txt` — build dependencies (`genanki`, `pyyaml`).

## Bank format

```yaml
note: python/tooling/testing/fixtures.md   # source note, relative to docs/
tier: core                                 # core | detail
questions:
  - id: fixture-scope-module               # stable slug — NEVER rename once created
    type: mcq                              # mcq | recall
    q: What does `scope="module"` mean?
    options:                               # 3-5 entries; FIRST one is the correct
      - Shared within a file               # answer (build shuffles display order)
      - New per test
      - Shared across the run
    explain: One-line reinforcement shown on the back.
  - id: why-yield-fixtures
    type: recall
    q: Why are yield fixtures preferred over addfinalizer?
    answer: Short model answer shown on the back.
```

Only backtick `code` markup is supported in text fields.

## Build and import

```bash
pip3 install -r quiz/requirements.txt   # once
python3 quiz/build_deck.py              # writes quiz/notes.apkg
```

Import: AirDrop `notes.apkg` to the phone and open it in AnkiMobile, or import in
Anki desktop and sync via AnkiWeb.

Card identity is stable across rebuilds (guid = bank path + question id), so
re-importing an updated deck edits cards in place and **preserves scheduling
history**. Renaming a question `id` or moving a bank file creates a new card —
don't do it to existing questions.

## Conventions

- Question volume: ≤8 per `core` note, ≤4 per `detail` note; roughly 70% mcq / 30% recall.
- Questions test understanding, not trivia; distractors must be plausible.
- Card tags: tier (`core`/`detail`) + top-level area (`python`, `data`, …) for
  filtered decks in Anki.
- The `QUIZ` workflow (see `.claude/skills/quiz/`) maintains these banks.
