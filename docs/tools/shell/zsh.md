---
tags:
  - cli
---

# zsh

Default shell on macOS (since Catalina). Superset of bash with better tab completion, globbing, and prompt customisation. Config lives in `~/.zshrc`.

## Navigation

```zsh
cd ~/projects        # ~ = home directory
cd ..                # up one level
cd -                 # toggle to previous directory
pwd                  # print current path
```

## Files and directories

```zsh
mkdir -p a/b/c       # create nested dirs (no error if exists)
cp -r src/ dst/      # copy directory recursively
mv old new           # rename or move
rm -rf dir/          # delete directory — permanent, no trash
```

## Viewing files

```zsh
cat file             # print whole file
less file            # paginate (q quit, / search)
head -n 20 file      # first 20 lines
tail -f log.txt      # follow as file grows
```

## Finding things

```zsh
find . -name "*.py"       # files matching pattern
grep -rn "pattern" .      # recursive search with line numbers
```

Silence `find`'s "Permission denied" noise (which goes to stderr):

```zsh
find / -name "*.conf" 2>/dev/null           # drop all stderr — simplest
find / -name "*.conf" 2>&1 | grep -v denied # keep other errors, filter noise
```

- Errors like `Permission denied` print to **stderr** (fd 2); real results go to stdout (fd 1). `2>/dev/null` discards only the errors, leaving matches intact.
- Downside of `2>/dev/null`: it hides *all* stderr, including genuine problems. Use the `grep -v` filter when you still want to see other errors.
- macOS/BSD `find` can prune unreadable dirs with `-perm -r` guards, but `2>/dev/null` is the portable one-liner.

## Redirects and pipes

```zsh
cmd > out.txt        # stdout to file (overwrite)
cmd >> out.txt       # append
cmd 2>&1             # stderr → stdout
cmd1 | cmd2          # pipe stdout of cmd1 into cmd2
```

## Variables and PATH

```zsh
NAME="Alice"
echo "${NAME}_suffix"    # braces required when followed by more text
export API_KEY="abc"     # export to child processes
```

`PATH` is searched left-to-right for executables. Add to it in `~/.zshrc`:

```zsh
export PATH="$HOME/.local/bin:$PATH"
```

## Aliases and functions

```zsh
# ~/.zshrc
alias ll="ls -la"
alias gs="git status"

mkcd() { mkdir -p "$1" && cd "$1"; }
```

Apply without reopening terminal: `source ~/.zshrc`

!!! note "Project-scoped shortcuts, not global aliases"
    An `alias` defined in `~/.zshrc` is global — visible (and often broken) in every project. `alias` also isn't an environment variable, so tools like direnv can't export it into a directory-scoped shell the way they export `PATH` or `API_KEY`. To get a command shortcut that only exists inside one project: put an executable script in a project `bin/` folder (see [bash-scripting.md](bash-scripting.md) for shebang/`exec`/argument-forwarding basics) and add that folder to `PATH` only while inside the project, via direnv's `PATH_add bin` — see [direnv.md](direnv.md). This is git-shareable and shell-agnostic, unlike a real `alias`.

## Command completion

Tab-completion for a command's subcommands, flags, and arguments (`git chec<TAB>` → `git
checkout`) isn't built into the program itself — it's a **completion function** the shell loads.
Most CLIs ship their own (`git`, `docker`, `kubectl`, `npm`), or one comes from a framework:

```zsh
# ~/.zshrc — zsh's completion system must be initialized once
autoload -Uz compinit && compinit

# a tool's completion script gets sourced directly, or added to the search path
fpath=(/path/to/some-tool/completions $fpath)
source ~/.git-completion.bash   # e.g. Git's own script, via zsh's bashcompinit
```

- **oh-my-zsh** plugins (`plugins=(git docker kubectl)`) bundle pre-wired completions for common
  tools plus aliases (`gst`, `gco`, ...) — the easiest path if already using the framework.
- Verify a completion function loaded: `type _git` should show a function, not "not found".
- **Version skew**: an outdated completion script won't know about a tool's newer subcommands even
  though the binary itself supports them (e.g. Git's `switch`/`restore`) — update the completion
  script alongside the tool, not just the tool.

!!! note "Same lookup mechanism as PATH"
    Completion functions are found via `$fpath`, the same left-to-right search idea as `$PATH` for
    executables (see [Variables and PATH](#variables-and-path) above). A command that won't
    complete is a `$fpath`/loading problem, not a problem with the command itself.

## Symlinks

```zsh
ln -s target link_name   # create symlink
ls -l link_name          # verify: shows  link_name -> target
rm link_name             # remove symlink (not the target)
unlink link_name         # same
```

!!! warning "Trailing slash with rm -rf"
    `rm -rf symlinked_dir/` follows the link and deletes the *target's* contents.
    `rm -rf symlinked_dir` (no slash) removes only the link.

Hard link vs symlink:

| | `ln -s` (symlink) | `ln` (hard link) |
|---|---|---|
| Points to | path | inode |
| Cross-filesystem | yes | no |
| Broken if target deleted | yes | no |
| Can link directories | yes | no |

Use symlinks almost always. Hard links are for deduplication/backup tooling.

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Kill process |
| `Ctrl+Z` | Suspend (resume: `fg`) |
| `Ctrl+R` | Reverse-search history (see [history.md](history.md)) |
| `Ctrl+L` | Clear screen |
| `!!` | Repeat last command |
| `!$` | Last argument of previous command |

For recalling and reusing past commands efficiently — prefix search, `Alt+.`,
`!`-expansion, fzf, and history config — see [Shell history](history.md).

## Introspection

```zsh
which python      # path to executable
type python       # alias / function / file
man ls            # manual page
```

## See also

- [env-vars.md](env-vars.md) — environment variables, .env files, scope
