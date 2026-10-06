#!/usr/bin/env python3
"""Read-only Jira REST helper when intake.jira.connection is api.

Site URL and credentials stay in the environment — never in config.json:

  JIRA_BASE_URL     https://example.atlassian.net  (no trailing slash required)
  JIRA_EMAIL        Cloud basic-auth user (optional; omit for Bearer PAT)
  JIRA_API_TOKEN    Cloud API token, or PAT / JIRA_TOKEN

Usage (from the product repo root):

  python .pipeline/skills/jira-intake/scripts/jira_api.py issue get KEY
  python .pipeline/skills/jira-intake/scripts/jira_api.py search "parent = KEY ORDER BY rank ASC" [--max N]

Stdout is JSON. Writes are refused; set PIPELINE_ALLOW_JIRA=1 does not enable
them in this script (intake is read-only unless the skill says otherwise).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


USAGE = 64
AUTH = 73


def flatten_adf(node: Any) -> str:
    """Turn Atlassian Document Format (or a plain string) into readable text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(flatten_adf(item) for item in node)
    if not isinstance(node, dict):
        return str(node)
    ntype = node.get("type")
    content = flatten_adf(node.get("content"))
    text = node.get("text") or ""
    if ntype in {"paragraph", "heading", "blockquote", "listItem"}:
        return f"{content}{text}\n"
    if ntype in {"bulletList", "orderedList", "table", "tableRow"}:
        return f"{content}\n" if content else ""
    if ntype == "hardBreak":
        return "\n"
    return f"{text}{content}"


def issue_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Jira issue JSON body into the fields intake collects."""
    fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    rendered = raw.get("renderedFields") if isinstance(raw.get("renderedFields"), dict) else {}
    key = str(raw.get("key") or "")
    itype = fields.get("issuetype") if isinstance(fields.get("issuetype"), dict) else {}
    status = fields.get("status") if isinstance(fields.get("status"), dict) else {}
    priority = fields.get("priority") if isinstance(fields.get("priority"), dict) else {}
    reporter = fields.get("reporter") if isinstance(fields.get("reporter"), dict) else {}
    assignee = fields.get("assignee") if isinstance(fields.get("assignee"), dict) else {}
    parent = fields.get("parent") if isinstance(fields.get("parent"), dict) else {}
    description = rendered.get("description")
    if not isinstance(description, str) or not description.strip():
        description = flatten_adf(fields.get("description")).strip()
    labels = fields.get("labels") if isinstance(fields.get("labels"), list) else []
    components = []
    for item in fields.get("components") or []:
        if isinstance(item, dict) and item.get("name"):
            components.append(str(item["name"]))
    attachments = []
    for item in fields.get("attachment") or []:
        if isinstance(item, dict) and item.get("filename"):
            attachments.append(str(item["filename"]))
    links = []
    for item in fields.get("issuelinks") or []:
        if not isinstance(item, dict):
            continue
        other = item.get("outwardIssue") or item.get("inwardIssue") or {}
        if isinstance(other, dict) and other.get("key"):
            links.append(str(other["key"]))
    comments: list[dict[str, str]] = []
    comment_block = fields.get("comment")
    bodies = comment_block.get("comments") if isinstance(comment_block, dict) else []
    for item in bodies or []:
        if not isinstance(item, dict):
            continue
        body = item.get("body")
        comments.append({"body": flatten_adf(body).strip() if not isinstance(body, str) else body})
    return {
        "key": key,
        "issue_type": str(itype.get("name") or ""),
        "status": str(status.get("name") or ""),
        "priority": str(priority.get("name") or ""),
        "summary": str(fields.get("summary") or ""),
        "description": description if isinstance(description, str) else flatten_adf(description),
        "labels": [str(x) for x in labels],
        "components": components,
        "parent": str(parent.get("key") or ""),
        "reporter": str(reporter.get("displayName") or ""),
        "assignee": str(assignee.get("displayName") or ""),
        "linked_issues": links,
        "attachments": attachments,
        "comments": comments,
        "environment": flatten_adf(fields.get("environment")).strip()
        if not isinstance(fields.get("environment"), str)
        else str(fields.get("environment") or ""),
    }


def _base_url() -> str:
    raw = (os.environ.get("JIRA_BASE_URL") or "").strip().rstrip("/")
    if not raw:
        print("Set JIRA_BASE_URL (site only, no path). Do not put it in config.json.", file=sys.stderr)
        raise SystemExit(USAGE)
    if not raw.startswith("https://"):
        print("JIRA_BASE_URL must be https://…", file=sys.stderr)
        raise SystemExit(USAGE)
    return raw


def _headers() -> dict[str, str]:
    token = (os.environ.get("JIRA_API_TOKEN") or os.environ.get("JIRA_TOKEN") or "").strip()
    email = (os.environ.get("JIRA_EMAIL") or "").strip()
    if not token:
        print("Set JIRA_API_TOKEN (or JIRA_TOKEN). Do not put it in config.json.", file=sys.stderr)
        raise SystemExit(AUTH)
    headers = {"Accept": "application/json", "User-Agent": "pipeline-kit-jira-intake"}
    if email:
        blob = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {blob}"
    else:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=_headers(), method="GET")
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        print(f"Jira HTTP {exc.code} for {url}: {detail}", file=sys.stderr)
        raise SystemExit(AUTH if exc.code in {401, 403} else USAGE) from exc
    except urllib.error.URLError as exc:
        print(f"Jira unreachable: {exc.reason}", file=sys.stderr)
        raise SystemExit(USAGE) from exc
    data = json.loads(body)
    if not isinstance(data, dict):
        print("Jira returned a non-object JSON body.", file=sys.stderr)
        raise SystemExit(USAGE)
    return data


def cmd_issue_get(key: str) -> int:
    key = key.strip()
    if not key:
        print("issue get requires a key.", file=sys.stderr)
        return USAGE
    encoded = urllib.parse.quote(key, safe="")
    url = (
        f"{_base_url()}/rest/api/3/issue/{encoded}"
        "?fields=summary,issuetype,status,priority,description,labels,components,"
        "fixVersions,versions,environment,reporter,assignee,issuelinks,parent,"
        "attachment,comment"
        "&expand=renderedFields"
    )
    raw = _get(url)
    json.dump(issue_payload(raw), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_search(jql: str, limit: int) -> int:
    jql = jql.strip()
    if not jql:
        print("search requires JQL.", file=sys.stderr)
        return USAGE
    query = urllib.parse.urlencode({"jql": jql, "maxResults": max(1, limit), "fields": "summary,issuetype,status,description,parent"})
    url = f"{_base_url()}/rest/api/3/search?{query}"
    raw = _get(url)
    issues = raw.get("issues") if isinstance(raw.get("issues"), list) else []
    out = [issue_payload(item) for item in issues if isinstance(item, dict)]
    json.dump({"jql": jql, "issues": out}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jira_api.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    issue = sub.add_parser("issue")
    issue_sub = issue.add_subparsers(dest="issue_cmd", required=True)
    get_p = issue_sub.add_parser("get")
    get_p.add_argument("key")
    search_p = sub.add_parser("search")
    search_p.add_argument("jql")
    search_p.add_argument("--max", type=int, default=20)
    args = parser.parse_args(argv)
    if args.cmd == "issue" and args.issue_cmd == "get":
        return cmd_issue_get(args.key)
    if args.cmd == "search":
        return cmd_search(args.jql, args.max)
    return USAGE


if __name__ == "__main__":
    raise SystemExit(main())
