# Examples

Runnable examples for the kit. Each folder has its own `README.md` and, unless blocked, a `smoke.py` that exits 0 on success. Smokes need only `pip install -e .`, run offline, and work on Windows, macOS and Linux.

Run one: `python examples/<name>/smoke.py`. Run all: `python -m pytest tests/test_examples.py -q`.

| Example | What it shows | Status |
|---------|---------------|--------|
| [stack-node](stack-node/) | Minimal Node repo, `init`, `doctor`, `deploy` and `verify` config keys | automated |
| [stack-python](stack-python/) | Same for a Python repo | automated |
| [stack-java](stack-java/) | Same for a Java (Maven) repo | automated |
| [stack-go](stack-go/) | Same for a Go repo | automated |
| [workflows](workflows/) | Every shipped workflow with an example prompt and expected artifacts | automated |
| [plugins-graphify](plugins-graphify/) | Register and check the Graphify plugin | automated (static) |
| [plugins-archify](plugins-archify/) | Register and check the Archify plugin | automated (static) |
| [observability-langfuse](observability-langfuse/) | Send traces and scores to Langfuse | manual (needs Langfuse and a license; static check only) |
| [memory-bank](memory-bank/) | Link an external memory bank, index and doctor it | automated (skips if the memory package is missing) |
| [troubleshooting-scenarios](troubleshooting-scenarios/) | Three problems reproduced offline with exact messages | automated |
| [qa-test-design](qa-test-design/) | QA test design with model deltas | blocked on #21 and #23 |

`_common.py` holds helpers shared by the smoke scripts.
