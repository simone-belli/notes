---
tags:
  - config
---

# YAML

**YAML** ("YAML Ain't Markup Language") is a data serialization format built for hand-written config: `mkdocs.yml`, [GitHub Actions](../git/github-actions.md) workflows, `docker-compose.yml`, Kubernetes manifests, [DVC](../ml/dvc/README.md) pipelines, and [Markdown](markdown.md) frontmatter all use it. YAML 1.2 is a strict superset of JSON — it adds an indentation-based syntax that drops the braces, quotes, and commas.

!!! tip "Mental model"
    Every YAML file is a tree of exactly three node kinds: **scalars** (`str`/`int`/`bool`/`null`), **sequences** (`list`), and **mappings** (`dict`). Any confusion is a question about which kind the parser inferred, at which indentation level.

## The three node kinds

```yaml
name: notes             # mapping: key → scalar
tags:                   # mapping: key → sequence
  - python
  - tools
meta:                   # mapping: key → mapping
  public: true
  stars: 12
```

Equivalent JSON: `{"name": "notes", "tags": ["python", "tools"], "meta": {"public": true, "stars": 12}}`.

## Indentation

- **Spaces only — tabs are a parse error**, not a style issue. Two spaces per level by convention.
- Nesting is set by indentation alone; there is no closing token.
- Sequence items may sit at the same column as their key. Both parse identically:

```yaml
tags:
- python        # legal
tags:
  - python      # legal, more readable
```

- Keys of a mapping inside a sequence align with the key after the `-`, not with the `-`:

```yaml
steps:
  - name: checkout
    uses: actions/checkout@v4     # same mapping as `name`
  - name: test
    run: pytest
```

## Block vs flow style

Flow style is the inline JSON-like form, useful for short leaf values. Once `{` or `[` opens, JSON rules apply (commas required, indentation irrelevant).

```yaml
point: {x: 1, y: 2}
colors: [red, green]
```

## Quoting

- **Plain (unquoted)** — the default. Cannot begin with an indicator character (`- ? : , [ ] { } # & * ! | > ' " %`) or contain `: ` or ` #`.
- **Single-quoted** — fully literal; `''` is the only escape. Best for backslashes (regexes, Windows paths).
- **Double-quoted** — the only style with escapes: `\n`, `\t`, `\"`, `\uXXXX`.

```yaml
version: "3.10"     # unquoted 3.10 is the float 3.1
time: "12:30"       # unquoted, YAML 1.1 reads sexagesimal → 750
message: "key: value inside a string"
url: http://example.com   # fine — no space after the colon
```

## Block scalars

For multi-line strings without quoting or escapes. Both strip the common leading indent.

```yaml
script: |           # literal: newlines preserved
  set -euo pipefail
  pytest -q
prose: >            # folded: single newlines become spaces
  one long logical
  line
oneliner: |-        # strip: no trailing newline
  exactly this
```

Chomping indicators control trailing newlines: `|` keeps exactly one (clip, default), `|-` keeps none (strip), `|+` keeps all (keep).

## Implicit typing

Unquoted scalars are auto-typed, and this causes most YAML bugs.

```yaml
a: 42            # int
b: 3.14          # float
c: true          # bool
d: null          # null
e: ~             # also null
f:               # empty → null
```

!!! warning "The Norway problem"
    YAML 1.1 — which **PyYAML implements** — treats `y`, `yes`, `no`, `on`, `off` (any capitalisation) as booleans, so the country code `NO` loads as `False`. YAML 1.2 narrowed booleans to `true`/`false`, but you can't rely on the consumer's version. Quote two-letter codes and y/n values.

Other traps:

- `1.10` → the float `1.1`; the trailing zero vanishes.
- `010` → octal `8` under YAML 1.1, the string `"010"` under 1.2.
- `1e5` → the float `100000.0`.
- **Duplicate keys** are implementation-defined; PyYAML silently keeps the last.

An explicit tag overrides inference — `!!str`, `!!int`, `!!float`, `!!bool`, `!!null`, `!!binary` — but quoting is usually clearer:

```yaml
version: !!str 1.10
```

Single-`!` tags are application-specific, which is how tools extend YAML (CloudFormation's `!Ref`).

## Anchors and aliases

The one feature that makes YAML more than JSON with indentation: reuse a node already defined in the same document.

```yaml
defaults: &defaults        # &name defines an anchor
  adapter: postgres
  host: localhost

development:
  <<: *defaults            # merge key: splice the mapping in
  database: dev_db

full_copy: *defaults       # alias: reuse the whole node
```

- `&name` anchors a node, `*name` aliases it — the alias *is* the same node, not a copy.
- `<<:` merges a mapping's keys into the current one; explicit keys win over merged ones.
- Anchors are **per-document** — you cannot reference one defined in another file.
- Merge keys are a YAML 1.1 extension, not core 1.2. Docker Compose supports anchors; **GitHub Actions does not**.

## Documents and comments

`---` separates documents in one file (common in Kubernetes and in Markdown frontmatter); `...` optionally ends one.

```yaml
---
name: first
---
name: second
```

Comments are `#` only — there are **no block comments**, and comments are not part of the data model, so a load→dump round trip destroys them.

## Reading YAML in Python

PyYAML installs as `pyyaml` but imports as `yaml`:

```python
import yaml

with open("config.yml") as f:
    config = yaml.safe_load(f)

text = yaml.safe_dump(config, sort_keys=False, default_flow_style=False)
```

!!! danger "Always safe_load"
    Bare `yaml.load()` and `yaml.unsafe_load()` construct arbitrary Python objects via tags like `!!python/object/apply:os.system` — remote code execution on untrusted input. Use `yaml.safe_load` / `yaml.safe_dump`.

- `yaml.safe_load_all(f)` — generator over a multi-document stream.
- `ruamel.yaml` — YAML 1.2, and round-trip mode preserves comments, quotes, and key order. Use it when *editing* a config file programmatically.
- `yamllint` catches duplicate keys and truthy traps; JSON Schema (`check-jsonschema`) validates structure, since YAML maps onto the JSON data model.

## YAML vs JSON vs TOML

| | YAML | JSON | TOML |
|---|---|---|---|
| Comments | yes | no | yes |
| Deep nesting | natural | natural | awkward |
| Ambiguous typing | yes | no | no |
| Multi-line strings | `\|` / `>` | escapes only | `"""` |
| References | anchors | no | no |
| Typical use | CI, k8s, config | interchange | `pyproject.toml` |

JSON for machine-to-machine, TOML for flat project config, YAML for hand-written nested config — paying for the expressiveness with the typing traps.

## Related

- [Markdown](markdown.md) — frontmatter blocks are embedded YAML documents
- [jq](jq.md) — the same querying instinct, for JSON
- [GitHub Actions](../git/github-actions.md) — workflows are YAML
