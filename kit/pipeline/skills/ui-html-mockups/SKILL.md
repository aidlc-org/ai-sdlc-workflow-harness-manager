---
name: ui-html-mockups
description: >-
  Load when ui-designer-agent must write static HTML/CSS mockups under
  features/{slug}/ui/. One file per primary screen. CSS variables from the
  design tokens. No product frameworks and no copy into the app tree.
---

# UI — HTML mockups

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | ui-designer-agent during U4 |
| Adapt | Do not add a product folder or CSS framework. |

Mockups are the **visual contract**. Developer translates them into the
product stack. Never copy these files into application source.

## Rules

- Static HTML + CSS only. No React, Vue, build step, or package.json.
- CSS variables on `:root` matching `ui-design.md` tokens.
- `features/{slug}/ui/index.html` lists every screen with relative links.
- One file per primary screen: `features/{slug}/ui/{kebab}.html`.
- Empty / loading / error / denied / success: sections on the same file
  (`id="state-empty"` …) unless they are distinct routes in the inventory.
- No external webfonts or CDNs. System font stack is enough.
- No scripts unless a `<details>` disclosure cannot express the nav.

## File skeleton

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{Screen} — {slug}</title>
    <style>
      :root {
        --color-bg: {token};
        --color-text: {token};
        --color-accent: {token};
        --focus-ring: {token};
      }
      :focus-visible { outline: 2px solid var(--focus-ring); }
      body { font-family: system-ui, sans-serif; background: var(--color-bg); color: var(--color-text); }
    </style>
  </head>
  <body>
    <a href="#main">Skip to content</a>
    <header>{nav}</header>
    <main id="main">{screen}</main>
  </body>
</html>
```

## Index

`ui/index.html` is a table: screen id, name, actors, link, states present.

## Do not

Inline product API keys · screenshot PNGs as the only artifact · minify to
the point BA cannot read labels · ship `node_modules`.
