# Regular Expressions (Regexp)

A regular expression (regexp, regex) describes a *pattern* in text — a shape
like "a sequence of digits" or "an optional prefix followed by three
letters" — that an engine scans a string to find. Formally, a regex describes
a **regular language**, the class recognized by a finite automaton (a finite
state machine (FSM) with no memory beyond its current state). That's the
theoretical reason regex can't match arbitrarily nested structure (balanced
parentheses, HTML tags) — nesting is context-free, a strictly more powerful
class requiring a stack.

## Core syntax

| Construct | Meaning |
|---|---|
| `.` | any character except newline |
| `[abc]`, `[a-z]`, `[^abc]` | character class / range / negation |
| `\d`, `\w`, `\s` | digit, word char, whitespace (uppercase = negated) |
| `^`, `$` | start / end of string (or line, in multiline mode) |
| `\b` | word boundary |
| `*`, `+`, `?` | 0+, 1+, 0-or-1 |
| `{n}`, `{n,m}` | exactly n / between n and m |
| `(...)` | capturing group |
| `(?:...)` | non-capturing group |
| `(?P<name>...)` | named capturing group (Python; `(?<name>...)` elsewhere) |
| `\|` | alternation ("or") |
| `\1` | backreference to group 1's matched text |

## Greedy vs. lazy quantifiers

Quantifiers are **greedy** by default: they consume as much as possible, then
backtrack only if needed. Appending `?` makes a quantifier **lazy**
(`*?`, `+?`, `{n,m}?`): it consumes as little as possible, expanding only if
the rest of the pattern requires it.

```text
input:  <a><b>
<.+>    -> "<a><b>"   (greedy: grabs everything, backs off minimally)
<.+?>   -> "<a>"      (lazy: grabs nothing, expands minimally)
```

!!! tip "Mental model"
    Greedy = grab everything, give back only what you must.
    Lazy = grab nothing, take only what you must.
    They differ exactly when multiple valid matches of different lengths
    exist — the classic "matching HTML tags" trap.

## Lookaround

Zero-width assertions that check adjacent text without consuming it:

- `(?=...)` / `(?!...)` — positive / negative lookahead
- `(?<=...)` / `(?<!...)` — positive / negative lookbehind

`\d+(?=px)` matches `"12"` in `"12px"` but not in `"12em"` — the `px` is
checked, not captured. Lookbehind traditionally must be fixed-length
(Python's [`re`](../python/language/stdlib/re.md) enforces this; some
engines like PCRE allow variable length), since the engine has to know how
far back to check.

## Backtracking vs. finite-automaton engines

- **Backtracking engines** (Python `re`, PCRE, Perl, JavaScript, Java) explore
  possibilities recursively, undoing choices that lead to failure. This
  supports backreferences and lookaround, but certain patterns can take
  **exponential** time — "catastrophic backtracking". A pattern like
  `(a+)+b` against a long run of `a`s with no trailing `b` explores every way
  of splitting the run between the two `+`s before failing. Applying such a
  pattern to attacker-controlled input is a real denial-of-service vector
  (ReDoS).
- **Finite-automaton engines** (RE2, Go `regexp`, Rust `regex`) compile the
  pattern into an actual state machine and simulate all states at once,
  guaranteeing linear time regardless of pattern — at the cost of dropping
  backreferences and lookaround, which need memory beyond "current state".

!!! warning "Untrusted patterns or input"
    If a pattern or its subject text is attacker-controlled, catastrophic
    backtracking is a genuine risk. Avoid nested quantifiers over the same
    class (`(a+)+`), use possessive quantifiers/atomic groups where
    available, set a match timeout, or use a linear-time engine (RE2) for
    untrusted patterns.

## Possessive quantifiers and atomic groups

PCRE and Java offer possessive quantifiers (`*+`, `++`, `?+`) — greedy, but
they never backtrack once matched — and atomic groups `(?>...)` for the same
effect on a subpattern. Both are a standard defense against catastrophic
backtracking. Python's `re` added them in 3.11.

## Practical guidance

- Compile a pattern once and reuse it if it runs in a loop.
- Prefer `(?:...)` over `(...)` when you don't need the captured text — it
  keeps group numbering stable.
- Anchor patterns (`^...$`, or a full-match API) — an unanchored pattern
  matches anywhere in the string, a common validation bug.
- Don't use regex for recursive/nested structures (HTML, JSON) — use a
  parser instead; regex is for flat, lexical pattern matching.

## Flavors at a glance

- **POSIX** (`grep`, `sed`, `awk`) — no `\d`/`\w`, no lookaround, no lazy
  quantifiers; alternation/groups need escaping unless in extended mode
  (`grep -E`).
- **PCRE** (Perl Compatible Regular Expressions) — the featureful,
  backtracking flavor most languages imitate (Python's `re`, JavaScript, Java).
- **RE2 / Go / Rust `regex`** — linear-time guaranteed; no backreferences or
  lookaround.
