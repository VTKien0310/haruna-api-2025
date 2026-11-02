# Code Review Conventions

> **Reusable reference** — used by `skills/code-review/SKILL.md` and `skills/pr-review/SKILL.md`. Covers Sections 1–10.
>
> Security (query injection, authorization, secrets, unsafe logging, uploads, vulnerable dependencies, and the rest of
> that checklist) is **not** covered here. Use `security-review` for working-tree changes or `security-pr-review` for a
> branch diff.

Standards live in [coding.md](../../../../doc/conventions-and-standards/coding.md),
[restful-api.md](../../../../doc/conventions-and-standards/restful-api.md),
[git.md](../../../../doc/conventions-and-standards/git.md), and
[application-tests.md](../../../../doc/conventions-and-standards/application-tests.md). Apply those documents if they
are stricter or newer than this checklist.

## Review Categories & Rules

### 1. Code Formatting

* Python changes must pass `uv run ruff format --check` and `uv run ruff check` with no issues.
* Style is PEP 8. Ruff is the formatter and linter. Strings use `"`.
* Do **not** auto-fix. Do not run `ruff format` without `--check`.
* On a working-tree review, Ruff failures outside the changed files are pre-existing. List them separately. They are
  not findings against the change.
* On a branch review, check only the Python files in the three-dot diff. If none changed, mark this section not
  applicable.
* Run `uv run pytest` only when the user explicitly asks.

### 2. Naming Conventions

* Modules, functions, variables, and methods use `snake_case`.
* Classes use `PascalCase`.
* Settings fields that mirror environment variables use `SCREAMING_SNAKE_CASE` (for example `SUPABASE_URL`,
  `AI_API_KEY` in `app/core/config.py`).
* Files are named for their role: `*_service.py`, `*_reader.py`, `*_writer.py`, `*_request.py`, `*_entity.py`,
  `*_guard.py`, `*_router.py`.
* Prefer a long, clear name over a short, ambiguous one.

### 3. Code Style

* Use strong typing on signatures and attributes. Avoid `Any` unless a comment states the reason. Prefer `T | None`.
* Prefix private instance attributes and methods with `__` (for example `self.__supabase`, `__create_thumbnail`).
* Prefix module-private functions with `_` (for example `_get_user_from_supabase_token`).
* Prefer a conditional expression for short, simple choices, and a guard clause over deeply nested `if` blocks.
* Match the surrounding code. Comment only when the comment adds information the code does not. Leave no dead code,
  commented-out blocks, or placeholders.

### 4. HTTP API

