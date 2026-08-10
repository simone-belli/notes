---
tags:
  - cli
---

# Shell history

Two independent ways to reuse past commands: **interactive recall** (find and
edit a command) and **history expansion** (reference past commands/args by
`!`-token). Works in both zsh and bash.

## Interactive recall

| Key | Action |
|-----|--------|
| `↑` / `↓` | walk history one line at a time |
| `Ctrl+R` | reverse incremental search; press again to step to the next-older match |
| `Ctrl+S` | forward search (free it with `stty -ixon` if flow-control eats it) |
| `Ctrl+G` | abort a search, restore the original line |
| `Alt+.` | insert **last argument** of previous command; repeat to walk back through earlier commands |
| `Ctrl+X Ctrl+E` | edit the current half-typed line in `$EDITOR` |

- In a `Ctrl+R` search, move the cursor (`→`, `Ctrl+E`) to **edit before running**
  rather than blind-running with `Enter` — the safe habit for destructive commands.
- **Prefix search** (the biggest win): type the start of a command, then `↑` to
  cycle only entries starting with it. Not on by default — bind it:

```zsh
# ~/.zshrc — 'git ' then ↑ cycles only past git commands
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey '^[[A' up-line-or-beginning-search      # ↑
bindkey '^[[B' down-line-or-beginning-search    # ↓
```

!!! tip "fzf rebinds `Ctrl+R` to a fuzzy finder"
    Installing [`fzf`](https://github.com/junegunn/fzf) turns `Ctrl+R` into a
    full-screen **fuzzy** history search (out-of-order, multi-word, with preview)
    — the single biggest ergonomic upgrade for history-heavy work.

## History expansion (`!` designators)

Expanded before the command runs:

| Token | Expands to |
|-------|-----------|
| `!!` | previous command (`sudo !!` reruns with sudo) |
| `!$` / `!^` / `!*` | last / first / all arguments of previous command |
| `!n` | command number `n` (from `history`) |
| `!-n` | command `n` entries back |
| `!string` | most recent command **starting with** `string` |
| `!?string?` | most recent command **containing** `string` |
| `^old^new` | rerun previous command, replacing first `old` with `new` |

Chain modifiers with `:` — `!!:p` **prints** without running (preview before a
dangerous rerun), `!$:h` takes the directory of the last path, `!!:s/a/b/`
substitutes.

!!! warning "Expansion fires before you run"
    `!string` can silently trigger an old command, and `!` is active inside
    double quotes in bash. Append `:p` to preview, or use single quotes. For
    anything destructive, prefer `Ctrl+R` — you *see* the full command first.

## List and bulk-edit

```zsh
history            # recent commands with numbers (then run !n)
history 20         # last 20
fc -l              # same listing (POSIX)
fc                 # open the last command in $EDITOR; save-quit runs it
```

## Config that makes recall work

```zsh
# ~/.zshrc
HISTSIZE=100000
SAVEHIST=100000               # on-disk (~/.zsh_history)
setopt HIST_IGNORE_ALL_DUPS  # collapse duplicates
setopt HIST_IGNORE_SPACE     # leading space = don't record (for secrets)
setopt HIST_FIND_NO_DUPS     # skip dupes while searching
setopt SHARE_HISTORY         # share live across sessions
```

bash: `HISTSIZE` / `HISTFILESIZE`, `HISTCONTROL=ignoreboth`, `shopt -s histappend`.

!!! tip "Keep a secret out of history"
    With `HIST_IGNORE_SPACE` (zsh) / `HISTCONTROL=ignorespace` (bash), prefix a
    command with a **single space** and it isn't recorded — the standard way to
    run something with an inline token without persisting it. See
    [env-vars.md](env-vars.md) for handling secrets properly.

## See also

- [zsh.md](zsh.md) — shell basics, navigation, keyboard shortcuts
