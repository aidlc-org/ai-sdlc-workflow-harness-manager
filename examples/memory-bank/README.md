# memory-bank

Keep feature artifacts in a separate git folder (a memory bank) shared across projects, instead of `features/` inside each repo. Needs the `pipeline-kit-memory` package (`pip install -e ".[memory]"`, or `packages/pipeline-kit-memory` on `PYTHONPATH`).

## Steps

```bash
pipeline-kit init ./my-project --ide claude-code
pipeline-kit memory link ../my-memory-bank ./my-project
pipeline-kit memory status ./my-project
pipeline-kit memory index ./my-project
pipeline-kit memory doctor ./my-project
pipeline-kit memory search "checkout" ./my-project
pipeline-kit memory unlink ./my-project
```

- `link` points the project at the bank. The bank is created if missing (README, gitignore, git repo) unless you pass `--no-init`. Options: `--project-id` (namespace under `projects/{id}/`) and `--layout flat|namespaced`.
- `status` prints the link as JSON: root, layout, index path, and whether the index exists.
- `index` builds the full-text search index. Until you run it, `doctor` reports `missing  search index` and exits 1.
- `doctor` checks the pack, the memory root, that it is writable and a git repo, and the index.
- `unlink` turns memory off without deleting the bank.

## Windows note

On a console using the cp1252 code page, `memory index` can fail with a `UnicodeEncodeError` after it has built the index, because it prints an arrow character. Set `PYTHONUTF8=1` first. The smoke script does this.

## Smoke test

```bash
python examples/memory-bank/smoke.py
```

Creates a temp project and bank, runs `link`, `status`, `index`, `doctor`, `unlink`, and checks the output. Offline. If `pipeline-kit-memory` is not importable it prints the reason and exits 0 (skipped).
