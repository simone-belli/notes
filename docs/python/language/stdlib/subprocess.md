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
