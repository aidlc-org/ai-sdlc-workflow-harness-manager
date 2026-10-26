# observability-langfuse

Send agent run traces and scores to Langfuse. **Manual example**: it needs a Langfuse account, the `evidence` license area, and network access, so CI only checks it statically.

## Steps

```bash
pipeline-kit obs install --ide claude-code --adapter langfuse
pipeline-kit obs status
pipeline-kit obs report
pipeline-kit obs flush
pipeline-kit obs uninstall --ide claude-code
```

1. Put your keys in the environment or in a `.env` file at the project root. Never put them in `config.json` and never commit them.

   ```text
   LANGFUSE_PUBLIC_KEY=<your public key>
   LANGFUSE_SECRET_KEY=<your secret key>
   LANGFUSE_BASE_URL=<your Langfuse URL>
   ```

2. `obs install` merges fail-open hooks into your IDE settings and never replaces existing entries. It also turns `agent_observability` on.
3. Work as usual. Hooks write a local ledger at `.pipeline/state/obs/events.jsonl`.
4. `obs status` shows enabled flag, adapter, ledger size and whether the keys are set. `obs report` prints local scores with no network. `obs flush` scores new ledger rows and ships them to Langfuse.

Every `obs` command except `report` needs the `evidence` license area. Without it, `obs status` exits 73 with `license: missing`.

## Smoke test

```bash
python examples/observability-langfuse/smoke.py
```

Static only. It checks that `obs --help` lists the commands used above, that `obs install --help` lists the `langfuse` adapter, that this README names the `LANGFUSE_*` variables, and that it contains no key. No network, no license needed.
