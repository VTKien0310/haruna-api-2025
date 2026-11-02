---
name: pr-review
description: >-
  Review the three-dot diff between two branches for formatting, naming, HTTP
  API conventions, feature architecture, git conventions, code smells, logic,
  configuration, and application tests. Use when the user wants a pull-request
  review, a branch comparison, or a review before merging. Do not use for
  uncommitted working-tree changes or a security-only review.
metadata:
  usage: "@pr-review <source-branch> <target-branch>"
  example: "@pr-review p1/feat/#3-authentication develop"
  conventions: "@ref ../code-review/references/REFERENCE.md"
compatibility: >-
  Requires git and uv. Formatting checks use `uv run ruff format --check`
  and `uv run ruff check` on the Python files in the diff. Do not format or
  rewrite files during a review.
allowed-tools: Bash(git:*) Bash(uv:*) Read Grep
---

## What I Do

Perform a structured code review of the diff between two branches and output a detailed report with a risk-weighted
verdict and status per category. All review rules and the output report template are defined in
[REFERENCE.md](../code-review/references/REFERENCE.md).

Rate every finding by **severity** and **likelihood of occurring in reality**, and derive the final verdict
(Pass / Pass with comments / Fail) from those ratings as defined in **Risk Assessment & Verdict** in
[REFERENCE.md](../code-review/references/REFERENCE.md). Rare or theoretical issues must not fail otherwise working code.
Do not chase perfection or invent findings to appear useful.

Always fetch the latest remote changes before reviewing, then use a dedicated `git worktree` for each pull-request
review. This keeps the active working copy free and lets concurrent reviews avoid checking out over each other.

## When to Use Me

Trigger when the user says any of:

* "review PR", "PR review", "review pull request"
* "review diff between branches", "compare branches"
* "review `<branch>` against `<branch>`", "review `<branch>` to `<branch>`"
* "review `<branch>` before merging"

Do not trigger for general coding assistance, writing new code, explaining concepts, or reviewing uncommitted
working-tree changes (use `code-review` for that).

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

Create a detached worktree for the source ref before gathering the diff or running checks. Build the directory name
from the source branch by replacing `/` and any character other than letters, numbers, `.`, and `-` with `-`.

```bash
git worktree list
git worktree add --detach ../haruna-api-2025-pr-review-<safe-source-branch> <review-source-ref>
cd ../haruna-api-2025-pr-review-<safe-source-branch>
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

### Step 5: Run Code Quality Checks

Check only the Python files in the diff. Do not run `ruff format` without `--check`, and do not apply fixes. If the
diff contains no Python files, skip Ruff and mark formatting as not applicable.

```bash
mapfile -t py_files < <(git diff <review-target-ref>...<review-source-ref> --name-only | grep '\.py$' || true)
if ((${#py_files[@]})); then
  uv run ruff format --check "${py_files[@]}"
  uv run ruff check "${py_files[@]}"
fi
```

Refer to **Section 1 (Code Formatting)** in [REFERENCE.md](../code-review/references/REFERENCE.md).

Run `uv run pytest` only when the user explicitly asks. Otherwise review test files in the diff against **Section 10
(Application Tests)**.

### Step 6: Review Against Conventions and Output the Report

Load and apply all rules from [REFERENCE.md](../code-review/references/REFERENCE.md) — Sections 1 through 10 — against
the diff from Step 4. For a security-only review of this branch diff, use `security-pr-review` instead.

Use the **Output Report Template** at the bottom of [REFERENCE.md](../code-review/references/REFERENCE.md), with the
heading:

```
## PR Review Report: `<source-branch>` → `<target-branch>`
```

For **Section 6 (Git Conventions)**, verify the source branch name against **§2 Branch name** in
[git.md](../../../doc/conventions-and-standards/git.md) in addition to the commit messages.

### Step 7: Clean Up the Review Worktree

After the report is ready, and before the final response, return to the original repository and remove the review
worktree:

```bash
git worktree remove ../haruna-api-2025-pr-review-<safe-source-branch>
```

If cleanup fails because files changed during checks, report the worktree path and the cleanup error. Do not
force-remove it.
