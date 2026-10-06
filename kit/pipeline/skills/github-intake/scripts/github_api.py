#!/usr/bin/env python3
"""Read-only GitHub REST helper when intake.github.connection is api.

Token and optional Enterprise base stay in the environment — never in config.json:

  GH_TOKEN / GITHUB_TOKEN   fine-grained or classic PAT (repo scope for private)
  GITHUB_API_URL            https://api.github.com or GHES api URL (no trailing slash)
  GITHUB_REPO               owner/repo when the ask is only #123

Usage (from the product repo root):

  python .pipeline/skills/github-intake/scripts/github_api.py issue get owner/repo#123
  python .pipeline/skills/github-intake/scripts/github_api.py issue get 123 --repo owner/repo
  python .pipeline/skills/github-intake/scripts/github_api.py sub-issues owner/repo#123 [--max N]

Stdout is JSON. Writes are refused; PIPELINE_ALLOW_GITHUB=1 does not enable
them in this script (intake is read-only unless the skill says otherwise).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USAGE = 64
AUTH = 73

URL_RE = re.compile(
    r"^https?://(?:github\.com|www\.github\.com)/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)/?$",
    re.I,
)
OWNER_NUM_RE = re.compile(r"^([^/#\s]+)/([^/#\s]+)#(\d+)$")
NUM_RE = re.compile(r"^#?(\d+)$")


def parse_ref(raw: str, repo: str = "") -> tuple[str, str, str]:
    """Return (owner, name, number) from a URL, owner/repo#n, or #n + repo."""
    text = (raw or "").strip()
    match = URL_RE.match(text)
    if match:
        return match.group(1), match.group(2), match.group(3)
    match = OWNER_NUM_RE.match(text)
    if match:
        return match.group(1), match.group(2), match.group(3)
    match = NUM_RE.match(text)
    owner_repo = (repo or os.environ.get("GITHUB_REPO") or "").strip()
    if match and "/" in owner_repo:
        owner, name = owner_repo.split("/", 1)
        return owner, name, match.group(1)
    print(
        "Need owner/repo#N, a github.com issues/pull URL, or #N with --repo / GITHUB_REPO.",
        file=sys.stderr,
    )
    raise SystemExit(USAGE)


def classify_issue(raw: dict[str, Any], labels: list[str]) -> str:
    if raw.get("pull_request"):
        return "pull_request"
    itype = raw.get("type") if isinstance(raw.get("type"), dict) else {}
    name = str(itype.get("name") or "").strip()
    if name:
        return name
    lowered = {item.lower() for item in labels}
    if lowered & {"bug", "defect", "incident"}:
        return "bug"
    if lowered & {"epic"}:
        return "epic"
    return "issue"


def issue_payload(raw: dict[str, Any], owner: str, name: str) -> dict[str, Any]:
    """Normalize a GitHub issue or PR JSON body into the fields intake collects."""
    number = str(raw.get("number") or "")
    labels: list[str] = []
    for item in raw.get("labels") or []:
        if isinstance(item, dict) and item.get("name"):
            labels.append(str(item["name"]))
        elif isinstance(item, str):
            labels.append(item)
    user = raw.get("user") if isinstance(raw.get("user"), dict) else {}
    assignees: list[str] = []
    for item in raw.get("assignees") or []:
        if isinstance(item, dict) and item.get("login"):
            assignees.append(str(item["login"]))
    comments: list[dict[str, str]] = []
    for item in raw.get("comments") or []:
        if isinstance(item, dict) and item.get("body"):
            comments.append({"body": str(item["body"])})
    return {
        "key": f"{owner}/{name}#{number}",
        "number": number,
        "repo": f"{owner}/{name}",
        "url": str(raw.get("html_url") or ""),
        "issue_type": classify_issue(raw, labels),
        "status": str(raw.get("state") or ""),
        "priority": "",
        "summary": str(raw.get("title") or ""),
        "description": str(raw.get("body") or ""),
        "labels": labels,
        "components": [],
        "parent": "",
        "reporter": str(user.get("login") or ""),
        "assignee": assignees[0] if assignees else "",
        "linked_issues": [],
        "attachments": [],
        "comments": comments,
        "environment": "",
        "is_pull_request": bool(raw.get("pull_request")),
    }


def _base_url() -> str:
    raw = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").strip().rstrip("/")
    if not raw.startswith("https://"):
        print("GITHUB_API_URL must be https://…", file=sys.stderr)
        raise SystemExit(USAGE)
    return raw


def _headers() -> dict[str, str]:
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not token:
        print("Set GH_TOKEN or GITHUB_TOKEN. Do not put it in config.json.", file=sys.stderr)
        raise SystemExit(AUTH)
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "pipeline-kit-github-intake",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(url: str, *, allow_404: bool = False) -> dict[str, Any] | list[Any] | None:
    request = urllib.request.Request(url, headers=_headers(), method="GET")
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        if allow_404 and exc.code == 404:
            return None
        print(f"GitHub HTTP {exc.code} for {url}: {detail}", file=sys.stderr)
        raise SystemExit(AUTH if exc.code in {401, 403} else USAGE) from exc
    except urllib.error.URLError as exc:
        print(f"GitHub unreachable: {exc.reason}", file=sys.stderr)
        raise SystemExit(USAGE) from exc
    data = json.loads(body)
    if not isinstance(data, (dict, list)):
        print("GitHub returned unexpected JSON.", file=sys.stderr)
        raise SystemExit(USAGE)
    return data


def cmd_issue_get(ref: str, repo: str = "") -> int:
    owner, name, number = parse_ref(ref, repo)
    encoded_owner = urllib.parse.quote(owner, safe="")
    encoded_name = urllib.parse.quote(name, safe="")
    url = f"{_base_url()}/repos/{encoded_owner}/{encoded_name}/issues/{urllib.parse.quote(number, safe='')}"
    raw = _get(url)
    if not isinstance(raw, dict):
        print("GitHub returned a non-object issue body.", file=sys.stderr)
        return USAGE
    json.dump(issue_payload(raw, owner, name), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_sub_issues(ref: str, repo: str = "", limit: int = 20) -> int:
    owner, name, number = parse_ref(ref, repo)
    encoded_owner = urllib.parse.quote(owner, safe="")
    encoded_name = urllib.parse.quote(name, safe="")
    url = (
        f"{_base_url()}/repos/{encoded_owner}/{encoded_name}/issues/"
        f"{urllib.parse.quote(number, safe='')}/sub_issues"
    )
    raw = _get(url, allow_404=True)
    issues = raw if isinstance(raw, list) else []
    capped = [item for item in issues if isinstance(item, dict)][: max(1, limit)]
    out = [issue_payload(item, owner, name) for item in capped]
    json.dump({"parent": f"{owner}/{name}#{number}", "issues": out}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="github_api.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    issue = sub.add_parser("issue")
    issue_sub = issue.add_subparsers(dest="issue_cmd", required=True)
    get_p = issue_sub.add_parser("get")
    get_p.add_argument("ref")
    get_p.add_argument("--repo", default="")
    children = sub.add_parser("sub-issues")
    children.add_argument("ref")
    children.add_argument("--repo", default="")
    children.add_argument("--max", type=int, default=20)
    args = parser.parse_args(argv)
    if args.cmd == "issue" and args.issue_cmd == "get":
        return cmd_issue_get(args.ref, args.repo)
    if args.cmd == "sub-issues":
        return cmd_sub_issues(args.ref, args.repo, args.max)
    return USAGE


if __name__ == "__main__":
    raise SystemExit(main())
