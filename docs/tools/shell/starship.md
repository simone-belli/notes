---
tags:
  - cli
  - config
---

# starship

A cross-shell prompt: one Rust binary (`brew install starship`) that renders the prompt for zsh, bash, fish, PowerShell and others, replacing hand-rolled `PS1`/`PROMPT` escapes with a declarative `starship.toml`. It reads context on every prompt — current directory, Git state, language versions, cloud profile — and prints only the modules that apply.

```zsh
# last line of ~/.zshrc
eval "$(starship init zsh)"
```

Other shells use the same `init` subcommand: `eval "$(starship init bash)"` for bash, `starship init fish | source` for fish.

| Path | Role |
|------|------|
| `~/.config/starship.toml` | The config — not created by install, you write it |
| `$STARSHIP_CONFIG` | Override the config path (e.g. keep it in a dotfiles repo) |
| `$STARSHIP_CACHE` | Where version lookups are cached |

!!! note "Nothing is required"
    Every key has a default, so a missing `starship.toml` still gives a full prompt. A config file only states *differences* from the default — `starship print-config` dumps the complete computed config, which is the best reference for what you can override.

## The prompt format

The top-level `format` string is the whole prompt. Modules are referenced as `$module_name`, and literal text between them is printed as-is:

```toml
format = """
$directory$git_branch$git_status
$character"""
add_newline = false
```

`$all` is shorthand for every module in starship's default order, *minus* any module you name explicitly elsewhere in the string. That makes "default prompt, but with the directory first" a one-liner:

```toml
format = "$directory$all"
```

Other top-level keys:

| Key | Default | Effect |
|-----|---------|--------|
| `format` | `"$all"` | The prompt itself |
| `right_format` | `""` | Right-aligned prompt (zsh, fish, PowerShell) |
| `add_newline` | `true` | Blank line before each prompt |
| `continuation_prompt` | `"[∙](bright-black) "` | Shown for multi-line input |
| `scan_timeout` | `30` | Milliseconds allowed for scanning files to detect a language |
| `command_timeout` | `500` | Milliseconds allowed per external command (e.g. `python --version`) |

A `$schema` key enables editor completion and validation:

```toml
"$schema" = "https://starship.rs/config-schema.json"
```

## Module format strings

Each module has its own `format`, written in the same mini-language. Three constructs matter:

- **Variables** — `$branch`, `$version`, `$symbol`, `$style`. Braces disambiguate when text follows: `${version}rc`.
- **Text groups** — `[text](style)`. The square brackets hold text (and variables), the parentheses a style string.
- **Conditional groups** — `(...)` renders only if *every* variable inside it is non-empty. This is what keeps separators from stranding when a value is missing.

```toml
[python]
format = 'via [${symbol}(${version} )(\($virtualenv\) )]($style)'
```

Here the trailing space lives *inside* each conditional group, so no version means no stray space, and no virtualenv means no empty `()`.

!!! warning "Use TOML literal strings for formats"
    Parentheses, brackets and `$` that should appear literally need a backslash: `\(`, `\[`, `\$`. In a basic (double-quoted) TOML string the backslash is itself an escape, so you end up doubling it. Single-quoted TOML strings are literal — `format = '[\[$all_status\]]($style) '` — which is why most defaults are written that way.

### Style strings

A style is a space-separated list of words, evaluated left to right; later colours win.

```toml
style = "bold fg:#89b4fa bg:black"
```

- Modifiers: `bold`, `italic`, `underline`, `dimmed`, `inverted`, `blink`, `strikethrough`, `hidden`.
- Colours: names (`red`, `bright-red`, `purple`), hex (`#ff0000`), or ANSI 256 numbers (`128`).
- `fg:` / `bg:` pick the layer; a bare colour means foreground.
- `none` clears everything; `prev_fg` / `prev_bg` reuse the previous segment's colour, which is how powerline-style arrows get their seam right.

### Palettes

Name colours once, then refer to them everywhere — the standard way to swap a whole theme by editing one line.

