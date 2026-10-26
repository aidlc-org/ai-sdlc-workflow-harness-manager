# plugins-archify

Archify produces architecture diagrams as an Agent Skill, pinned by the kit (`v2.16.0`). It is optional and off until you install it. Without it, the kit falls back to Mermaid diagrams. It needs GitHub CLI 2.90+ and Node.js 18+.

## Commands

```bash
pipeline-kit plugins list
pipeline-kit plugins install archify --ide claude-code --scope project
pipeline-kit plugins status --plugin archify
pipeline-kit plugins uninstall --help
```

- `install archify` registers the plugin skill for your IDE.
- `status` reports whether the skill is installed, the pinned version, whether `architecture_diagrams.enabled` is set, and the fallback.
- `uninstall` removes the plugin skill. Generated diagrams stay unless you pass `--purge`.

## Smoke test

```bash
python examples/plugins-archify/smoke.py
```

Static. It checks that every command and flag above exists in the CLI help, and that `plugins list` names `archify`. It installs nothing and uses no network.
