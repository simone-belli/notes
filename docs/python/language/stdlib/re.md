# `re` — Regular Expressions

Python's `re` module matches [regex patterns](../../../tools/regexp.md)
against strings (or `bytes`). It's a **backtracking** engine, so everything
about catastrophic backtracking applies directly — `re` has no built-in
match timeout.

## Core functions

```python
import re

re.match(pat, s)      # anchored at the START of s
re.fullmatch(pat, s)  # must consume ALL of s
re.search(pat, s)     # first match anywhere in s
re.findall(pat, s)    # list of all matches
re.finditer(pat, s)   # lazy iterator of Match objects
re.sub(pat, repl, s)  # substitute, return new string
re.split(pat, s)      # split on pattern
```

!!! warning "match vs. fullmatch for validation"
    `re.match(r"\d+", "123abc")` succeeds — it only checks a *prefix*. Use
    `re.fullmatch` when validating that an entire string conforms to a
    format.

## Match objects

```python
m = re.search(r"(?P<year>\d{4})-(?P<month>\d{2})", "2024-03")
m.group(0)       # "2024-03" (whole match)
m.group("year")  # "2024" (named group)
m.groupdict()    # {"year": "2024", "month": "03"}
m.span("year")   # (0, 4) — index range of that group
```

A failed match returns `None`; a successful match returns a `Match` object
that is always truthy (even zero-length) — check `is None`, not truthiness
of the match's content. An unmatched optional group returns `None` from
`.group(n)` rather than raising.

## Compiling

```python
pattern = re.compile(r"\d+", re.IGNORECASE)
pattern.findall(s)
```

`re.compile` returns a reusable `Pattern`; module-level calls like
`re.search(p, s)` compile internally and cache the last ~512 patterns. Still
prefer explicit `compile()` for patterns used in loops or across functions —
clearer intent, no reliance on cache size.

## Flags

| Flag | Inline | Effect |
|---|---|---|
| `re.IGNORECASE` | `(?i)` | case-insensitive |
| `re.MULTILINE` | `(?m)` | `^`/`$` match per line |
| `re.DOTALL` | `(?s)` | `.` also matches newline |
| `re.VERBOSE` | `(?x)` | ignore whitespace/`#` comments in the pattern |
| `re.ASCII` | `(?a)` | `\d`/`\w`/`\s` restricted to ASCII |

Python strings are Unicode, so `\w`/`\d` match non-ASCII letters/digits by
default — use `re.ASCII` to force byte-oriented matching.

## Substitution and splitting

```python
re.sub(r"\s+", " ", "a  b\tc")                  # "a b c"
re.sub(r"\d+", lambda m: str(int(m[0]) * 2), s) # callable replacement
re.split(r"(\s+)", "a  b")                       # ['a', '  ', 'b'] — group kept
```

`re.sub`'s replacement can reference groups (`r"\1"`, `r"\g<name>"`) or be a
callable that receives the `Match` and returns a string. `re.split` includes
captured separator text in the result if the pattern has a capturing group.

## `re.escape`

```python
re.escape("3.14 (pi)")   # r'3\.14\ \(pi\)'
```

Always wrap literal/user-supplied text with `re.escape` before splicing it
into a larger pattern — otherwise its regex metacharacters are interpreted,
which is a correctness bug and, with untrusted input, a potential
[ReDoS](../../../tools/regexp.md) vector.

!!! tip "Always use raw strings"
    `r"\d+"`, not `"\d+"` — plain strings run Python's own escape processing
    first, so e.g. `\b` (regex word boundary) silently becomes a backspace
    character instead.

## Python-specific notes

- 3.11 added **possessive quantifiers** (`*+`, `++`, `?+`) and **atomic
  groups** (`(?>...)`) — both block backtracking into the matched portion,
  a standard defense against catastrophic backtracking.
- The third-party `regex` package extends `re` with variable-length
  lookbehind, recursive patterns, and better Unicode support, for when
  `re`'s feature set is insufficient.
- `re.Pattern` / `re.Match` are the public type-hint names (Python 3.8+),
  e.g. `def f(m: re.Match[str]) -> str: ...`.