```toml
palette = "catppuccin"

[palettes.catppuccin]
sky = "#89b4fa"
mauve = "#cba6f7"

[directory]
style = "bold fg:sky"
```

## Configuring individual modules

Nearly every module accepts `format`, `style`, `symbol` and `disabled`; language modules add `version_format` and `detect_extensions`/`detect_files` to control when they appear.

```toml
[character]
success_symbol = "[➜](bold green)"
error_symbol = "[➜](bold red)"

[directory]
truncation_length = 2        # keep this many parent dirs
truncation_symbol = "…/"     # marker for what was cut
truncate_to_repo = true      # paths shown relative to the repo root

[git_branch]
format = "on [$symbol$branch]($style) "
symbol = " "

[git_status]
ahead = "⇡${count}"          # $count is available inside these sub-symbols
behind = "⇣${count}"
diverged = "⇕⇡${ahead_count}⇣${behind_count}"

[cmd_duration]
min_time = 2000              # only report commands slower than 2 s
format = "took [$duration]($style) "
```

Silencing a module is a single key, and worth reaching for on the slow ones — language modules shell out to `<lang> --version`:

```toml
[nodejs]
disabled = true
```

The `git_status` symbols mirror `git status --porcelain` — see [Git](../../git/git.md#machine-readable-status) for what those index/worktree flags mean. The `[python]` module can report the version manager's name instead of the interpreter's via `pyenv_version_name = true`; see [pyenv](../../python/tooling/pyenv.md).

## Custom modules

`[custom.<name>]` runs a shell command and puts its output in the prompt, gated by a condition so it costs nothing elsewhere.

```toml
[custom.k8s_ns]
command = "kubectl config view --minify -o jsonpath='{..namespace}'"
when = "command -v kubectl"   # shell command; module shows only on exit 0
format = "[󱃾 $output]($style) "
style = "bold blue"
```

- `when` takes a shell command (exit status decides) or `true`.
- `files`, `extensions` and `directories` gate on the current directory's contents instead.
- `shell = ["bash", "--norc", "-c"]` pins the interpreter rather than using the default shell.
- Reference it in `format` as `${custom.k8s_ns}`; a bare `$custom` renders all custom modules.

Because `command` is spawned on every prompt, keep it under `command_timeout` — this is the usual cause of a prompt that feels laggy.

## Presets

Starship ships complete themes. `starship preset --list` names them (`nerd-font-symbols`, `catppuccin-powerline`, `gruvbox-rainbow`, `pure-preset`, `plain-text-symbols`, `no-nerd-font`, …); `-o` writes one out as a starting point to edit.

```zsh
starship preset --list
starship preset nerd-font-symbols -o ~/.config/starship.toml   # overwrites the file
```

!!! tip "Symbols need a patched font"
    Most presets use glyphs from the Nerd Font range. Without a patched terminal font they render as tofu boxes — either install one (`brew install --cask font-fira-code-nerd-font`) or use the `no-nerd-font` / `plain-text-symbols` presets.

## Debugging and introspection

| Command | Use |
|---------|-----|
| `starship explain` | Annotated breakdown of what each segment of the current prompt means |
| `starship timings` | Per-module render time — find the module making the prompt slow |
| `starship module python` | Render one module in isolation while tuning its `format` |
| `starship print-config` | The full computed config, defaults included |
| `starship config` | Open `starship.toml` in `$EDITOR` |
| `starship toggle nodejs` | Flip a module's `disabled` for the session |
| `starship prompt` | Print the prompt once, with flags like `--path` and `--status` to simulate state |

Each takes the same simulation flags as `prompt`, so a config can be tested without `cd`-ing anywhere:

```zsh
starship explain --path ~/some/repo --status 1
```

## See also

- [zsh](zsh.md) — the shell starship hooks into, and where the `init` line lives
- [direnv](direnv.md) — the `[direnv]` module reports its state (disabled by default)
- [Environment Variables](env-vars.md) — `STARSHIP_CONFIG` and friends, and the `[env_var]` module
