(() => {
  "use strict";

  const TOKEN = new URLSearchParams(location.search).get("t") || "";
  const state = { view: "fleet", project: null, pollTimer: null, fleet: [], search: "" };

  // ------------------------------------------------------------------ api

  function api(path, opts = {}) {
    const url = new URL(path, location.origin);
    if (TOKEN) url.searchParams.set("t", TOKEN);
    return fetch(url, {
      method: opts.method || "GET",
      headers: opts.body ? { "Content-Type": "application/json" } : undefined,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    }).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const err = new Error(data.error || `HTTP ${res.status}`);
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    });
  }

  // -------------------------------------------------------------- dom helpers

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (key === "class") node.className = value;
      else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
      else if (value !== undefined && value !== null) node.setAttribute(key, value);
    }
    for (const child of children || []) {
      if (child === undefined || child === null || child === false) continue;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
    return node;
  }

  const SVG_NS = "http://www.w3.org/2000/svg";

  function icon(inner, viewBox = "0 0 24 24", cls = "icon") {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", viewBox);
    svg.setAttribute("class", cls);
    svg.innerHTML = inner;
    return svg;
  }

  const ICONS = {
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>',
    team: '<circle cx="9" cy="8" r="3"/><path d="M3 21v-1a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v1"/><circle cx="17.5" cy="8.5" r="2.3"/><path d="M21 21v-1a4.3 4.3 0 0 0-2.8-4"/>',
    plug: '<path d="M9 2v4M15 2v4M7 10h10v3a5 5 0 0 1-10 0v-3z"/><path d="M8 20h8M12 17v4"/>',
    box: '<path d="M21 8 12 3 3 8l9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>',
    shieldCheck: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3z"/><path d="m9 12 2 2 4-4"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    runs: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 4v5"/>',
    copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    warnTriangle: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>',
    inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    close: '<path d="M18 6 6 18M6 6l12 12"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6M9 9l6 6"/>',
  };

  function chip(text, cls, pulse) {
    return el("span", { class: `chip ${cls || ""} ${pulse ? "pulse" : ""}` }, [text]);
  }

  function panelHead(iconKey, title, countText) {
    const head = el("div", { class: "panel-head" }, [
      icon(ICONS[iconKey], "0 0 24 24", "icon panel-icon"),
      el("h3", {}, [title]),
    ]);
    if (countText) head.appendChild(el("span", { class: "panel-count" }, [countText]));
    return head;
  }

  // ------------------------------------------------------------------ toasts

  function toast(message, { type = "ok", timeout = 4500 } = {}) {
    const stack = document.getElementById("toastStack");
    const node = el("div", { class: `toast ${type}` }, [
      icon(type === "bad" ? ICONS.warnTriangle : ICONS.check, "0 0 24 24", "icon"),
      el("div", { class: "msg" }, [message]),
      el("button", { class: "btn-ghost", onclick: () => node.remove() }, [icon(ICONS.close, "0 0 24 24", "icon")]),
    ]);
    stack.appendChild(node);
    if (timeout) setTimeout(() => node.remove(), timeout);
  }

  function setStatus(text, cls) {
    const pill = document.getElementById("connStatus");
    pill.className = `status-pill ${cls || ""}`;
    pill.querySelector(".status-text").textContent = text;
  }

  // -------------------------------------------------------------- severity

  function severity(row) {
    if (!row.reachable) return "bad";
    if (!row.installed) return "warn";
    const runs = row.runs || [];
    if (runs.some((r) => r.status === "blocked" || r.status === "error")) return "bad";
    if (row.behind) return "warn";
    if (runs.some((r) => (r.pending_gates || []).length)) return "warn";
    return "ok";
  }

  const SEV_RANK = { bad: 0, warn: 1, ok: 2 };

  // ---------------------------------------------------------------- fleet

  function fleetChips(row) {
    const chips = [];
    if (!row.reachable) return [chip("stale — path unreachable", "bad")];
    if (!row.installed) return [chip("not installed", "warn")];
    chips.push(chip(`${row.mode || "kit"}`, ""));
    if (row.version) chips.push(chip(`v${row.version}`, row.behind ? "warn" : ""));
    if (row.behind) chips.push(chip(`behind v${row.current_kit_version}`, "warn"));
    const runs = row.runs || [];
    const active = runs.filter((r) => r.status === "running" || r.status === "awaiting_approval");
    if (active.length) chips.push(chip(`${active.length} active run${active.length > 1 ? "s" : ""}`, "ok", true));
    const pendingGates = runs.reduce((n, r) => n + (r.pending_gates || []).length, 0);
    if (pendingGates) chips.push(chip(`${pendingGates} gate${pendingGates > 1 ? "s" : ""} awaiting approval`, "warn"));
    if (row.observability && row.observability.enabled) {
      const unflushed = row.observability.unflushed_bytes || 0;
      chips.push(chip(unflushed > 0 ? "obs: unflushed" : "obs: flushed", unflushed > 0 ? "warn" : "ok"));
    }
    return chips;
  }

  // The portal reports drift, it never runs init/update itself (see README) —
  // this is only ever a copy-pasteable hint, never a button that acts.
  function fixCommand(row) {
    if (!row.reachable) return null;
    if (!row.installed) return `pipeline-kit init "${row.path}"`;
    if (row.behind) return `pipeline-kit update "${row.path}"`;
    return null;
  }

  function fixHint(row) {
    const cmd = fixCommand(row);
    if (!cmd) return null;
    const code = el("code", {}, [cmd]);
    const copyBtn = el(
      "button",
      {
        class: "btn-ghost",
        title: "Copy command",
        onclick: (ev) => {
          ev.stopPropagation();
          navigator.clipboard?.writeText(cmd).then(() => toast("Command copied to clipboard."), () => {});
        },
      },
      [icon(ICONS.copy, "0 0 24 24", "icon")]
    );
    return el("div", { class: "fix-hint" }, [code, copyBtn]);
  }

  function matchesSearch(row, query) {
    if (!query) return true;
    const haystack = `${row.label || ""} ${row.path} ${row.team || ""}`.toLowerCase();
    return haystack.includes(query);
  }

  function renderFleet() {
    const container = document.getElementById("fleetGroups");
    container.innerHTML = "";
    const query = state.search.trim().toLowerCase();
    const visible = state.fleet.filter((row) => matchesSearch(row, query));

    const subtitle = document.getElementById("fleetSubtitle");
    const teamCount = new Set(state.fleet.map((r) => r.team || "ungrouped")).size;
    subtitle.textContent = state.fleet.length
      ? `${state.fleet.length} project${state.fleet.length === 1 ? "" : "s"} across ${teamCount} team${teamCount === 1 ? "" : "s"}`
      : "No projects registered yet.";

    if (!state.fleet.length) {
      container.appendChild(
        el("div", { class: "empty" }, [icon(ICONS.inbox, "0 0 24 24", "icon"), el("div", {}, ["No projects registered yet. Click “Add project” above."])])
      );
      return;
    }
    if (!visible.length) {
      container.appendChild(el("div", { class: "empty" }, [icon(ICONS.inbox, "0 0 24 24", "icon"), el("div", {}, [`No projects match “${state.search}”.`])]));
      return;
    }

    const groups = new Map();
    for (const row of visible) {
      const team = row.team || "ungrouped";
      if (!groups.has(team)) groups.set(team, []);
      groups.get(team).push(row);
    }

    for (const [team, rows] of [...groups.entries()].sort()) {
      rows.sort((a, b) => SEV_RANK[severity(a)] - SEV_RANK[severity(b)]);
      const cards = rows.map((row) =>
        el(
          "div",
          { class: `card sev-${severity(row)}`, onclick: () => openProject(row.path) },
          [
            el("div", { class: "card-top" }, [
              el("div", { class: "card-icon" }, [icon(ICONS.folder, "0 0 24 24", "icon")]),
              el("div", { style: "min-width:0;flex:1" }, [
                el("div", { class: "card-title", title: row.label || row.path }, [row.label || row.path.split(/[\\/]/).pop()]),
                el("div", { class: "card-path", title: row.path }, [row.path]),
              ]),
            ]),
            el("div", { class: "chips" }, fleetChips(row)),
            fixHint(row),
          ]
        )
      );
      container.appendChild(
        el("div", { class: "team-group" }, [
          el("div", { class: "team-group-head" }, [
            icon(ICONS.team, "0 0 24 24", "icon"),
            el("h2", {}, [team]),
            el("span", { class: "team-count" }, [String(rows.length)]),
          ]),
          el("div", { class: "cards" }, cards),
        ])
      );
    }
  }

  function loadFleet() {
    return api("/api/fleet")
      .then((payload) => {
        state.fleet = payload.projects || [];
        renderFleet();
        setStatus("connected", "ok");
      })
      .catch((err) => {
        setStatus("disconnected", "bad");
        toast(`Could not reach the portal server: ${err.message}`, { type: "bad" });
      });
  }

  document.getElementById("fleetSearch").addEventListener("input", (ev) => {
    state.search = ev.target.value;
    renderFleet();
  });

  // ------------------------------------------------------------ add drawer

  const drawer = document.getElementById("addDrawer");
  const backdrop = document.getElementById("backdrop");

  function openDrawer() {
    drawer.classList.add("open");
    backdrop.classList.add("open");
    document.getElementById("addPath").focus();
  }

  function closeDrawer() {
    drawer.classList.remove("open");
    backdrop.classList.remove("open");
  }

  document.getElementById("openAddDrawer").addEventListener("click", openDrawer);
  document.getElementById("closeAddDrawer").addEventListener("click", closeDrawer);
  document.getElementById("cancelAdd").addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && drawer.classList.contains("open")) closeDrawer();
  });

  document.getElementById("addForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const form = new FormData(ev.target);
    const path = form.get("path");
    api("/api/registry/add", { method: "POST", body: { path, team: form.get("team"), label: form.get("label") } })
      .then(() => {
        ev.target.reset();
        closeDrawer();
        toast(`Added ${path} to the fleet.`);
        loadFleet();
      })
      .catch((err) => toast(`Could not add project: ${err.message}`, { type: "bad" }));
  });

  document.getElementById("backToFleet").addEventListener("click", () => showView("fleet"));

  // ------------------------------------------------------------- project

  function toggleRow(label, detail, on, locked, onToggle) {
    const sw = el("div", { class: `switch ${on ? "on" : ""} ${locked ? "locked" : ""}`, title: locked ? "Read-only or requires a license" : "" }, [
      el("div", { class: "knob" }),
    ]);
    if (!locked) sw.addEventListener("click", () => onToggle(!on));
    return el("div", { class: "row" }, [
      el("div", {}, [el("div", { class: "row-name" }, [label]), el("div", { class: "row-detail" }, [detail || ""])]),
      sw,
    ]);
  }

  function writeToggle(path, body, onDone) {
    api(path, { method: "POST", body })
      .then(() => onDone())
      .catch((err) => {
        if (err.status === 409) {
          toast("config.json changed since this view was loaded — refreshing.", { type: "warn" });
        } else {
          toast(`Toggle failed: ${err.message}`, { type: "bad" });
        }
        openProject(state.project, { keepTab: true });
      });
  }

  function renderSetup(data) {
    const pane = document.getElementById("tabSetup");
    pane.innerHTML = "";
    const readOnly = !!data.read_only;

    // Features
    const featureRows = [];
    const flags = (data.features && data.features.flags) || {};
    const flagEntries = Object.entries(flags);
    for (const [id, info] of flagEntries) {
      const locked = readOnly || id === "jira-intake" || id === "agent-observability";
      featureRows.push(
        toggleRow(id, info.config_key, info.state === "on", locked, (next) =>
          writeToggle("/api/features/toggle", { path: data.path, id, on: next, config_mtime: data.config_mtime }, () =>
            openProject(data.path, { keepTab: true })
          )
        )
      );
    }
    pane.appendChild(el("div", { class: "panel" }, [panelHead("box", "Features", `${flagEntries.length}`), ...featureRows]));

    // Plugins
    const plugins = data.plugins || {};
    const pluginRows = [];
    if (plugins.graphify) {
      const fresh = (plugins.graphify.freshness || {}).state || "unknown";
      pluginRows.push(
        toggleRow(
          "graphify",
          `graph: ${fresh}`,
          !!plugins.graphify.enabled || plugins.graphify.state === "ready",
          readOnly,
          (next) => writeToggle("/api/plugins/toggle", { path: data.path, name: "graphify", on: next }, () => openProject(data.path, { keepTab: true }))
        )
      );
    }
    if (plugins.archify) {
      pluginRows.push(
        toggleRow("archify", plugins.archify.fallback ? `fallback: ${plugins.archify.fallback}` : "", !!plugins.archify.enabled, readOnly, (next) =>
          writeToggle("/api/plugins/toggle", { path: data.path, name: "archify", on: next }, () => openProject(data.path, { keepTab: true }))
        )
      );
    }
    pane.appendChild(el("div", { class: "panel" }, [panelHead("plug", "Plugins"), ...pluginRows]));

    // Extensions
    const ext = data.extensions || {};
    const extBody = [];
    if (ext.mode === "orchestrator") {
      extBody.push(el("div", { class: "row-detail", style: "font-size:12px;padding:6px 0" }, [`first-party: ${(ext.first_party || []).join(", ") || "none"}`]));
      extBody.push(
        el("div", { class: "row-detail", style: "font-size:12px;padding:6px 0" }, [
          `associate (declared, not loaded): ${(ext.associate_declared || []).join(", ") || "none"}`,
        ])
      );
    } else {
      const workflows = ext.workflows || [];
      const table = el("table", {}, [
        el("thead", {}, [el("tr", {}, [el("th", {}, ["Workflow"]), el("th", {}, ["Configured"]), el("th", {}, ["Classes"])])]),
        el(
          "tbody",
          {},
          workflows.map((wf) =>
            el("tr", {}, [
              el("td", {}, [wf.name]),
              el("td", {}, [wf.configured ? chip("yes", "ok") : chip("no", "")]),
              el("td", {}, [(wf.classes || []).join(", ") || "—"]),
            ])
          )
        ),
      ]);
      extBody.push(workflows.length ? table : el("div", { class: "empty" }, ["No workflows found."]));
    }
    pane.appendChild(el("div", { class: "panel" }, [panelHead("box", "Extensions"), ...extBody]));

    // Doctor
    const doctor = data.doctor || {};
    const checks = Object.entries(doctor.checks || {});
    const doctorRows = checks.map(([label, passed]) =>
      el("div", { class: "row" }, [el("div", { class: "row-name" }, [label]), chip(passed ? "ok" : "missing", passed ? "ok" : "bad")])
    );
    pane.appendChild(
      el("div", { class: "panel" }, [panelHead("shieldCheck", "Doctor", `${doctor.passed || 0}/${doctor.total || 0}`), ...doctorRows])
    );
  }

  function renderHealth(data, health) {
    const pane = document.getElementById("tabHealth");
    pane.innerHTML = "";

    const runs = data.runs || [];
    const boards = data.boards || [];
    const runRows = [
      ...runs.map((r) => ({ ...r, kind: "orchestrator" })),
      ...boards.map((b) => ({ ...b, kind: "kit", status: b.current_status, current_node: b.current_step })),
    ];
    const runTable = el("table", {}, [
      el("thead", {}, [el("tr", {}, [el("th", {}, ["Slug"]), el("th", {}, ["Workflow"]), el("th", {}, ["Step"]), el("th", {}, ["Status"]), el("th", {}, ["Gates"])])]),
      el(
        "tbody",
        {},
        runRows.map((r) =>
          el("tr", {}, [
            el("td", {}, [r.slug]),
            el("td", {}, [r.workflow || "—"]),
            el("td", {}, [r.current_node || "—"]),
            el("td", {}, [chip(r.status || "—", r.status === "blocked" || r.status === "error" ? "bad" : r.status === "awaiting_approval" ? "warn" : "ok")]),
            el("td", {}, [(r.pending_gates || []).join(", ") || "—"]),
          ])
        )
      ),
    ]);
    pane.appendChild(
      el("div", { class: "panel" }, [
        panelHead("runs", "Runs & boards", String(runRows.length)),
        runRows.length ? runTable : el("div", { class: "empty" }, [icon(ICONS.inbox, "0 0 24 24", "icon"), el("div", {}, ["No runs yet."])]),
      ])
    );

    if (!health || !health.available) {
      pane.appendChild(
        el("div", { class: "panel" }, [
          panelHead("chart", "Ledger scores"),
          el("div", { class: "empty" }, [(health && health.reason) || "No ledger yet."]),
        ])
      );
      return;
    }
    const scoreTable = el("table", {}, [
      el("thead", {}, [
        el("tr", {}, [
          el("th", {}, ["Step"]),
          el("th", { class: "num" }, ["Waste"]),
          el("th", { class: "num" }, ["Retry"]),
          el("th", { class: "num" }, ["Denied"]),
          el("th", { class: "num" }, ["Verify cov."]),
          el("th", { class: "num" }, ["Context peak"]),
          el("th", { class: "num" }, ["Tokens in/out"]),
        ]),
      ]),
      el(
        "tbody",
        {},
        (health.steps || []).map((s) =>
          el("tr", {}, [
            el("td", {}, [s.step]),
            el("td", { class: "num" }, [pct(s.waste_ratio)]),
            el("td", { class: "num" }, [pct(s.retry_ratio)]),
            el("td", { class: "num" }, [String(s.denied_count || 0)]),
            el("td", { class: "num" }, [pct(s.verify_coverage)]),
            el("td", { class: "num" }, [s.context_peak_percent != null ? `${s.context_peak_percent.toFixed(0)}%` : "—"]),
            el("td", { class: "num" }, [`${s.input_tokens || 0} / ${s.output_tokens || 0}`]),
          ])
        )
      ),
    ]);
    pane.appendChild(el("div", { class: "panel" }, [panelHead("chart", "Ledger scores", `${health.event_count || 0} events`), scoreTable]));
  }

  function pct(value) {
    return value == null ? "—" : `${(value * 100).toFixed(0)}%`;
  }

  function renderConfig(data) {
    const pane = document.getElementById("tabConfig");
    pane.innerHTML = "";
    pane.appendChild(
      el("div", { class: "panel" }, [
        panelHead("box", "config.json — read-only"),
        el("div", { class: "row-detail", style: "margin-bottom:8px" }, ["Edit via the CLI commands shown in Setup, not here."]),
        el("pre", { class: "config-block" }, [JSON.stringify(data.config || {}, null, 2)]),
      ])
    );
  }

  function activateTab(name) {
    for (const btn of document.querySelectorAll(".tab")) btn.classList.toggle("active", btn.dataset.tab === name);
    for (const pane of ["Setup", "Health", "Config"]) {
      document.getElementById(`tab${pane}`).hidden = pane.toLowerCase() !== name;
    }
  }

  document.getElementById("projectTabs").addEventListener("click", (ev) => {
    const btn = ev.target.closest(".tab");
    if (btn) activateTab(btn.dataset.tab);
  });

  function openProject(path, opts = {}) {
    state.project = path;
    showView("project");
    document.getElementById("projectTitle").textContent = path.split(/[\\/]/).pop();
    document.getElementById("projectPath").textContent = path;
    if (!opts.keepTab) {
      for (const id of ["tabSetup", "tabHealth", "tabConfig"]) {
        document.getElementById(id).innerHTML = '<div class="skeleton"></div>';
      }
    }
    Promise.all([api(`/api/project?path=${encodeURIComponent(path)}`), api(`/api/health?path=${encodeURIComponent(path)}`).catch(() => null)])
      .then(([data, health]) => {
        renderSetup(data);
        renderHealth(data, health);
        renderConfig(data);
        if (!opts.keepTab) activateTab("setup");
      })
      .catch((err) => toast(`Could not load project: ${err.message}`, { type: "bad" }));
  }

  function showView(name) {
    state.view = name;
    document.getElementById("fleetView").hidden = name !== "fleet";
    document.getElementById("projectView").hidden = name !== "project";
    const crumbs = document.getElementById("crumbs");
    crumbs.innerHTML = "";
    if (name === "fleet") {
      crumbs.appendChild(el("b", {}, ["Fleet"]));
      loadFleet();
    } else {
      crumbs.append("Fleet / ", el("b", {}, [state.project]));
    }
  }

  // -------------------------------------------------------------- polling

  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(() => {
      if (state.view === "fleet") loadFleet();
    }, 5000);
  }

  setStatus("connecting…");
  showView("fleet");
  startPolling();
})();