* Query strings follow the [JSON API specification](https://jsonapi.org/). The response envelope is the project
  envelope, not a raw JSON API document.
* Response fields and request parameters use `snake_case` (for example `translated_text`, `thumbnail_signed_url`).
* Routes are mounted under `settings.API_PREFIX` (`/api`). Path segments are lowercase. A multi-word segment uses `-`.
  Path parameters use `snake_case` (for example `/medias/{media_id}/thumbnails`, `/translation/translate`).
* One route performs one action.
* GET must not modify data and must not take a request body. Use a query string or a path parameter.
* Routers return the inner value. They do not wrap `{"ok": true, "content": ...}` themselves. `_WrapResponseMiddleware`
  wraps success. Failure is `{"ok": false, "content": {"error": ...}}` from `AppException` or `HTTPException`.

### 5. Architecture

Keep HTTP, feature, port, and core layers separate:

* `app/http/` — thin routers. Parse the request, delegate, and return a plain value. Register each `APIRouter` in
  `router_registry` (`app/http/__init__.py`). `bootstrap_application` mounts them under `settings.API_PREFIX`.
* `app/features/<feature>/` — domain logic, one package per feature (`auth`, `media`, `translation`, `attendance`,
  `pto`, `profile`), using `data/`, `entities/`, `guards/`, `requests/`, and `services/` as needed.
* `app/ports/` — adapters for external services (`SupabasePort`, `AiApiPort`).
* `app/core/` — settings, bootstrap, `AppException`, response wrapping, and shared HTTP clients.

Implementation rules:

* Services, readers, and writers are classes with `handle()`. Inject dependencies in `__init__` and store them on `__`
  attributes. Export `*Dep = Annotated[T, Depends()]`. Readers may return `Model | None`. Writers perform the insert,
  update, or delete. Example: `FindMediaByIdReader`.
* Guards are private FastAPI dependencies. Export `AuthenticatedGuardDep` and `CurrentAuthenticatedUserDep`. Protected
  routers set `dependencies=[AuthenticatedGuardDep]`.
* Request bodies are Pydantic `BaseModel`s with `Field` constraints, in the feature's `requests/`.
* Domain models that do not map one-to-one onto a request body are `@dataclass`es in `entities/`, with a
  `@classmethod` factory such as `from_spb_data` or `from_spb_auth`. Keep related enums beside the model.
* Re-export public names from each package `__init__.py` (`from .module import Name as Name`). Import from the package,
  not from a deep module path.
* Domain failures raise `AppException(status_code, code, message)`. Use `HTTPException` for standard protocol errors
  such as authentication failure.
* Do not put business logic in routers. Do not add a dependency without a clear reason. Do not introduce a second
  persistence style for Supabase access; go through `SupabasePort`.

### 6. Git Conventions

Follow [git.md](../../../../doc/conventions-and-standards/git.md).

* **Branch name** (§2): `{phase}/{group}/#{issue-id}-{name}`. Phase is the project phase (`p1`, `p2.5`). Group is one
  of `feat`, `fix`, `hotfix`, `ref`, `test`, `conf`, `chore`. The issue id may be omitted when there is no issue.
  Spaces in the name are `-`. Example: `p1/feat/#3-authentication`. A branch review checks the source branch name.
  Phase integration branches such as `p1/develop`, and the long-lived branches `master`, `develop`, `testing`,
  `staging`, and `production`, are bases, not feature-branch names.
* **Commit message** (§4):

  ```
  [type]: [Short summary in sentence case]

  - [What changed, with the module or file when it helps.]
  ```

  Types: `feat`, `fix`, `hotfix`, `ref`, `test`, `conf`, `chore`, `doc`. The subject is one sentence in sentence
  case. Bullets describe the change. Do not mix unrelated work in one commit.

Pull requests should stay small. When a change needs setup (a new dependency, master data, or a new environment
name), the review notes that the pull request must say so. Do not open or edit the pull request from this skill.

### 7. Code Smell

* **Long methods**: Flag a method or function whose pure logic exceeds about 30 lines, excluding blank lines and
  comments.
* **Deep nesting**: Flag conditionals or loops nested deeper than 3 levels. Prefer an early return or an extracted
  function.
* **Dead code**: Flag unreachable branches, unused variables, unused imports, and methods the diff never calls.
* **Magic values**: Flag unexplained numeric or string literals that should be named constants.
* **Too many parameters**: Flag a method with more than 4 business parameters. Injected constructor dependencies do
  not count toward that limit. Suggest a value object when the business parameters belong together.
* **Duplicated blocks**: Flag copy-pasted logic that appears more than once and should be extracted.
* **God objects**: Flag a class or method that handles unrelated responsibilities.

### 8. Logic Issues

* **Conflicting conditions**: Flag branches whose conditions contradict each other or cannot both be reached.
* **Unreachable code**: Flag a condition or branch the surrounding types, guards, or callers cannot satisfy.
* **Complex boolean logic**: Flag double negatives, chains of `and` / `or` beyond 2–3 operands, and nested conditional
  expressions. Suggest a named boolean.
* **Misleading names**: Flag a variable or method whose name does not match what it returns or does.
* **Inconsistent return patterns**: Flag a method that mixes early returns and fall-through so the result is unclear.
* **Logic vs. comments**: Flag logic that contradicts its own comment or docstring.

### 9. Configuration

* Load configuration from environment variables through `Settings` in `app/core/config.py`. Do not call `os.getenv` or
  read `os.environ` in feature, HTTP, or port code, other than the existing environment-file switch inside
  `app/core/config.py`.
* Do not hardcode a secret, token, endpoint, or other value when a settings field already exists.
* Register routers only from `router_registry` and mount them only from `bootstrap_application`. Do not attach routers
  from request-handling code.
* Shared `httpx` clients on `app.state` are process-wide transports. Do not store user data or credentials on them.

### 10. Application Tests

Review tests that are part of the change. Do not start the suite unless the user asked.

* Behavior changes belong with tests under `tests/`, mirroring the application (`tests/features/`, `tests/http/`,
  `tests/ports/`, `tests/architecture/`). A missing test is a finding. Rate it with the risk matrix. It is not an
  automatic failure.
* Name files `test_*.py`. Assert observable results: returned entities, row counts, status codes, and the wrapped
  `{"ok": ...}` body. Do not test private methods.
* Tests run in memory. They must not read an environment file, use a real credential, construct the real Supabase
  client, open an outbound socket, or use a filesystem database. Auth, storage, and AI responses stay on the in-memory
  fakes.
* Pass `supabase` into a reader, writer, or service constructor. HTTP tests use the `client` fixture. Build rows with
  the `insert_*` helpers. Register a bearer token with `supabase.auth().register(token)` before a protected request.
* A missing test for a pure formatting or comment change is not a finding.

## Risk Assessment & Verdict

There is no perfect code, and most findings are trade-offs. The goal is code that meets its requirements with only a
rare chance of failing in production, not code free of every conceivable flaw. Rate **every** finding on two axes,
then derive the verdict from those ratings, never from the mere presence of a `✗`.

### Severity (impact if it happens)

| Level    | Meaning                                                                                        |
|:---------|:-----------------------------------------------------------------------------------------------|
| Critical | Data loss or corruption, security breach, or the main requirement of the change does not work. |
| High     | A requirement or important flow is broken for some users or cases; wrong data is returned or persisted. |
| Medium   | Degraded behavior with a workaround, poor error handling, or a notable maintainability cost.   |
| Low      | Style, naming, formatting, readability, or a minor convention deviation with no behavioral impact. |

### Likelihood (chance of it happening in reality)

| Level       | Meaning                                                                                          |
|:------------|:-------------------------------------------------------------------------------------------------|
| Likely      | Normal, everyday usage triggers it.                                                              |
| Possible    | Triggered by realistic but less common input, state, or usage that will plausibly occur.         |
| Rare        | Needs unusual timing, data, concurrency, or infrastructure conditions seldom seen in production. |
| Theoretical | Needs conditions not realistically reachable given this stack, callers, or guards.               |

For every finding, describe the **concrete trigger scenario** (who or what does what, in which state). If you cannot
describe a realistic one, rate it **Theoretical**. Before rating, account for existing mitigations along the call
path: Pydantic validation, service checks, auth guards, Supabase filters scoped to the caller, and the actual callers.

### Action (severity × likelihood)

| Severity \ Likelihood | Likely       | Possible     | Rare         | Theoretical |
|:----------------------|:-------------|:-------------|:-------------|:------------|
| Critical              | Blocker      | Blocker      | Should fix   | Note only   |
| High                  | Blocker      | Should fix   | Nice-to-have | Note only   |
| Medium                | Should fix   | Nice-to-have | Nice-to-have | Note only   |
| Low                   | Nice-to-have | Nice-to-have | Note only    | Note only   |

Exception: a failing `ruff format --check` or `ruff check` on code in the change is always at least **Should fix**,
because the project requires a clean Ruff run. It is trivial to fix and is never, on its own, a reason for **Fail**.

### Verdict

* **Fail** — at least one **Blocker**.
* **Pass with comments** — no Blockers, but one or more **Should fix** items.
* **Pass** — only Nice-to-have or Note only items, or no findings at all.

### Reviewer discipline

* Do not invent or inflate findings to appear useful. "No issues found" is a valid outcome.
* Prefer working code with minor, unlikely defects over blocking delivery to chase perfection.
* Do not upgrade a rating because a fix is easy, and do not downgrade it because a fix is hard. Rate the risk itself.
* Keep Theoretical items brief, and omit them when they add no insight.

## Output Report Template

Return the full review as Markdown using this structure. For a branch review, replace the heading with
`## PR Review Report: \`<source-branch>\` → \`<target-branch>\``.

```markdown
## Code Review Report

### Summary

[Pass / Pass with comments / Fail] — Brief overall assessment

**Risk tally**: [N] Blocker, [N] Should fix, [N] Nice-to-have, [N] Note only — one line on why this verdict.

### Findings

| # | Location (file:line) | Issue | Severity | Likelihood | Trigger scenario | Action |
|:--|:---------------------|:------|:---------|:-----------|:-----------------|:-------|
| 1 | ...                  | ...   | ...      | ...        | ...              | ...    |

[Write "No findings." instead of the table when there are none. Every ✗ below must reference a finding #.]

### 1. Code Formatting

- **ruff format --check**: [✓/✗/not applicable] — Status
- **ruff check**: [✓/✗/not applicable] — Status
- **Issues**: [violations in the change, or "None"]
- **Pre-existing**: [failures outside the change, or "None"]

### 2. Naming Conventions

- **Modules, functions, variables, methods**: [✓/✗] — snake_case
- **Classes**: [✓/✗] — PascalCase
- **Settings fields**: [✓/✗] — SCREAMING_SNAKE_CASE
- **File roles**: [✓/✗] — role suffix

### 3. Code Style

- **Typing**: [✓/✗] — strong typing, no unjustified Any
- **Privacy prefixes**: [✓/✗] — `__` instance, `_` module

### 4. HTTP API

- **JSON API query strings**: [✓/✗] — query string format
- **Response envelope**: [✓/✗] — routers return the inner value
- **Field names**: [✓/✗] — snake_case
- **Routes**: [✓/✗] — `/api`, `-` segments, snake_case params, one action
- **GET safety**: [✓/✗] — no mutation and no request body

### 5. Architecture

- **Layering**: [✓/✗] — http / features / ports / core
- **Feature pattern**: [✓/✗] — handle(), Dep aliases, dataclasses, Pydantic requests, re-exports

### 6. Git Conventions

- **Branch naming**: [✓/✗/not applicable]
- **Commit message**: [✓/✗]

### 7. Code Smell

- **Long methods**: [✓/✗] — [count or "None"]
- **Deep nesting**: [✓/✗] — [count or "None"]
- **Dead code**: [✓/✗] — [instances or "None"]
- **Magic values**: [✓/✗] — [instances or "None"]
- **Too many parameters**: [✓/✗] — [instances or "None"]
- **Duplication**: [✓/✗] — [instances or "None"]

### 8. Logic Issues

- **Conflicting conditions**: [✓/✗] — [instances or "None"]
- **Unreachable code**: [✓/✗] — [instances or "None"]
- **Complex boolean logic**: [✓/✗] — [instances or "None"]
- **Misleading names**: [✓/✗] — [instances or "None"]
- **Inconsistent returns**: [✓/✗] — [instances or "None"]
- **Logic vs. comments**: [✓/✗] — [instances or "None"]

### 9. Configuration

- **Settings access**: [✓/✗] — [instances or "None"]
- **Router registration**: [✓/✗] — [instances or "None"]

### 10. Application Tests

- **Coverage of behavior changes**: [✓/✗/not applicable]
- **In-memory isolation**: [✓/✗/not applicable]
- **pytest**: [output summary, or "not run"]

### Commands Run

- `uv run ruff format --check`: [output summary]
- `uv run ruff check`: [output summary]
- `uv run pytest`: [output summary or "not run"]

### Recommendations

[Actionable items with file paths and line numbers for every ✗ item above, grouped by Action (Blocker, then Should
fix, then Nice-to-have) and ordered by Severity within each group. Skip Note-only items. For security findings, run
`security-review` on working-tree changes or `security-pr-review` on a branch diff.]
```
