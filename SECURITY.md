# Security policy

## Supported versions

Security fixes are applied on the latest released `pipeline-kit` version on the
default branch. Older tags may not receive backports.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Email the maintainers at the contact listed on the GitHub organization, or use
GitHub's private vulnerability reporting for this repository if it is enabled.

Include:

- A description of the issue and its impact
- Steps to reproduce or a proof of concept
- Affected versions or commit hashes if known

We will acknowledge the report and work on a fix. Please give us reasonable time
before public disclosure.

## Secrets and keys

- License **issue and validation** live in the private `pipeline-kit-license`
  package. The Ed25519 **public** key ships only with that package.
- The license **signing** private key must never appear in any repository, CI
  logs, issues, or pull requests.
- Portal ingest keys, customer license tokens, and deployment secrets belong in
  private systems only.

## Scope notes

This project installs workflow packs and optional tooling into developer
environments. Treat untrusted project content carefully. Report issues that
could lead to unexpected code execution, credential leakage, or privilege
escalation when using the shipped CLI and hooks.
