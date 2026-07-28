---
tags:
  - cli
---

# subprocess

Run shell commands from Python. Prefer `subprocess.run()` over `os.system()` — it captures output and handles errors.

## subprocess.run() — the main API

```python
import subprocess

result = subprocess.run(
    ["git", "log", "--oneline", "-5"],   # list of tokens, not a string
    capture_output=True,                  # capture stdout + stderr
    text=True,                            # decode as str, not bytes
    check=True,                           # raise on non-zero exit
    cwd="/path/to/repo",                  # optional working directory
)
print(result.stdout)
print(result.returncode)   # 0 = success
```

Key arguments:

| Argument | Effect |
|---|---|
| `capture_output=True` | `result.stdout` / `result.stderr` as strings |
| `text=True` | decode bytes → str |
| `check=True` | raise `CalledProcessError` if exit code != 0 |
| `cwd="path"` | working directory for the subprocess |
| `env={**os.environ, "K": "V"}` | environment variables |
| `input="..."` | feed string to stdin |
| `timeout=N` | raise `TimeoutExpired` after N seconds |

## Shell strings, pipes, globs — use shell=True

```python
# Pipes and globs require shell=True
result = subprocess.run(
    "cat file.txt | grep ERROR | wc -l",
    shell=True,
    capture_output=True,
    text=True,
)
```

`shell=True` passes the string to `/bin/sh -c`. To force **zsh** specifically:

```python
subprocess.run(["/bin/zsh", "-c", "ls *.py | wc -l"], capture_output=True, text=True)
```

!!! warning "shell=True with user input is a shell injection risk"
    Never build the shell string from untrusted input. Use a list instead — subprocess handles quoting safely.

## Error handling

```python
try:
    result = subprocess.run(["git", "status"], capture_output=True, text=True, check=True)
except subprocess.CalledProcessError as e:
    print(e.returncode, e.stderr)
except FileNotFoundError:
    print("executable not found")
```

## Streaming output (Popen)

Use `Popen` when you need output line-by-line before the process finishes:

```python
with subprocess.Popen(["ping", "-c", "5", "8.8.8.8"], stdout=subprocess.PIPE, text=True) as p:
    for line in p.stdout:
        print(line, end="")
```

## Quick patterns

```python
# Capture a single value
sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

# Run and discard output
subprocess.run(["make", "clean"], check=True)

# Inject an env var
subprocess.run(["./script.sh"], env={**os.environ, "DEBUG": "1"}, check=True)
```

!!! tip "Don't shell out when Python can do it"
    `pathlib`, `shutil`, and `os` cover most file/dir operations without spawning a process. Reserve `subprocess` for external tools (`git`, `ffmpeg`, CLI utilities).

## Running git specifically

Git commands default to human-oriented output — colorized, paginated, subject
to change between versions. When scripting, prefer:

- **Plumbing commands** (`git rev-parse`, `git cat-file`, `git ls-tree`) over
  **porcelain** ones (`git log`, `git status`, `git diff`) — plumbing output
  is a stable, documented interface; porcelain output isn't guaranteed to
  stay the same across git versions.
- **`--porcelain` flags** on porcelain commands that offer one (`git status
  --porcelain`) for a stable, script-friendly format without giving up the
  more convenient command.
- **`--no-pager` and `--no-color`** — `git --no-pager log ...` — a pager or
  ANSI color codes in captured output will break naive parsing, even though
  `subprocess` pipes (not a terminal) usually suppress both by default.

```python
# Target a repo without changing cwd
subprocess.run(["git", "-C", "/path/to/repo", "status", "--porcelain"], ...)

# Stop option parsing before a value that might start with '-'
subprocess.run(["git", "log", "--", user_supplied_path], ...)
```

!!! warning "Exit codes aren't uniformly pass/fail"
    Some git commands overload the exit code: `git diff --exit-code` returns
    `1` for "a difference exists", not failure. Run with `check=False` and
    branch on `result.returncode` for such commands instead of trusting
    `check=True`. `128` conventionally means "fatal" (e.g. not a git repo).

For frequent programmatic traversal of commits/branches/diffs as objects
rather than parsed text, a library gives a nicer API than raw `subprocess`
calls: **GitPython** wraps the `git` binary in a `Repo`/`Commit`/`Diff`
object model (still shells out under the hood); **pygit2** binds `libgit2`
directly (no `git` executable needed, faster for high call volume);
**dulwich** is a pure-Python git implementation for environments without a
system `git` binary at all.
