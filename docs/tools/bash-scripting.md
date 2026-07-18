---
tags:
  - cli
---

# Bash/shell scripting basics

A shell script is a text file interpreted by a shell, made runnable via a shebang line and the execute permission bit. Distinct from interactive shell use — see [zsh.md](zsh.md) for that.

## Shebang and execution

```bash
#!/bin/sh              # POSIX shell — most portable, fewest features
#!/bin/bash             # bash at its canonical path
#!/usr/bin/env bash     # find bash via PATH — portable across install locations
```

- First line, tells the kernel which interpreter to run the file with — only takes effect when the file is invoked as a path (`./script`), not when passed explicitly (`bash script`).
- Requires execute permission: `chmod +x script`.
- Match the shebang to the syntax used: `#!/bin/sh` scripts must avoid bash-only features (`[[ ]]`, arrays, `set -o pipefail`).

## `exec`: replace, don't spawn

```bash
#!/bin/sh
exec poetry run pytest src/ "$@"
```

`exec cmd` replaces the current shell process with `cmd` instead of running it as a child. For a thin wrapper script:

- No leftover shell process once `cmd` finishes.
- Signals (`Ctrl+C`) go straight to `cmd`.
- Exit code passes through exactly, with nothing after it to clobber it.

!!! tip "When to use exec"
    Use `exec cmd "$@"` when the script's whole job is "become this other command." Skip it if you need to run cleanup *after* the command (`cmd; rm -f tmp`) — `exec` never returns to the script.

## Argument forwarding: quote `"$@"`

| Form | Behaviour |
|---|---|
| `"$@"` | Each argument preserved as its own word — correct for forwarding |
| `$@` / `$*` (unquoted) | Word-splits every argument on spaces — breaks on args containing spaces |
| `"$*"` | Joins all arguments into one string |

```bash
run_pytest -k "test name with spaces"
# "$@"  → one arg: "test name with spaces"   (correct)
# $@    → four args: test / name / with / spaces   (wrong)
```

`$0` = script name, `$1`, `$2`, … = positional args, `$#` = arg count, `$?` = exit status of the last command.

## Control flow

```bash
if [ -f "file.txt" ]; then
    echo "exists"
fi

for f in *.py; do echo "$f"; done

while read -r line; do echo "$line"; done < file.txt

greet() { echo "Hello, $1"; }
```

`[ ... ]` is the portable POSIX test; `[[ ... ]]` is bash/zsh-only, with no word-splitting inside it — requires a bash/zsh shebang.

## Fail-fast safety net

```bash
set -euo pipefail
# -e: exit on any command failure
# -u: error on unset variable use
# -o pipefail: a pipeline fails if any stage fails, not just the last
```
Bash-only — needs `#!/bin/bash`, not `#!/bin/sh`.

## See also

- [zsh.md](zsh.md) — interactive shell use: aliases, navigation, PATH
- [direnv.md](direnv.md#direnv-commands) — `PATH_add` to make a project's `bin/` scripts callable by name only inside that project
