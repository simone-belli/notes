---
tags:
  - config
---

# direnv — auto-loading project variables

A `.env` file is inert text — nothing exports it into your shell automatically. `direnv` (`brew install direnv`) hooks the shell's directory-change event: `cd` into a project and variables export automatically in *any* terminal (Cursor, Terminal.app, SSH); `cd` out and they unexport.

See [env-vars.md](env-vars.md#env-files) for what `.env` files are and why they exist. For an editor-scoped alternative (Cursor/VS Code only, no shell config), see [env-vars.md](env-vars.md#auto-loading-project-variables-into-a-terminal).

```bash
# one-time, in ~/.zshrc — generic hook, no project data
eval "$(direnv hook zsh)"
```
```bash
# <project-root>/.envrc — per project, auto-loads/unloads on cd
dotenv   # or: export KEY=value directly
```
```bash
direnv allow   # approve once per new/changed .envrc
```

The `~/.zshrc` line is written once, ever, and carries no secrets.

direnv's `PATH_add <dir>` prepends a project-local directory to `PATH` (also scoped to entering/leaving the folder) — useful for project-scoped command shortcuts, since `alias` itself isn't an environment variable and can't be exported this way (see [zsh.md](zsh.md#aliases-and-functions)):

```bash
# .envrc
PATH_add bin   # ./bin/* callable as plain commands only inside this project
```

The scripts placed in `bin/` are themselves plain shell scripts — see [bash-scripting.md](bash-scripting.md) for the shebang, `exec`, and argument-quoting basics behind a wrapper like `bin/run_pytest`.

## direnv commands

| Command | Effect |
|---------|--------|
| `direnv allow` | Trust the current `.envrc` (re-run after any edit) |
| `direnv deny` | Revoke trust — variables unexport on next `cd` |
| `direnv edit` | Open `.envrc` in `$EDITOR`, then re-prompts `allow` |
| `direnv reload` | Force re-evaluation without leaving/re-entering the dir |
| `direnv status` | Show which `.envrc` is active and whether it's loaded |

!!! warning "Trust is per-content, not per-path"
    direnv hashes `.envrc` and refuses to load an unapproved or changed file — silently skipping it, not erroring — until `direnv allow` runs again. This stops a malicious `.envrc` (e.g. from `git pull` or `cd` into an untrusted repo) from executing arbitrary shell code unnoticed.

## Other stdlib functions

Beyond `dotenv` and `PATH_add`, `.envrc` can call:

```bash
use python 3.12       # activate a language-specific env (pyenv, nvm, etc. — needs the matching plugin)
layout python          # create/activate a venv in .direnv/ scoped to the project
source_up               # inherit and extend the parent directory's .envrc (monorepo subfolders)
dotenv_if_exists .env.local   # like dotenv, but silent if the file is missing
```
