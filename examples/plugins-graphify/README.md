# plugins-graphify

Graphify builds the code knowledge graph the kit uses for scans, test design and the codebase docs workflows. It is optional and stays off until you register it. The kit does not vendor Graphify; you install the official CLI yourself.

## Commands

```bash
pipeline-kit plugins list
pipeline-kit plugins install graphify --ide claude-code --scope project
pipeline-kit plugins install graphify --ide claude-code --hook
pipeline-kit plugins status --plugin graphify
pipeline-kit plugins uninstall --help
```

- `install graphify` registers the plugin skill for your IDE. `--hook` also installs Graphify's commit hook after it registers.
- `status` reports whether the Graphify CLI is found, its version, whether the graph is fresh, and whether the hook is present.
- `uninstall` removes the plugin skill. Generated graphs stay unless you pass `--purge`.
- `pipeline-kit doctor` also prints a Graphify readiness line.

## Smoke test

```bash
python examples/plugins-graphify/smoke.py
```

Static. It checks that every command and flag above exists in the CLI help, and that `plugins list` names `graphify`. It installs nothing and uses no network.
