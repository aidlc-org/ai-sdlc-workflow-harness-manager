# troubleshooting-scenarios

Three problems you can reproduce offline in a throwaway folder, with the exact message you will see and what to do.

## 1. `doctor` on a folder that was never initialised

```bash
pipeline-kit doctor ./empty-folder --ide none
```

Output ends with `missing  install marker`, `missing  configuration` and `missing  workflow loader`, then `pipeline-kit setup is incomplete` on stderr. Exit code 1.

Doctor falls back to your home pack (`~/.pipeline`) when the project has none, so it reports `user pack`, not `project pack`. Fix: run `pipeline-kit init ./empty-folder --ide none`, then run `doctor` again.

## 2. `init` run twice

```bash
pipeline-kit init ./my-project --ide none
pipeline-kit init ./my-project --ide none
```

The first run prints `config.json: wrote`. The second prints `config.json: merged` and exits 0. It is safe: your local `config.json` values are kept and only new keys are added. To refresh managed files on purpose, use `pipeline-kit update ./my-project`.

## 3. A hook denial

The shell hook blocks commits and pushes unless you opted in. Simulate the agent calling it:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}' | python my-project/.pipeline/hooks/before-shell.py
```

The JSON reply has `"permission": "deny"` and the reason `Blocked commit/push/publish. Set PIPELINE_ALLOW_GIT=1 only when the user asked to ship.` Set `PIPELINE_ALLOW_GIT=1` for that session and the same call returns `allow`. A harmless command such as `ls` is allowed.

## Smoke test

```bash
python examples/troubleshooting-scenarios/smoke.py
```

Reproduces all three in temp folders (with a temp home, so your real `~/.pipeline` is not touched) and asserts the message text above. Automated, offline.
