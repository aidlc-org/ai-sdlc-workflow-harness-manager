---
title: Knowledge and plugins
description: Turn on the QA knowledge overlay and optional Graphify/Archify plugins without changing the default feature ladder until you are ready.
---

**Goal:** Build a code-graph-informed knowledge base and optionally register Graphify and Archify — all **opt-in**.

**Components used:** [Knowledge](/docs/capabilities/knowledge), [Plugins](/docs/capabilities/plugins), [Graphify](/docs/capabilities/graphify), [Archify](/docs/capabilities/archify).

## Prerequisites

- Project with `.pipeline/` from `init`
- Network access to install plugin CLIs / skills when you choose those steps

## Steps

### 1. Knowledge init

```bash
cd /path/to/your-app
pipeline-kit knowledge init
```

`init` does **not** run Graphify for you. Follow the knowledge docs for extract → model delta → cases.

**Verify:** knowledge layout exists under the paths documented in [Knowledge base](/docs/capabilities/knowledge).

### 2. Extract a graph (Graphify)

```bash
pipeline-kit plugins install graphify
# then follow Graphify skill / CLI to produce graphify-out/graph.json
pipeline-kit knowledge extract   # when your flow uses kit extract
```

Details: [Graphify plugin](/docs/capabilities/graphify).

### 3. Architecture HTML (Archify)

```bash
pipeline-kit plugins install archify
```

Pins Archify **v2.16.0** for interactive architecture HTML. **Mermaid in `architecture.md` stays required** — Archify does not replace it.

Details: [Archify plugin](/docs/capabilities/archify).

### 4. Bootstrap workflow (curator)

When you need the one-time QA overlay curator path:

→ [Knowledge bootstrap workflow](/docs/workflows/knowledge-bootstrap)

The feature-development ladder stays unchanged until knowledge-related flags are on ([feature flags](/docs/capabilities/feature-flags)).

### 5. Confirm plugins are listed

```bash
pipeline-kit plugins list
pipeline-kit doctor
```

## Done when

- [ ] Knowledge init completed  
- [ ] Graph artifact available if you need graph-based cases  
- [ ] Graphify/Archify only present if you installed them (`init` never forces them)  

## Next

- [Observability, eval, and testing](/docs/cookbooks/observability-eval-testing)
- [Plugins overview](/docs/capabilities/plugins)
- [Components — testing](/docs/components/testing)
