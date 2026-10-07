# Security policy

## Supported versions

Security fixes are applied on the latest released `pipeline-kit` version on the
default branch. Older tags may not receive backports.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

**Preferred:** use [GitHub private vulnerability reporting](https://github.com/digitalneedstech/ai-sdlc-workflow-harness-manager/security/advisories/new) for this repository (enable “Private vulnerability reporting” in repo settings if it is not on yet).

If that is unavailable, email the maintainers via the contact on the
[digitalneedstech](https://github.com/digitalneedstech) GitHub organization profile.

Include:

- A description of the issue and its impact
- Steps to reproduce or a proof of concept
- Affected versions or commit hashes if known

We will acknowledge the report and work on a fix. Please give us reasonable time
before public disclosure.

## Secrets and keys

- License **issue and validation** live in the private `pipeline-kit-license`
  package (not this repository). Paying customers receive an **installable**
  package/wheel from the vendor — not the signing private key, and not
  unrestricted source access by default.
- The Ed25519 **public** key ships only with that private package.
- The license **signing** private key must never appear in any repository, CI
  logs, issues, or pull requests.
- Portal ingest keys, customer license tokens, and deployment secrets belong in
  private systems only.

## Scope notes

This project installs workflow packs and optional tooling into developer
environments. Treat untrusted project content carefully. Report issues that
could lead to unexpected code execution, credential leakage, or privilege
escalation when using the shipped CLI and hooks.
