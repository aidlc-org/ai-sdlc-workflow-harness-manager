# Orchestrator mode

Optional `--mode orchestrator`. The chain lives in this Python package
(installed as `pipeline_orchestrator`). `init` does **not** copy
`agents/`, `skills/`, `loader/`, or `workflows/`.

Associates add extra workflows with `pipeline_extensions/` in the
customer app, or a `pipeline_kit.workflows` entry point. Kit mode never
loads those files.

## Contents

1. [Steps](#steps)
2. [Model choice](#model-choice)

## Steps

1. From the kit checkout, install the extra into the same CLI:

```bash
uv tool install -e ".[orchestrator]"
```

2. Initialize the product:

```bash
cd /path/to/your-app
pipeline-kit init --mode orchestrator --ide cursor
pipeline-kit run --slug checkout-redesign --workflow feature-development \
  --request "redesign checkout so guests can pay without an account"
```

Copy-ready examples: [`extensions/orchestrator/`](../extensions/orchestrator/).
Scaffold: `pipeline-kit workflows --scaffold NAME`.

Public import (do not change): `from pipeline_orchestrator.graph import WorkflowSpec`.

## Model choice

The sealed graph still picks the next agent. Before each agent runs, the engine asks a model decider which Cursor model should execute that step. `.pipeline/config.json` selects the implementation:

```json
"orchestrator": {
  "decider": "jev",
  "fallback_model": "composer-2.5",
  "models": {
    "steps": {},
    "candidates": [
      "composer-2.5",
      "grok-4.5",
      "grok-4.6",
      "grok-4.7",
      "claude-opus-5",
      "gpt-5.5",
      "gpt-5.6-sol"
    ]
  },
  "jev": { "model": "jev-latest", "min_confidence": 0.5 }
}
```

`jev` (default) sends one TypeSafe Choice. It does not send the full Cursor catalog. `models.candidates` is the shortlist Jev may pick from, intersected with this account’s live list. An empty `candidates` array sends every catalog id. Each option includes `fit` and a per-agent `for_this_agent` line so planning and review prefer Claude Opus or GPT, and implementation prefers Composer. Set `TYPESAFE_API_KEY`. A confident answer becomes `Agent.create(model=...)`. Confidence below `min_confidence`, a missing key, or an API failure uses `fallback_model` and the run continues.

### Add a model

The id must already appear in this Cursor account’s model list. A name that is only in config is skipped.

Put the id on `models.candidates`. Add details in `models.cards`, or as an object in the same list:

```json
"models": {
  "candidates": [
    "composer-2.5",
    "claude-opus-5",
    {
      "id": "glm-5.2",
      "kind": "reasoning",
      "fit": "Strong reasoning model. Fit for planning, architecture, and review.",
      "display_name": "GLM 5.2",
      "description": "Use for requirements and review, not fast code edits."
    }
  ],
  "cards": {
    "composer-2.5": {
      "kind": "coding",
      "fit": "Fast coding model. Poor fit for planning and review."
    }
  }
}
```

`kind` is `coding`, `reasoning`, `general`, or `writing`. That value drives `for_this_agent`. `fit`, `display_name`, and `description` override the kit hint and empty Cursor fields. `cards` overlays an id that is already in `candidates`. Remove an id from `candidates` to stop sending it.

`fixed` does not call TypeSafe. It uses a pin when one is set, otherwise `fallback_model`.

### Pin one step

A pin is a model id you choose for one agent. That step uses the id and does not call Jev. Every other agent still asks Jev. Built-in workflows leave `AgentStep.model` empty, so they ask Jev. If the pinned id is not in this Cursor account’s model list, that step stops.

Pin in an associate workflow (or in `graph.py`):

```python
from pipeline_orchestrator.graph import AgentStep, WorkflowSpec

WorkflowSpec(
    name="my-review",
    nodes=[
        AgentStep(id="product-manager-agent"),  # asks Jev
        AgentStep(id="developer-agent", model="composer-2.5"),  # pin; skips Jev
    ],
)
```

Or pin from the project, without editing the graph. In `.pipeline/config.json`:

```json
"orchestrator": {
  "decider": "jev",
  "fallback_model": "composer-2.5",
  "models": {
    "steps": {
      "developer-agent": "composer-2.5"
    }
  }
}
```

`developer-agent` uses `composer-2.5`. The product-manager step still asks Jev. A model set on `AgentStep` wins over `models.steps`.

A run prints a short block per agent before that agent starts. `sent` is the shortlist Jev saw, not the whole Cursor catalog:

```text
model step=product-manager-agent chosen=claude-opus-5 reason=jev decider=jev confidence=0.84
  need: planning: write requirements, scope, and acceptance criteria.
  basis: Jev picked claude-opus-5 (0.84). That model runs.
  sent: composer-2.5, grok-4.5, grok-4.6, grok-4.7, claude-opus-5, gpt-5.5, gpt-5.6-sol
  scores: claude-opus-5 0.84; gpt-5.5 0.10; composer-2.5 0.02
```

`chosen` is the model that will run. `need` is the capability Jev was asked to match. `basis` is why that id was used. `sent` is every candidate id that was also in the catalog. `scores` is the top five Jev probabilities. `jev_choice` appears when Jev named a model but the confidence floor replaced it with `fallback_model`. `--change-class micro` only runs coding steps, so Composer is the expected pick there. Use `feature` to see planning and review.

`--dry-run` prints the same blocks, then a `summary` table of every step. It does not start Cursor agents. It asks Jev when `CURSOR_API_KEY` is set so the catalog is known. Without that key it prints `reason=catalog_unavailable`. Specialist briefs stay the inlined markdown context.
