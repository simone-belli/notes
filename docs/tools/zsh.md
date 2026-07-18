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
| `Ctrl+R` | Reverse-search history |
| `Ctrl+L` | Clear screen |
| `!!` | Repeat last command |
| `!$` | Last argument of previous command |

## Introspection

```zsh
which python      # path to executable
type python       # alias / function / file
man ls            # manual page
```

## See also

- [env-vars.md](env-vars.md) — environment variables, .env files, scope
