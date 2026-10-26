---
title: Adapt to your stack
description: Worked deploy, verify and test examples for Node, Java with Maven, .NET, Go and Python projects.
---

The shipped pack is generic. Three things make it fit your stack:

| What | Where | Used by |
|------|-------|---------|
| `deploy.target`, `deploy.targets` | `.pipeline/config.json` | Devops. The parent passes one value as `DEPLOY_TARGET` |
| `verify.rules` | `.pipeline/config.json` | The after-edit hook. It adds a reminder when a path matches |
| Deploy script and runbook | `.pipeline/skills/local-deployment/` | Devops. Builds, starts and health-checks your apps |
| Test commands | `UNIT_TEST_CMD` and `API_TEST_CMD` (environment), or the tester skills | Tester |

`config.json` has no keys for build or test commands. The commands live in the deploy script and the tester skills. Do not invent new keys. See the [config reference](/docs/reference/config) for the real list, [adapt config.json](/docs/guides/config), [adapt local deploy](/docs/guides/local-deploy) and [adapt tests](/docs/guides/tests).

## Step 1: write the script once

The shipped `deploy-local.sh` exits `1` until you rewrite it. It takes a feature slug and a target. It must write `features/{slug}/deploy-result.env` with `OVERALL=` set to `passed` or `failed`, plus one health line per surface. Keep that contract and replace the placeholder body.

This skeleton works for every stack below. Only the three commands per target change.

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SLUG="${1:-}"; TARGET="${2:-auto}"
[[ -z "$SLUG" ]] && { echo "usage: deploy-local.sh <slug> [target]" >&2; exit 2; }
FEAT="$ROOT/features/$SLUG"; mkdir -p "$FEAT"
RESULT="$FEAT/deploy-result.env"; LOG="$FEAT/deploy-log.txt"; : >"$LOG"
log() { printf '%s\n' "$*" | tee -a "$LOG"; }

PORT=8080
HEALTH="http://127.0.0.1:$PORT/health"

healthy() { curl -fsS --max-time 3 "$HEALTH" >/dev/null 2>&1; }

cd "$ROOT"
# 1. build   (stack specific)
# 2. serve   (stack specific, only if healthy fails)
# 3. probe   (retry healthy for up to 30 seconds)

if healthy; then
  printf 'OVERALL=passed\nDEPLOY_TARGET=%s\nAPP_HEALTH=ok\n' "$TARGET" >"$RESULT"
else
  printf 'OVERALL=failed\nDEPLOY_TARGET=%s\nAPP_HEALTH=down\n' "$TARGET" >"$RESULT"
  exit 1
fi
```

Rules that apply to every stack:

- Bind to `127.0.0.1` only.
- If the port already answers, reuse it. Do not start a second copy and do not kill a process the script did not start. See [reuse listeners](/docs/troubleshooting/deploy-listeners).
- Put no tokens or secrets in the script, HANDOFF files or the runbook.
- Keep the target names in `deploy.targets` identical to the names the script handles.
- The script is bash. On Windows, run the pipeline from Git Bash or WSL.

Also fill in `.pipeline/skills/local-deployment/assets/local-deploy-runbook.md` with the same commands in its table, so a human can follow it.

## Step 2: pick your stack

Each example gives the `deploy` and `verify` blocks for `config.json`, the three script commands, and the test command. Merge the blocks into your existing file. Do not replace the whole file.

### Node (React or Vite plus an API)

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "web", "api", "both"]
},
"verify": {
  "rules": [
    {
      "match": "/web/",
      "message": "You edited the UI. Run npm run build in web/ and keep empty, error and loading states."
    },
    {
      "match": "/api/",
      "message": "You edited the API. Run npm test in api/ and check GET /health."
    }
  ]
}
```

| Step | Command |
|------|---------|
| Build | `npm ci && npm run build` in `web/` |
| Serve | `npm run preview -- --host 127.0.0.1 --port 4173` for web. `npm start` in `api/` on its port |
| Probe | `GET http://127.0.0.1:4173/` and `GET http://127.0.0.1:3000/health` |
| Unit tests | `UNIT_TEST_CMD="npm test --prefix web"` |

If the repo already has Playwright, tell the tester to use that project. Do not add a second Playwright tree.

