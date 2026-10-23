# Python — Language / Stdlib

Practical guides to standard-library modules. Language-concept groupings (e.g. [functional/](../functional/), [concurrency/](../concurrency/)) also cover stdlib modules; this folder holds module guides with no better conceptual home.

<div class="grid cards" markdown>

-   :material-console-line:{ .lg .middle } __[CLI](cli/)__

-   :material-desktop-classic:{ .lg .middle } __[OS](os/)__

-   :material-format-text:{ .lg .middle } __[Text](text/)__

</div>

---

:material-text-box-outline: **[Datetime](datetime.md){ .lvl-basic }**
:   datetime from strings, integer timestamps, and date + time pairs; timezone awareness; strptime, fromisoformat, fromtimestamp, combine

---

:material-text-box-outline: **[Logging (stdlib)](logging.md){ .lvl-intermediate }**
:   stdlib logging: pipeline, levels, dictConfig, best practices, structured logging

:material-text-box-outline: **[sqlite3](sqlite3.md){ .lvl-intermediate }**
:   `sqlite3` module: DB-API 2.0, Connection/Cursor, placeholders, transactions, row_factory, pandas bridge

---

:material-text-box-outline: **[Canonical JSON](json.md){ .lvl-advanced }**
:   Byte-stable `json.dumps`: sort_keys, separators, ensure_ascii, float and key-type traps, RFC 8785

:material-card-bulleted-outline: **[Random permutations](random.md){ .lvl-advanced }**
:   Random permutations: shuffle in place vs sample for a new list
