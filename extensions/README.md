# Extensions

Add a process without forking the kit. There are **two modes**, and each
has its own extension contract.

## Contents

1. [Pick a mode](#pick-a-mode)
2. [Kit mode](#kit-mode)
3. [Orchestrator mode](#orchestrator-mode)

## Pick a mode

```text
kit mode            markdown pack in .pipeline/
  └─ extensions/kit

orchestrator mode   Python graphs in the wheel + pipeline_extensions/
  └─ extensions/orchestrator
```

| Mode | How you add a workflow | Loaded by |
|------|------------------------|-----------|
| **Kit** (default) | Skill + `workflows/{name}.json` + `config.json` chain | Loader / `run-workflow` |
| **Orchestrator** | `pipeline_extensions/{name}.py` (or a setuptools entry point) | `pipeline-kit run` |

Kit mode never imports `pipeline_extensions/`. Orchestrator mode never
runs the markdown loader chain.

## Kit mode

See [`kit/README.md`](./kit/README.md). Shipped examples live in
[`kit/pipeline/workflows/`](../kit/pipeline/workflows/). After `init`,
customers edit `.pipeline/` the same way.

## Orchestrator mode

See [`orchestrator/README.md`](./orchestrator/README.md). Copy-ready
associate workflows: security review, CI audit, dependency audit,
accessibility review.

```bash
cp -R extensions/orchestrator/pipeline_extensions /path/to/your-app/
pipeline-kit init --mode orchestrator --ide cursor
pipeline-kit workflows --scaffold my-review
```

Do not reuse a first-party name (`feature-development`, `jira-story`, …).
