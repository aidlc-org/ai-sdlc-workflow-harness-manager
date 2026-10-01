# Dependency declaration and code minimalism

| Attribute | Value |
|-----------|--------|
| Type | Wiki |
| Audience | Parent or specialist when INDEX triggers match |
| Adapt | Add a new page after retro. Do not store secrets or customer identifiers. |

- **Layer:** pipeline
- **Load when:** a dependency install was refused, or a feature's diff is much larger than the requirement warranted

## Symptom

`Blocked undeclared dependency: react-datepicker` on a legitimate task, or the
opposite: a one-line requirement arriving as a new package plus an eighty-line
wrapper.

## Root cause

The hooks enforce the ladder, but only the Architect can record the answer.
`before-shell.py` and `pre-write.py` read
`features/{slug}/state/architect-agent.json`, so a package nobody declared has
no record to match — regardless of how reasonable it is.

The older failure mode was the reverse: every install was refused and the only
escape was `PIPELINE_ALLOW_DEPS=1`, which left no record of *why* a library was
added.

## Do not

- Set `PIPELINE_ALLOW_DEPS=1` to get past a refusal. It is break-glass, and it
  records nothing.
- Add a package on micro, minor, or `jira-bug` class. Those take none.
- Write `why_nothing_existing_works` as a restatement of the feature. Name the
  rung that failed: what in the repo, the standard library, the platform, or the
  installed manifest was checked.
- Edit `package.json` by hand to dodge the shell gate. `pre-write.py` reads
  manifests too.
- Assume the gate is on. Without `FEATURE_SLUG` there is no declaration to find,
  so installs fall back to a blanket refusal and manifest edits are allowed.

## Convention

Ladder and class table in
`.pipeline/skills/feature-development/assets/minimalism-policy.md`.

| Class / workflow | new_dependencies |
|------------------|------------------|
| micro / minor / jira-bug | forbidden |
| feature (and jira-story / jira-epic at feature class) | allowed when declared |

Declare in both places, in the Architect step:

- `features/{slug}/state/architect-agent.json` → `context.new_dependencies`
  (`name`, `why_nothing_existing_works`) — this is what the hooks read
- `features/{slug}/HANDOFF-architect.md` → `**new_dependencies:**` line

A child slug inherits the parent's declaration. `npm install` with no package
argument is allowed — it restores what the manifest already pins. One-run escape
is `ALLOW_DEPENDENCY={name}`.

## Files

`.pipeline/skills/feature-development/assets/minimalism-policy.md`,
`.pipeline/hooks/before-shell.py`, `.pipeline/hooks/pre-write.py`,
`.pipeline/hooks/lib.py`, `.pipeline/config.json` (`code_minimalism`)

## Verify

- Architect's A4 blockers include the dependency declaration row.
- `echo '{"command":"npm i axios"}' | python .pipeline/hooks/before-shell.py`
  denies without a declaration and allows with one.
- A manifest edit adding an undeclared package is refused and the message names
  the package.
