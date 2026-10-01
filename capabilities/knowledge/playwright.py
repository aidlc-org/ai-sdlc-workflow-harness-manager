"""Project reviewed cases.json into existing automation-tests Playwright specs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ALLOWED_VERBS = frozenset(
    {
        "goto",
        "fill",
        "click",
        "expect_visible",
        "expect_text",
        "expect_disabled",
        "expect_count",
    }
)
BROWSER_LAYERS = frozenset({"ui", "e2e", "a11y"})
AUTH_FIXTURE = re.compile(r"^FIX-.+-SIGNED-IN", re.I)
LOGIN_ACTION = re.compile(r"(login|sign[-_ ]?in|open-console|open_console)", re.I)
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


class PlaywrightError(ValueError):
    """cases.json or locators.json cannot be projected."""


def generate_playwright(project: Path, slug: str) -> list[Path]:
    try:
        from pipeline_kit.paths import feature_dir as _fd
        base = _fd(project, slug)
    except Exception:
        base = project / "features" / slug
    cases_path = base / "test-design" / "cases.json"
    locators_path = base / "test-design" / "locators.json"
    if not cases_path.is_file():
        raise PlaywrightError(f"INPUT_MISSING: missing {cases_path}")
    payload = _read_json(cases_path)
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        raise PlaywrightError("cases.json must contain a cases array")
    browser = [item for item in cases if isinstance(item, dict) and _layer(item) in BROWSER_LAYERS]
    if not browser:
        return []
    if not locators_path.is_file():
        raise PlaywrightError(f"INPUT_MISSING: missing {locators_path}")
    locators = _locator_index(_read_json(locators_path))
    pw_dir = _playwright_dir(project)
    spec_dir = pw_dir / "specs" / slug
    written: list[Path] = []
    needs_auth = any(_has_auth_fixture(item) for item in browser)
    if needs_auth:
        written.append(_write_auth_setup(spec_dir, slug))
    for item in browser:
        written.append(
            _write_spec(
                spec_dir,
                slug,
                item,
                locators,
                needs_auth and _has_auth_fixture(item),
            )
        )
    return written


def _playwright_dir(project: Path) -> Path:
    cfg_path = project / ".pipeline" / "config.json"
    directory = "automation-tests"
    if cfg_path.is_file():
        try:
            loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        block = loaded.get("test_design") if isinstance(loaded, dict) else None
        if isinstance(block, dict) and isinstance(block.get("playwright_dir"), str):
            directory = block["playwright_dir"]
    return project / directory


def _layer(item: dict[str, Any]) -> str:
    return str(item.get("level") or item.get("layer") or "").strip().lower()


def _has_auth_fixture(item: dict[str, Any]) -> bool:
    fixtures = item.get("fixtures") or item.get("preconditions") or []
    if not isinstance(fixtures, list):
        fixtures = [fixtures]
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        ident = str(fixture.get("id") or "")
        kind = str(fixture.get("kind") or "")
        if kind.lower() == "auth" or AUTH_FIXTURE.match(ident):
            return True
    return False


def _locator_index(payload: dict[str, Any]) -> dict[tuple[str, int], dict[str, str]]:
    index: dict[tuple[str, int], dict[str, str]] = {}
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, dict):
        return index
    for case_id, body in cases.items():
        if not isinstance(body, dict):
            continue
        steps = body.get("steps")
        if not isinstance(steps, list):
            continue
        for offset, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            raw_index = step.get("index", offset + 1)
            try:
                step_index = int(raw_index)
            except (TypeError, ValueError):
                step_index = offset + 1
            role = step.get("role")
            name = step.get("name")
            if isinstance(role, str) and isinstance(name, str) and role.strip() and name.strip():
                index[(str(case_id), step_index)] = {
                    "role": role.strip(),
                    "name": name.strip(),
                }
    return index


def _write_auth_setup(spec_dir: Path, slug: str) -> Path:
    depth = _lib_prefix(slug)
    state = f"artifacts/{slug}/.auth/storageState.json"
    source = (
        f"// feature: {slug}\n"
        "import { test as setup, expect } from '@playwright/test';\n"
        f"import {{ captureReviewScreenshot }} from '{depth}lib/captureReviewScreenshot';\n\n"
        "const username = process.env.E2E_PRODUCER_USERNAME;\n"
        "const password = process.env.E2E_PRODUCER_PASSWORD;\n"
        "if (!username || !password) {\n"
        "  throw new Error('E2E_PRODUCER_USERNAME and E2E_PRODUCER_PASSWORD must be set');\n"
        "}\n\n"
        "setup('authenticate', async ({ page }) => {\n"
        "  const base = process.env.E2E_BASE_URL || '/';\n"
        "  await page.goto(base);\n"
        "  await page.getByRole('textbox', { name: /email|username/i }).fill(username);\n"
        "  await page.getByLabel(/password/i).fill(password);\n"
        "  await page.getByRole('button', { name: /sign in|log in|submit/i }).click();\n"
        "  await expect(page.getByRole('navigation').or(page.getByRole('main'))).toBeVisible();\n"
        "  await captureReviewScreenshot(page, 'AUTH');\n"
        f"  await page.context().storageState({{ path: '{state}' }});\n"
        "});\n"
    )
    return _write(spec_dir / "auth.setup.ts", source)


def _write_spec(
    spec_dir: Path,
    slug: str,
    item: dict[str, Any],
    locators: dict[tuple[str, int], dict[str, str]],
    use_auth: bool,
) -> Path:
    case_id = str(item.get("id") or "TC")
    title = _js_string(str(item.get("title") or item.get("what") or case_id))
    steps = item.get("steps") or item.get("actions") or []
    if not isinstance(steps, list):
        raise PlaywrightError(f"{case_id}: steps must be an array")
    expected = item.get("expected") or item.get("oracles") or []
    if not isinstance(expected, list):
        expected = []
    body: list[str] = []
    if use_auth:
        state = f"artifacts/{slug}/.auth/storageState.json"
        body.append(f"test.use({{ storageState: '{state}' }});")
        body.append("")
    body.append(f"test('{_js_string(case_id)} {title}', async ({{ page }}) => {{")
    emitted = 0
    for offset, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise PlaywrightError(f"{case_id} step {offset}: expected an object")
        if use_auth and _is_login_step(step):
            continue
        body.extend(_emit_step(case_id, offset, step, locators.get((case_id, offset))))
        emitted += 1
    if emitted == 0 and not use_auth:
        raise PlaywrightError(f"{case_id}: no executable steps")
    for oracle in expected:
        if isinstance(oracle, dict):
            see = oracle.get("see")
            if isinstance(see, str) and see.strip():
                body.append(
                    f"  await expect(page.getByText({_js_quote(see.strip())})).toBeVisible();"
                )
    body.append(f"  await captureReviewScreenshot(page, '{_js_string(case_id)}');")
    body.append("});")
    depth = _lib_prefix(slug)
    source = (
        f"// feature: {slug}\n"
        "import { test, expect } from '@playwright/test';\n"
        f"import {{ captureReviewScreenshot }} from '{depth}lib/captureReviewScreenshot';\n\n"
        + "\n".join(body)
        + "\n"
    )
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", case_id).strip("-") or "case"
    return _write(spec_dir / f"{safe}.spec.ts", source)


def _is_login_step(step: dict[str, Any]) -> bool:
    action = str(step.get("action_id") or step.get("id") or "")
    do = str(step.get("do") or "")
    return bool(LOGIN_ACTION.search(action) or LOGIN_ACTION.search(do))


def _emit_step(
    case_id: str,
    index: int,
    step: dict[str, Any],
    locator: dict[str, str] | None,
) -> list[str]:
    verb = str(step.get("verb") or "").strip().lower()
    if verb not in ALLOWED_VERBS:
        raise PlaywrightError(
            f"INPUT_MISSING: {case_id} step {index} needs verb in {sorted(ALLOWED_VERBS)}"
        )
    if verb == "goto":
        url = step.get("url") or step.get("value") or "process.env.E2E_BASE_URL || '/'"
        if isinstance(url, str) and url.startswith("process.env"):
            return [f"  await page.goto({url});"]
        if isinstance(url, str) and url.startswith(("http://127.0.0.1", "http://localhost", "/")):
            return [f"  await page.goto({_js_quote(url)});"]
        return ["  await page.goto(process.env.E2E_BASE_URL || '/');"]
    control = locator or _control(step.get("control"))
    if not control:
        raise PlaywrightError(
            f"INPUT_MISSING: {case_id} step {index} needs control role/name in cases or locators.json"
        )
    target = (
        f"page.getByRole({_js_quote(control['role'])}, "
        f"{{ name: {_js_quote(control['name'])} }})"
    )
    if verb == "click":
        return [f"  await {target}.click();"]
    if verb == "fill":
        env = step.get("value_from_env")
        if not isinstance(env, str) or not ENV_NAME.fullmatch(env):
            raise PlaywrightError(
                f"INPUT_MISSING: {case_id} step {index} fill requires value_from_env env name"
            )
        return [f"  await {target}.fill(process.env.{env} || '');"]
    if verb == "expect_visible":
        return [f"  await expect({target}).toBeVisible();"]
    if verb == "expect_disabled":
        return [f"  await expect({target}).toBeDisabled();"]
    if verb == "expect_text":
        see = step.get("text") or step.get("see") or control["name"]
        return [f"  await expect({target}).toHaveText({_js_quote(str(see))});"]
    if verb == "expect_count":
        count = step.get("count", 1)
        try:
            n = int(count)
        except (TypeError, ValueError) as exc:
            raise PlaywrightError(f"{case_id} step {index}: count must be an integer") from exc
        return [f"  await expect({target}).toHaveCount({n});"]
    raise PlaywrightError(f"{case_id} step {index}: unsupported verb {verb}")


def _control(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    role = value.get("role")
    name = value.get("name")
    if isinstance(role, str) and isinstance(name, str) and role.strip() and name.strip():
        return {"role": role.strip(), "name": name.strip()}
    return None


def _lib_prefix(slug: str) -> str:
    extra = slug.strip("/").count("/")
    return "../" * (2 + extra)


def _js_quote(value: str) -> str:
    return json.dumps(value)


def _js_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlaywrightError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise PlaywrightError(f"{path} must be a JSON object")
    return loaded


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
