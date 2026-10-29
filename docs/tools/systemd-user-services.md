---
tags:
  - config
---

# systemd user services — running a task at startup

On Ubuntu (and most modern Linux distributions), `systemd` is the init system that starts and supervises background processes. Besides the system-wide instance, every user gets a **user instance** of systemd that runs services as that user — no `sudo`, no root-owned files. Dropping a unit file into `~/.config/systemd/user/` and enabling it is the clean way to start a script or daemon automatically, restart it when it crashes, and collect its logs.

## The unit file

A service is described by a `.service` file. The file name (minus the extension) is the service's name:

```ini
# ~/.config/systemd/user/my-task.service
[Unit]
Description=My startup task
After=network-online.target

[Service]
Type=simple
ExecStart=%h/bin/my-task.sh --verbose
WorkingDirectory=%h/projects/my-task
Environment=LOG_LEVEL=info
EnvironmentFile=-%h/.config/my-task.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

- `[Unit]` — metadata and ordering: `Description=`, `After=` / `Wants=` for dependencies.
- `[Service]` — what to run and how:
    - `ExecStart=` — the command; must be an **absolute path** (`%h` expands to the home directory).
    - `WorkingDirectory=` — the current directory for the process.
    - `Environment=` / `EnvironmentFile=` — variables, since the service inherits none of your shell's (see [Environment Variables](shell/env-vars.md)); a leading `-` makes the file optional.
    - `Restart=on-failure` + `RestartSec=` — automatic restart after a non-zero exit.
- `[Install]` — what `enable` hooks the unit into. `default.target` is the user instance's "started" target, so the service starts when the user's systemd starts.

!!! warning "No shell, no profile"
    `ExecStart=` is not run through a shell: pipes, `&&`, `~`, and globbing don't work, and `~/.zshrc` / `~/.profile` are never read. Use absolute paths, set variables with `Environment=`, and wrap anything shell-like in a script (see [Bash/shell scripting basics](shell/bash-scripting.md)) or use `ExecStart=/bin/bash -c '...'`.

## Service types

| `Type=` | Use for |
|---------|---------|
| `simple` (default) | A long-running process that stays in the foreground |
| `oneshot` | A script that runs once and exits; add `RemainAfterExit=yes` to keep the unit "active" afterwards |
| `forking` | Legacy daemons that fork into the background — avoid, run in the foreground instead |
| `notify` | Programs that signal readiness via `sd_notify` |

A one-off startup script:

```ini
[Service]
Type=oneshot
ExecStart=%h/bin/mount-backups.sh
RemainAfterExit=yes
```

## Enabling and managing it

Every command takes `--user` to talk to the user instance instead of the system one:

```bash
systemctl --user daemon-reload            # re-read unit files (after every edit)
systemctl --user enable --now my-task     # start at startup + start right now
systemctl --user status my-task           # state, process ID, last log lines
systemctl --user restart my-task
systemctl --user disable --now my-task    # stop and remove from startup
systemctl --user list-units --type=service
journalctl --user -u my-task -f           # follow the logs (stdout/stderr land here)
```

- `enable` creates a symlink in `~/.config/systemd/user/default.target.wants/`; `disable` removes it.
- Forgetting `daemon-reload` after editing the file is the most common "my change did nothing" cause.
- `systemctl --user cat my-task` shows the file systemd actually loaded.

## Login vs boot: lingering

!!! note "User services start at login by default"
    The user instance starts when you first log in and stops when your last session ends. So an enabled user service runs **from login to logout**, not from boot. To start it at boot — before anyone logs in — and keep it running after logout, enable *lingering*:

```bash
loginctl enable-linger "$USER"     # user instance starts at boot
loginctl show-user "$USER" | grep Linger
```

For services that need the desktop (a tray app, anything using `DISPLAY` or Wayland), use `WantedBy=graphical-session.target` and `After=graphical-session.target` instead of `default.target`.

## User vs system services

| | User service | System service |
|---|---|---|
| Unit location | `~/.config/systemd/user/` | `/etc/systemd/system/` |
| Commands | `systemctl --user ...` | `sudo systemctl ...` |
| Runs as | You | root, or `User=` in `[Service]` |
| Starts | At login (or boot with lingering) | At boot (`WantedBy=multi-user.target`) |

!!! tip "Running on a schedule instead"
    For "every hour" or "15 minutes after boot", pair the service with a `.timer` unit of the same name (`OnBootSec=15min`, `OnCalendar=hourly`, `WantedBy=timers.target`) and `enable --now my-task.timer` — systemd's replacement for cron, with the same logging via `journalctl`.
