---
tags:
  - cli
---

# jq — formatting & querying JSON

APIs return JSON as one unbroken line — fine for machines, unreadable for humans. **`jq`** is the de-facto tool to fix that: a command-line JSON processor that both **pretty-prints** and **queries/transforms** JSON. It reads JSON on stdin, applies a *filter*, and writes to stdout — a natural [pipe](shell/zsh.md) partner for [curl](web/curl.md). Install it: `brew install jq` / `apt install jq`.

!!! tip "Two habits cover 90%"
    **`| jq`** pretty-prints anything; **`| jq -r '<path>'`** pulls one value out as plain text. Everything else is refinement.

## Pretty-print

```bash
curl -s https://api.example.com/ticker | jq        # indent + colourise
curl -s https://api.example.com/ticker | jq .      # '.' = identity filter (same thing)
```

`jq` with no filter defaults to `.` (the **identity filter** — the whole input unchanged). It colourises to a terminal and auto-drops colour when piped to a file; force with `-C`, disable with `-M`.

## Accessing fields

```bash
echo '{"symbol":"BTC","price":42000}' | jq '.price'   # 42000
echo '{"user":{"name":"me"}}'         | jq '.user.name'
echo '{"tags":["a","b","c"]}'         | jq '.tags[0]'  # "a"
echo '{"tags":["a","b","c"]}'         | jq '.tags[]'   # a b c  (separate outputs)
```

- `.foo` / `.foo.bar` — value at a key / nested.
- `.[0]` — index into an array.
- `.[]` — **iterate**: emit each array element (or object value) as a *separate* output; the workhorse for lists.
- `.foo?` — suppress the error if `.foo` is missing.

Always **single-quote** the filter so the shell doesn't expand `$`, `[]`, `*`.

## The internal pipe

`jq` has its own `|`, separate from the shell's — feed one filter into the next:

```bash
curl -s .../trades | jq '.trades[] | .price'       # "for each trade, take its price"
```

## Filter & reshape

```bash
jq '.[] | select(.price > 40000)'        # WHERE-style filter
jq '.[] | select(.symbol == "BTC")'
jq '.[] | {sym: .symbol, p: .price}'     # build a trimmed object per element
jq '{symbol, price}'                      # shorthand: {symbol} == {symbol: .symbol}
jq '[.[] | .price]'                       # collect a stream back into one array
```

- `select(cond)` keeps inputs where `cond` is true.
- `{}` constructs an object, `[ ... ]` re-gathers a `.[]` stream into an array.

## Raw output: `-r`

By default strings print **quoted** (`"BTC"`). `-r` strips the quotes — essential when feeding values to other commands or building text:

```bash
jq -r '.symbol'                          # BTC   (not "BTC")
jq -r '.[] | "\(.symbol): \(.price)"'    # BTC: 42000   — \(...) is interpolation
```

## Useful built-ins

```bash
jq 'keys'            # sorted keys of an object
jq 'length'          # array length / key count / string length
jq 'map(.price)'     # map(f) == [.[] | f]
jq 'sort_by(.price)' # sort array by a field
jq 'group_by(.sym)'  # group array elements
jq 'add'             # sum numbers / concat arrays
jq -s 'add'          # -s "slurp": read the whole input stream into one array first
```

`-s` / `--slurp` is handy over a stream of separate JSON values (e.g. [JSON Lines](../python/libraries/jsonl.md)).

!!! warning "`Cannot index array with \"foo\"`"
    You used `.foo` on an array — you need `.[].foo` (every element) or `.[0].foo` (the first).

## No-install pretty-printers

When you only need indentation and `jq` isn't available:

```bash
curl -s .../x | python3 -m json.tool               # stdlib, everywhere Python is
curl -s .../x | python3 -m json.tool --sort-keys
echo '{"a":1}' | json_pp                           # Perl, preinstalled on many systems
```

These also **validate** — invalid JSON exits non-zero with a parse error.

## Other tools

- **`yq`** — `jq` syntax over YAML/XML/TOML, and converts between them.
- **`fx`** — interactive JSON viewer: fold/expand a tree in the terminal.
- **`gron`** — flattens JSON to `path = value;` lines so you can `grep` it; `gron -u` reverses it.

## Related

- [curl](web/curl.md) — produces the JSON you pipe into `jq`
- [HTTP Requests](web/http-request.md) — the request behind the response you're formatting
- [JSON Lines (JSONL)](../python/libraries/jsonl.md) — streams of JSON values; pair with `jq -s`
