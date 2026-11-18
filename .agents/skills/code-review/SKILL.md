---
name: code-review
description: >-
  Review uncommitted working-tree changes for formatting, naming, HTTP API
  conventions, feature architecture, git conventions, code smells, logic,
  configuration, and application tests. Use when the user asks for a code
  review, code analysis, or a check of current changes. Do not use for a
  security-only review, a branch or pull-request diff, or general coding.
metadata:
  usage: "@code-review"
  example: "@code-review current code changes"
  conventions: "@ref ./references/REFERENCE.md"
compatibility: >-
  Requires git and uv. Formatting checks use `uv run ruff format --check`
  and `uv run ruff check`. Do not format or rewrite files during a review.
allowed-tools: Bash(git:*) Bash(uv:*) Read Grep
---

## What I Do

Perform a structured code review of the current working tree against project conventions and output a detailed report
with a risk-weighted verdict and status per category. All review rules and the output report template are defined in
[REFERENCE.md](./references/REFERENCE.md).

Rate every finding by **severity** and **likelihood of occurring in reality**, and derive the final verdict
(Pass / Pass with comments / Fail) from those ratings as defined in **Risk Assessment & Verdict** in
[REFERENCE.md](./references/REFERENCE.md). Rare or theoretical issues must not fail otherwise working code. Do not chase
perfection or invent findings to appear useful.

This skill covers logic, formatting, naming, architecture, and application tests. For a security-only review (query
injection, authorization, secrets, unsafe logging, uploads, vulnerable dependencies, and the rest of that checklist),
use the `security-review` skill instead.

Review local changes in the current checkout. Do not create, switch to, or clean up a separate `git worktree`. The
purpose is to inspect the exact uncommitted changes before they are pushed.

## When to Use Me

Trigger when the user says any of:

* "review code", "review this", "code review"
* "analyze code", "analyze changes"
* "check code", "review changes"

Do not trigger for general coding assistance, writing new code, or explaining concepts. Do not trigger for a diff
between two branches; use `pr-review` for that.

## My procedures

### Step 1: Gather Information

Stay in the current repository checkout. Do not run `git checkout`, `git switch`, or `git worktree`.

Run:

```bash
git status
git diff
git diff --cached
```

Identify every modified file before proceeding. `git diff` omits staged and untracked files. Read untracked files listed
by `git status`, and include `git diff --cached` in the review.

### Step 2: Run Code Quality Checks

Check only. Do not run `ruff format` without `--check`, and do not apply fixes.

```bash
uv run ruff format --check
uv run ruff check
```

Refer to **Section 1 (Code Formatting)** in [REFERENCE.md](./references/REFERENCE.md). Failures in files the change does
not touch are pre-existing. Report them separately and do not treat them as findings against this change.

Run `uv run pytest` only when the user explicitly asks. Otherwise review test files in the diff against **Section 10
(Application Tests)**.

### Step 3: Review Against Conventions

Load and apply all rules from [REFERENCE.md](./references/REFERENCE.md) — Sections 1 through 10.

### Step 4: Output Report

Use the **Output Report Template** at the bottom of [REFERENCE.md](./references/REFERENCE.md).
