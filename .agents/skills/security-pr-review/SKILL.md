---
name: security-pr-review
description: >-
  Review the three-dot diff between two branches for query injection, untrusted
  content, bearer-token request protection, mass assignment, authorization,
  secrets, unsafe logging, process state, uploads and signed URLs, and
  vulnerable dependencies. Use when the user wants a security review of a pull
  request or a security comparison of two branches before merging. Do not use
  for general code quality or uncommitted working-tree changes.
metadata:
  usage: "@security-pr-review <source-branch> <target-branch>"
  example: "@security-pr-review p1/feat/#3-authentication develop"
  conventions: "@ref ../security-review/references/REFERENCE.md"
compatibility: >-
  Requires git and uv. The dependency audit runs
  `uv run --with pip-audit pip-audit` inside the review worktree and does not
  add a project dependency.
allowed-tools: Bash(git:*) Bash(uv:*) Read Grep
---

## What I Do

Perform a structured, security-only review of the diff between two branches and output a detailed report with a
risk-weighted verdict and status per security category. All review rules and the output report template are defined in
[REFERENCE.md](../security-review/references/REFERENCE.md).

Rate every finding by **severity** and **likelihood of occurring in reality**, and derive the final verdict
(Pass / Pass with comments / Fail) from those ratings as defined in **Risk Assessment & Verdict** in
[REFERENCE.md](../security-review/references/REFERENCE.md). Rare or theoretical issues must not fail otherwise working
code. Do not chase perfection or invent findings to appear useful.

Always fetch the latest remote changes before reviewing, then use a dedicated `git worktree` for each review. This
keeps the active working copy free and lets concurrent reviews avoid checking out over each other.

This skill is security only. For a general review of a branch diff, use `pr-review`. For a security-only review of
uncommitted working-tree changes, use `security-review`.

## When to Use Me

Trigger when the user says any of:

* "security review of this PR", "security PR review"
* "review `<branch>` against `<branch>` for security issues"
* "audit `<branch>` for security before merging"
* "compare branches for vulnerabilities"

Do not trigger for a general pull-request review (use `pr-review`), a security review of uncommitted changes (use
`security-review`), general coding assistance, writing new code, or explaining concepts.

## My Procedures

### Step 1: Parse Branch Arguments

Extract the **source branch** (feature or pull-request branch) and **target branch** (base branch, for example
`develop`) from the user's message.

If either branch is missing, ask the user:

> Which two branches should I compare? Provide: `<source-branch>` (the pull-request branch) and `<target-branch>` (the
> base branch).

Do not validate branch existence until after fetching in Step 2.

### Step 2: Fetch Latest Changes

Always fetch before validating branches, creating the review worktree, or gathering the diff:

```bash
git fetch --prune origin
```

After fetching, validate both branches exist locally or on `origin`:

```bash
git branch -a | grep "<source-branch>"
git branch -a | grep "<target-branch>"
```

Use the fetched remote refs when they exist:

* `<review-source-ref>` is `origin/<source-branch>` when that remote ref exists, otherwise `<source-branch>`.
* `<review-target-ref>` is `origin/<target-branch>` when that remote ref exists, otherwise `<target-branch>`.

### Step 3: Create an Isolated Review Worktree

Create a detached worktree for the source ref before gathering the diff or running checks. Use the
`security-pr-review` prefix so the path does not collide with a concurrent `pr-review` worktree for the same branch.
Build the directory name from the source branch by replacing `/` and any character other than letters, numbers, `.`,
and `-` with `-`.

```bash
git worktree list
git worktree add --detach ../haruna-api-2025-security-pr-review-<safe-source-branch> <review-source-ref>
cd ../haruna-api-2025-security-pr-review-<safe-source-branch>
```

If that path already exists, inspect `git worktree list`. Reuse it only when it already points at the same source ref.
Otherwise pick a unique suffix such as `-2`. Do not remove an existing worktree unless the user explicitly asks.

Run every remaining review command from inside the review worktree.

### Step 4: Gather Diff Information

Use the **three-dot diff** so the review shows only what the source branch adds since it diverged from the target:

```bash
git log <review-target-ref>..<review-source-ref> --oneline
git diff <review-target-ref>...<review-source-ref> --name-only
git diff <review-target-ref>...<review-source-ref>
```

Identify every modified file before proceeding.

### Step 5: Read Project Security Rules

Read these from **inside the review worktree**, because the branch under review may have changed them. Layer them on
the checklist. The documents win when they are stricter or newer than the reference:

* `AGENTS.md` — Security
* `doc/conventions-and-standards/security.md`

See **Section 12 (Project Conventions)** in [REFERENCE.md](../security-review/references/REFERENCE.md).

### Step 6: Run the Dependency Audit

From the review worktree, without adding a dependency to the project:

```bash
uv run --with pip-audit pip-audit
```

If the diff changes dependencies in `pyproject.toml`, confirm `uv.lock` is part of the diff. If the audit command
cannot run, record that and continue the review. Refer to **Section 11 (Dependencies)** in
[REFERENCE.md](../security-review/references/REFERENCE.md).

### Step 7: Review Against the Security Checklist and Output the Report

Load and apply [REFERENCE.md](../security-review/references/REFERENCE.md) — Sections 1 through 12 — against the diff
from Step 4, layered with anything found in Step 5.

Use the **Output Report Template** at the bottom of [REFERENCE.md](../security-review/references/REFERENCE.md), with
the heading:

```
## Security PR Review Report: `<source-branch>` → `<target-branch>`
```

### Step 8: Clean Up the Review Worktree

After the report is ready, and before the final response, return to the original repository and remove the review
worktree:

```bash
git worktree remove ../haruna-api-2025-security-pr-review-<safe-source-branch>
```

If cleanup fails because files changed during checks, report the worktree path and the cleanup error. Do not
force-remove it.
