# Pipeline Kit documentation

Local Docusaurus site for the kit. It is **not** copied into customer `.pipeline/` packs.

## Information architecture

| Section | Role |
|---------|------|
| **Introduction** | What it is, problems, how it works |
| **Components** | Six pillars: workflows, packages, plugins, capabilities, testing, governance |
| **Getting started** | Install, first project, checklist |
| **Cookbooks** | Tessl-style tutorials (problem → steps → done when) |
| **Workflow reference** | Per-workflow pages |
| **Guides / Adapters / Reference / Troubleshooting / Maintainers** | Deep how-to and ops |

The landing page (`/`) is a dark foundry overview. Markdown under `docs/` uses a polished Infima theme aligned with the same tokens.

The customer adaptation guide in the repo is still
[`CUSTOMER-GUIDE.md`](../CUSTOMER-GUIDE.md) (copied to `.pipeline/docs/` on
`init`).

Agent-oriented index: [`static/llms.txt`](./static/llms.txt).

```bash
cd website
npm install
npm start
```

Open `http://127.0.0.1:3000`. Production preview:

```bash
npm run build
npm run serve
```