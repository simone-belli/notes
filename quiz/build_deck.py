#!/usr/bin/env python3
"""Compile quiz/banks/**/*.yaml into a single Anki package (quiz/notes.apkg).

Bank format: one YAML file per note, mirroring the docs/ tree. See quiz/README.md.

Stability guarantees (what keeps Anki scheduling history intact across rebuilds):
- model and deck IDs are deterministic constants/hashes, never random per build
- each card's guid derives from (bank path, question id) via genanki.guid_for
- MCQ option order is shuffled with a RNG seeded on the question id
Therefore: re-importing a rebuilt .apkg updates card content in place; renaming a
question id or moving a bank file creates a NEW card and orphans the old one.
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

import genanki
import yaml

ROOT = Path(__file__).resolve().parent
BANKS_DIR = ROOT / "banks"
OUT_FILE = ROOT / "notes.apkg"
SITE_URL = "https://bellinquente-a11y.github.io/notes"
ROOT_DECK = "Notes"

MCQ_MODEL_ID = 1626061000
RECALL_MODEL_ID = 1626061001

CSS = """
.card { font-family: -apple-system, sans-serif; font-size: 19px;
        text-align: left; color: #222; background: #fff; padding: 6px; }
.q { font-weight: 600; margin-bottom: 12px; }
ol.opts { list-style-type: upper-alpha; padding-left: 28px; }
ol.opts li { margin: 6px 0; }
li.correct { font-weight: 700; color: #1a7f37; }
.explain { margin-top: 10px; }
.src { margin-top: 14px; font-size: 15px; }
code { font-size: 90%; background: #f2f2f2; padding: 1px 4px; border-radius: 3px; }
"""

MCQ_MODEL = genanki.Model(
    MCQ_MODEL_ID,
    "KB MCQ",
    fields=[
        {"name": "Question"},
        {"name": "Options"},        # <ol> without the answer marked
        {"name": "OptionsSolved"},  # same <ol> with the correct <li> highlighted
        {"name": "Explain"},
        {"name": "Source"},
    ],
    templates=[
        {
            "name": "MCQ",
            "qfmt": '<div class="q">{{Question}}</div><ol class="opts">{{Options}}</ol>',
            "afmt": (
                '<div class="q">{{Question}}</div>'
                '<ol class="opts">{{OptionsSolved}}</ol>'
                '<hr><div class="explain">{{Explain}}</div>'
                '<div class="src">{{Source}}</div>'
            ),
        }
    ],
    css=CSS,
)

RECALL_MODEL = genanki.Model(
    RECALL_MODEL_ID,
    "KB Recall",
    fields=[
        {"name": "Question"},
        {"name": "Answer"},
        {"name": "Source"},
    ],
    templates=[
        {
            "name": "Recall",
            "qfmt": '<div class="q">{{Question}}</div>',
            "afmt": (
                '{{FrontSide}}<hr>{{Answer}}'
                '<div class="src">{{Source}}</div>'
            ),
        }
    ],
    css=CSS,
)


def deck_id_for(name: str) -> int:
    digest = hashlib.sha256(name.encode()).hexdigest()
    return (int(digest[:15], 16) % (1 << 30)) + (1 << 30)


def md_inline(text: str) -> str:
    """Minimal markdown-to-HTML: `code` spans only (banks use no other markup)."""
    out, parts = [], str(text).split("`")
    for i, part in enumerate(parts):
        part = part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.append(f"<code>{part}</code>" if i % 2 else part)
    return "".join(out)


def note_url(note_path: str) -> str:
    return f"{SITE_URL}/{note_path.removesuffix('.md')}/"


def load_bank(path: Path) -> dict:
    bank = yaml.safe_load(path.read_text())
    rel = path.relative_to(BANKS_DIR).as_posix()
    for key in ("note", "tier", "questions"):
        if key not in bank:
            sys.exit(f"{rel}: missing top-level key '{key}'")
    if bank["tier"] not in ("core", "detail"):
        sys.exit(f"{rel}: tier must be core|detail, got {bank['tier']!r}")
    seen = set()
    for q in bank["questions"]:
        qid = q.get("id")
        if not qid or qid in seen:
            sys.exit(f"{rel}: missing or duplicate question id {qid!r}")
        seen.add(qid)
        if q.get("type") not in ("mcq", "recall"):
            sys.exit(f"{rel}:{qid}: type must be mcq|recall")
        if q["type"] == "mcq" and not (3 <= len(q.get("options", [])) <= 5):
            sys.exit(f"{rel}:{qid}: mcq needs 3-5 options (first = correct)")
        if q["type"] == "recall" and not q.get("answer"):
            sys.exit(f"{rel}:{qid}: recall needs an answer")
        if not q.get("q"):
            sys.exit(f"{rel}:{qid}: missing question text 'q'")
    return bank


def build_note(bank: dict, bank_rel: str, q: dict) -> genanki.Note:
    guid = genanki.guid_for(bank_rel, q["id"])
    area = bank_rel.split("/")[0]
    tags = [bank["tier"], area]
    source = f'<a href="{note_url(bank["note"])}">{bank["note"]}</a>'

    if q["type"] == "recall":
        return genanki.Note(
            model=RECALL_MODEL, guid=guid, tags=tags,
            fields=[md_inline(q["q"]), md_inline(q["answer"]), source],
        )

    options = [md_inline(o) for o in q["options"]]
    order = list(range(len(options)))
    random.Random(q["id"]).shuffle(order)
    plain = "".join(f"<li>{options[i]}</li>" for i in order)
    solved = "".join(
        f'<li class="correct">{options[i]}</li>' if i == 0 else f"<li>{options[i]}</li>"
        for i in order
    )
    return genanki.Note(
        model=MCQ_MODEL, guid=guid, tags=tags,
        fields=[md_inline(q["q"]), plain, solved, md_inline(q.get("explain", "")), source],
    )


def main() -> None:
    bank_paths = sorted(BANKS_DIR.rglob("*.yaml"))
    if not bank_paths:
        sys.exit(f"no banks found under {BANKS_DIR}")

    decks: dict[str, genanki.Deck] = {}
    n_cards = 0
    for path in bank_paths:
        rel = path.relative_to(BANKS_DIR).as_posix()
        bank = load_bank(path)
        deck_name = "::".join([ROOT_DECK, *rel.split("/")[:-1]])
        deck = decks.setdefault(deck_name, genanki.Deck(deck_id_for(deck_name), deck_name))
        for q in bank["questions"]:
            deck.add_note(build_note(bank, rel, q))
            n_cards += 1

    genanki.Package(sorted(decks.values(), key=lambda d: d.name)).write_to_file(OUT_FILE)
    print(f"wrote {OUT_FILE.name}: {n_cards} cards in {len(decks)} decks from {len(bank_paths)} banks")
    for name in sorted(decks):
        print(f"  {name}: {len(decks[name].notes)} cards")


if __name__ == "__main__":
    main()
