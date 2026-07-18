---
tags:
  - config
quiz: detail
---

# Environment Variables — macOS / Unix

## What is "the environment"?

Every Unix process has a small key-value store called the **process environment**: a flat list of `KEY=value` strings held in memory alongside the process. It's separate from the filesystem and from heap memory.

Inheritance rule: a child process gets a **copy** of its parent's environment at spawn time. Changes in the child never propagate back up. Changes in the parent after spawning don't reach existing children.

The shell (zsh/bash) is itself a process. When you open a terminal, the shell inherits from whatever launched it (the terminal app, launchd, SSH daemon) and passes copies to every command you run.

## Environment variables

A variable is one `KEY=value` entry. Convention: **UPPERCASE_WITH_UNDERSCORES** keys; values are always strings — programs interpret them as paths, integers, booleans, JSON, etc.

Why they matter:
- Configure behaviour without code changes (dev vs. prod, debug vs. quiet)
- Keep secrets (API keys, tokens) out of source code
- Interop: many tools look for well-known names (`HOME`, `PATH`, `EDITOR`, `AWS_ACCESS_KEY_ID`, `PYTHONPATH`)

```bash
env               # print entire environment
printenv HOME     # print one variable
echo $HOME        # shell expands inline
```

## Setting variables — three scopes

**Current session** (gone when terminal closes):
```bash
export API_KEY="sk-abc123"   # export = visible to child processes
```

Without `export`, the variable exists in the shell but children don't inherit it.

**One command only** (parent shell unchanged):
```bash
LOG_LEVEL=DEBUG python app.py
```

**Permanent** (add to shell startup file):
```bash
# ~/.zshrc  (zsh, macOS default)
export EDITOR="vim"
export API_KEY="sk-abc123"
export PATH="$HOME/.local/bin:$PATH"  # prepend to PATH

source ~/.zshrc   # reload without reopening terminal
```

| Shell | Startup file | When loaded |
|-------|-------------|-------------|
| zsh | `~/.zshrc` | Every interactive shell |
| bash | `~/.bashrc` | Every interactive shell |
| bash (login) | `~/.bash_profile` | Login shells, SSH |

## PATH

`PATH` is a colon-separated list of directories searched left-to-right for executables:

```bash
echo $PATH
# /opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin

which python        # which directory won the search
```

Prepend to be found first; append to be found last:
```bash
export PATH="/new/dir:$PATH"
```

## .env files

A `.env` file is a plain-text `KEY=value` file at a **project root**, gitignored, read by the app at startup — not by the shell automatically.

```
myproject/
├── .env           ← gitignored; real secrets
├── .env.example   ← committed; fake values, documents what's needed
├── pyproject.toml
└── src/
```

```bash
# .env syntax
API_KEY=sk-abc123
DATA_DIR=./data
LOG_LEVEL=DEBUG
# no spaces around =; no export keyword; comments with #
```

### Why .env and not ~/.zshrc?

- Per-project scope: avoids leaking project A's keys into project B's processes
- Tooling reads it: `pydantic-settings`, `python-dotenv`, Docker Compose, most frameworks all look for `.env` by default

### Reading .env in Python

Bare:
```python
from dotenv import load_dotenv
import os

load_dotenv()                        # reads .env from cwd
api_key = os.environ["API_KEY"]      # KeyError if missing
api_key = os.getenv("API_KEY", "")   # default if missing
```

With types + validation — prefer [pydantic-settings](../python/libraries/pydantic/pydantic-settings.md):
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    api_key: str

settings = Settings()
```

## Auto-loading project variables into a terminal

A `.env` file is inert text — nothing exports it into your shell automatically. To have variables appear in a terminal the moment you open a project, without touching `~/.zshrc` and without leaking to other projects, two options:

**Editor-scoped (Cursor/VS Code only, zero shell config):**
```json
// <project-root>/.vscode/settings.json
{
  "terminal.integrated.env.osx": {
    "DATABASE_URL": "postgres://localhost/dev"
  }
}
```
Applied only when Cursor spawns its own integrated terminal for that workspace; merges on top of the normal environment. A plain Terminal.app window in the same folder won't see it. Gitignore the file (or just this key) if it holds secrets.

**Shell-scoped, any terminal (`direnv`):**
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
direnv (`brew install direnv`) hooks the shell's directory-change event: `cd` into the folder and variables export automatically in *any* terminal (Cursor, Terminal.app, SSH); `cd` out and they unexport. The `.zshrc` line is written once, ever, and carries no secrets.

## Scope summary

| Scope | Where | Who sees it |
|-------|-------|-------------|
| System | `/etc/environment`, `/etc/profile` | All users |
| User session | `~/.zshrc` | Your terminal processes |
| Project | `.env` at project root | Only when explicitly loaded |
| Single command | `KEY=val cmd` | That command only |

## Debugging

```bash
env | grep MYAPP                       # filter for your app's vars
printenv MYAPP_KEY                     # empty = not set
echo ${MYAPP_KEY:-"not set"}           # show fallback if unset
```

## Security

!!! warning "Env vars are not a security boundary between processes on the same host"
    Any process running as the same OS user can read another process's environment via `/proc/<pid>/environ` or `ps e`. Env vars are safe for keeping secrets *out of source code* and *out of logs*, but they don't protect against a compromised co-tenant process. For strong isolation, use a secrets manager (Vault, AWS Secrets Manager) that issues scoped credentials per service.

- **Never commit `.env`** with real secrets — always gitignore it
- **Never hardcode secrets** in source — once in git history, assume compromised
- Env vars are visible to all processes on the host running as the same user (`ps e`) — not a security boundary between processes on the same machine
- In CI/CD: use the platform's secret manager (GitHub Actions secrets, etc.); they're injected as env vars at runtime without appearing in logs
