# stack-node

A minimal Node repo (`skeleton/`, no dependencies) used to show how the kit is set up for this stack.

## Set up

```bash
pipeline-kit init ./my-node-project --ide claude-code
pipeline-kit doctor ./my-node-project --ide claude-code
```

Use `--ide cursor`, `github` or `none` for other tools. `init` writes `.pipeline/` next to your code and leaves your source alone.

## Stack settings

Edit `.pipeline/config.json`. These are the real keys; the kit ships them with placeholder values.

```json
{
  "deploy": { "target": "auto", "targets": ["auto"] },
  "verify": { "rules": [] }
}
```

- `deploy.targets`: the targets your deploy runbook understands. For this stack you might list your own target names, for example `"staging"` and `"production"`, then set `deploy.target` to one of them. The command to run it (for example `npm run deploy:staging`) is yours; the kit only holds the target names.
- `verify.rules`: path-substring reminders, with an optional `expect` regex for integrity checks. Keep it empty until you have a rule worth enforcing.
- Your test command for this stack is typically `npm test`; keep it in your repo rules or in the prompt you give the tester agent.

## Smoke test

```bash
python examples/stack-node/smoke.py
```

Copies `skeleton/` to a temp directory, runs `init --ide none` and `doctor`, and checks `.pipeline/config.json`, the shell hook and the loader exist. Automated, offline.
