---
title: Windows, macOS and Linux
description: What differs by operating system, shell and installer, and what has and has not been checked.
---

The kit is plain Python. Most commands behave the same everywhere. This page lists the differences the code and docs support. Items marked "verified" were run on Windows 11 while writing this page. Nothing here was run on macOS or Linux, so those sections only repeat what the code does.

## Quick reference

| Topic | Windows | macOS and Linux |
|-------|---------|-----------------|
| Home pack | `C:\Users\<you>\.pipeline` (verified) | `~/.pipeline` |
| Interpreter probe for hook commands | `python`, then `python3`, then `py -3` | `python3`, then `python` |
| Set an environment variable | PowerShell: `$env:NAME = 'value'` | `export NAME='value'` |
| `./install.sh` | Needs a bash (Git Bash or WSL). Or skip it and use `uv tool install` or `pipx install` | Works. Picks `uv`, else `pipx` |
| Shell scripts in the pack (such as `deploy-local.sh`) | Need a bash | Run directly |

## Python and the launcher

The CLI needs Python 3.11 or later (`requires-python = ">=3.11"`).

- `python3` is usually missing on Windows. When the Microsoft Store alias is on it is a stub that prints `Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases.` (verified). That is why the installer does not assume `python3` on Windows.
- `py -3` is the Windows launcher and worked here (verified). `python3` is first on macOS and Linux because many Linux images ship only `python3`.
- If `pipeline-kit` runs under the wrong Python, `pipeline-kit doctor` shows the version it sees, for example `ok  Python 3.13 (3.11+)`.

## Hook commands and the interpreter

`init` writes the interpreter it found into `.cursor/hooks.json`, `.claude/settings.json` or `.github/hooks/pipeline-guardrails.json`. The installer tries the candidates above with a small probe and falls back to the absolute path of the Python that is running the installer.

Consequences, from the pack's `hooks/README.md` and the installer code. See also [IDE hooks](/docs/troubleshooting/hooks).

- A repo whose IDE config was committed on one machine can carry an interpreter that does not exist on another. Re-run `pipeline-kit init --ide <ide>` after cloning, or on a machine where Python moved. Re-running replaces the kit's own entries and leaves yours.
- A config that still contains `{{PYTHON}}` was not written by the installer.
- Hook commands carry no `VAR=value` prefix. That syntax is a parse error in `cmd.exe` and PowerShell and used to disable every hook on Windows. If you hand-edit a hook command and add one, hooks will stop working there.
- GitHub Copilot CLI treats a crashed `preToolUse` hook as a denial. The other two hosts let the call through. See the [GitHub adapter](/docs/adapters/github).

## Installing the CLI

| Method | Notes |
|--------|-------|
| `uv tool install git+<repo-url>` | Puts `pipeline-kit` in uv's tool bin directory. On this Windows machine that is `C:\Users\<you>\.local\bin` (`uv tool dir --bin`, verified) |
| `pipx install git+<repo-url>` | Same idea with pipx |
| `./install.sh` from a clone | A bash script. It runs `uv tool install --force`, else `pipx install --force`, else prints that one of them is required and exits 1 |
| `python -m pip install -e .` | Installs into whichever Python you ran. The README shows this for contributors |

If `pipeline-kit` is not found after a tool install, the bin directory is not on `PATH`. `uv tool update-shell` exists to add it. Open a new terminal afterwards.

### `uv tool` and `pip` are separate environments

An extra such as `.[orchestrator]`, `.[assess]` or `.[memory]` must go into the same environment as the CLI you run. If you installed with `uv tool`, use `uv tool install -e ".[memory]"`. A `pip install` goes to a different Python and the CLI will not see it. The missing-extra messages are in [Error messages](/docs/troubleshooting/errors#optional-packages-and-extras).

## Environment variables

Examples in the docs use `export`. In PowerShell use `$env:` instead. A variable set in one terminal is not seen by an IDE that was already running. Restart the IDE, or set the variable at user level, so the agent's shell inherits it.

```powershell
$env:CURSOR_API_KEY = '<key>'
$env:PIPELINE_KIT_LICENSE = '<token>'
```

The README uses the same pattern for `PIPELINE_KIT_LICENSE`.

## Paths

- The Graphify wrapper converts backslashes in `docs-modules.yaml` module paths to forward slashes before it runs the extract, so either style works there. Other commands were not checked for this.
- The scoring code once failed on Windows paths. The fix is in the 1.2.2 changelog ("Observability scoring path normalization on Windows"). Upgrade if you run an older version and the scores look wrong on Windows.
- The home pack and `license.json` live under your user profile, not the repo. Project `uninstall` removes the project pack only.

## File permissions

- On install the kit sets executable bits on `.py` and `.sh` files it copies. On Windows that setting has little meaning. The repo records no Windows problem from it.
- `pipeline-kit license activate` writes `~/.pipeline/license.json` with mode `0600`. Whether Windows enforces that mode was not checked. Keep the file in your profile folder and do not copy it into a repo.

## Console output

On Windows with a legacy code page, messages that contain the em dash print a replacement character. For example `no .pipeline/config.json � run pipeline-kit init first` (verified). Only the display is affected; the exit code and the message are the same. Setting `PYTHONUTF8=1` is a general Python option for this. It was not tested against this CLI.

## Cursor and the workspace root

Open the folder that contains `.cursor/hooks.json` and `.pipeline/` as the only workspace root, on every platform. See [Cursor](/docs/adapters/cursor).

## Agent security on Windows

Cursor session scanning uses the optional `adr-sensor` package. The docs say it is strongest on macOS and Linux and that on Windows the database path may be found but the parser can still miss it. See [Agent security](/docs/capabilities/agent-security).

## What is not known

- No macOS- or Linux-specific problems are recorded in the repo, so none are listed.
- Native-Windows alternatives to the pack's `.sh` scripts are not documented. Use Git Bash or WSL.
- Long-path limits, antivirus effects and corporate proxy behaviour are not covered by the repo.

Related: [Prerequisites](/docs/getting-started/prerequisites), [Install the CLI](/docs/getting-started/install-cli), [IDE hooks](/docs/troubleshooting/hooks).