### Java with Maven (Spring Boot service)

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "service"]
},
"verify": {
  "rules": [
    {
      "match": "/src/main/java/",
      "message": "You edited service code. Run mvn -q test and keep the actuator health endpoint working."
    },
    {
      "match": "pom.xml",
      "message": "You edited pom.xml. Declare new dependencies in the Architect handoff first."
    }
  ]
}
```

| Step | Command |
|------|---------|
| Build | `mvn -q -DskipTests package` |
| Serve | `java -jar target/app.jar --server.address=127.0.0.1 --server.port=8080` |
| Probe | `GET http://127.0.0.1:8080/actuator/health` |
| Unit tests | `UNIT_TEST_CMD="mvn -q test"` |
| API tests | `API_TEST_CMD="mvn -q verify"` |

Set `HEALTH` in the skeleton to the actuator URL. For Gradle, use `./gradlew test` and `./gradlew bootJar`.

Dependency gates read `package.json` and `requirements.txt` by default (`code_minimalism.manifest_files`). The write hook does not parse Maven or Gradle manifests, so keep the Architect declaration in the HANDOFF and check it in review.

### .NET

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "api"]
},
"verify": {
  "rules": [
    {
      "match": ".cs",
      "message": "You edited C# code. Run dotnet build and dotnet test before reporting done."
    },
    {
      "match": "appsettings",
      "message": "You edited settings. Keep secrets out of appsettings files."
    }
  ]
}
```

| Step | Command |
|------|---------|
| Build | `dotnet build -c Release` |
| Serve | `dotnet run --project src/Api -c Release --no-build --urls http://127.0.0.1:5080` |
| Probe | `GET http://127.0.0.1:5080/health` |
| Unit tests | `UNIT_TEST_CMD="dotnet test"` |

### Go

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "api"]
},
"verify": {
  "rules": [
    {
      "match": ".go",
      "message": "You edited Go code. Run go vet ./... and go test ./... before reporting done."
    }
  ]
}
```

| Step | Command |
|------|---------|
| Build | `go build -o bin/app ./cmd/app` |
| Serve | `./bin/app` listening on `127.0.0.1:8080` |
| Probe | `GET http://127.0.0.1:8080/health` |
| Unit tests | `UNIT_TEST_CMD="go test ./..."` |

### Python (FastAPI or Flask)

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "api"]
},
"verify": {
  "rules": [
    {
      "match": "/app/",
      "message": "You edited the API. Run pytest -q and check GET /health."
    },
    {
      "match": "requirements.txt",
      "message": "You edited requirements.txt. Declare new dependencies in the Architect handoff first."
    }
  ]
}
```

| Step | Command |
|------|---------|
| Build | `pip install -r requirements.txt` (optional) |
| Serve | `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Probe | `GET http://127.0.0.1:8000/health` |
| Unit tests | `UNIT_TEST_CMD="pytest -q"` |

The default unit fallback is already `pytest` when a `tests/` tree exists, so you can often leave `UNIT_TEST_CMD` unset.

## Step 3: point the tester at your runners

The tester skills read an override first, then fall back to defaults.

| Layer | Override | Fallback in the skill |
|-------|----------|-----------------------|
| Unit | `UNIT_TEST_CMD` or `unit_test_cmd` in `features/{slug}/test-strategy.md` | `pytest` if `tests/` exists, else `npm test` |
| API | `API_TEST_CMD` or `api_test_cmd` in `test-strategy.md` | `pytest` |
| UI e2e | Edit the paths in `.pipeline/skills/testing-ui-playwright/SKILL.md` | `automation-tests/` |

Set the environment variable in the shell that launches the agent, or change the fallback line in the skill if the whole team uses one runner. Do not add a new test framework. With no UI, skip Playwright and keep unit and API layers. See [test layers](/docs/troubleshooting/test-layers).

## Step 4: check it

1. Parse `.pipeline/config.json`. A broken file stops the hooks and loader. Run `pipeline-kit doctor`.
2. Run the script by hand from the repo root: `.pipeline/skills/local-deployment/scripts/deploy-local.sh try-deploy auto`. Read `features/try-deploy/deploy-result.env`.
3. Run it a second time while the app is up. It must reuse the listener and still report `OVERALL=passed`.
4. Run a micro change such as "Change one label" and watch for the `verify.rules` reminder after the edit.

Until the script reports `OVERALL=passed` for your repo, devops must not report success. If you want the pipeline to finish without a preview, document a "build only" target in the runbook.
