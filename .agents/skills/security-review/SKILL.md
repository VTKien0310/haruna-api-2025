---
name: security-review
description: >-
  Review uncommitted working-tree changes for query injection, untrusted
  content, bearer-token request protection, mass assignment, authorization,
  secrets, unsafe logging, process state, uploads and signed URLs, and
  vulnerable dependencies. Use when the user asks for a security review,
  security audit, or vulnerability check of current changes. Do not use for
  general code quality or a branch diff.
metadata:
  usage: "@security-review"
  example: "@security-review current code changes"
  conventions: "@ref ./references/REFERENCE.md"
compatibility: >-
  Requires git and uv. The dependency audit runs
  `uv run --with pip-audit pip-audit` and does not add a project dependency.
allowed-tools: Bash(git:*) Bash(uv:*) Read Grep
---

## What I Do

Perform a structured, security-only review of the current working tree and output a detailed report with a
risk-weighted verdict and status per security category. All review rules and the output report template are defined in
[REFERENCE.md](./references/REFERENCE.md).

Rate every finding by **severity** and **likelihood of occurring in reality**, and derive the final verdict
(Pass / Pass with comments / Fail) from those ratings as defined in **Risk Assessment & Verdict** in
[REFERENCE.md](./references/REFERENCE.md). Rare or theoretical issues must not fail otherwise working code. Do not chase
perfection or invent findings to appear useful.

Review local changes in the current checkout. Do not create, switch to, or clean up a separate `git worktree`. The
purpose is to inspect the exact uncommitted changes before they are pushed.

This skill is security only. For logic, formatting, naming, architecture, and other code-quality concerns, use
`code-review`.

## When to Use Me

Trigger when the user says any of:

* "security review", "review security", "security audit"
* "check for vulnerabilities", "check for security issues"
* "is this code secure", "audit this code for security"

Do not trigger for a general code review (use `code-review`), a security review of a branch diff (use
`security-pr-review`), general coding assistance, writing new code, or explaining concepts.

## My Procedures

### Step 1: Gather Information

Stay in the current repository checkout. Do not run `git checkout`, `git switch`, or `git worktree`.

Run:

```bash
git status
git diff
git diff --cached
```

Identify every modified file before proceeding. Read untracked files listed by `git status`. Include staged changes
from `git diff --cached`.

### Step 2: Read Project Security Rules

Read these from the current checkout and layer them on the checklist. The documents win when they are stricter or
newer than [REFERENCE.md](./references/REFERENCE.md):

* [AGENTS.md](../../../AGENTS.md) — Security
* [doc/conventions-and-standards/security.md](../../../doc/conventions-and-standards/security.md)

See **Section 12 (Project Conventions)** in [REFERENCE.md](./references/REFERENCE.md).

### Step 3: Run the Dependency Audit

From the repository root, without adding a dependency to the project:

```bash
uv run --with pip-audit pip-audit
```

If `pyproject.toml` dependencies changed, confirm `uv.lock` is part of the change. If the audit command cannot run,
record that and continue the review. Refer to **Section 11 (Dependencies)** in
[REFERENCE.md](./references/REFERENCE.md).

### Step 4: Review Against the Security Checklist

Load and apply [REFERENCE.md](./references/REFERENCE.md) — Sections 1 through 12 — against the diff from Step 1, layered
with anything found in Step 2.

### Step 5: Output Report

Use the **Output Report Template** at the bottom of [REFERENCE.md](./references/REFERENCE.md).
