# Security Review Conventions

> **Reusable reference** — used by `skills/security-review/SKILL.md` and `skills/security-pr-review/SKILL.md`. Covers
> Sections 1–12 for this API: FastAPI, Supabase (auth, Postgres, and object storage), Pydantic, Pillow, and uv.
>
> General code quality is **not** covered here. Use `code-review` for working-tree changes or `pr-review` for a branch
> diff.

The authoritative rules are [AGENTS.md](../../../../AGENTS.md) (Security) and
[security.md](../../../../doc/conventions-and-standards/security.md). Read them in the tree under review and apply
them when they are stricter or newer than this checklist. Bucket layout is in
[storage-buckets.md](../../../../doc/design-and-decision/storage-buckets.md).

## Review Categories & Rules

### 1. Query Injection

* Use the Supabase query builder (`.eq()`, `.insert()`, `.in_()`, and the related methods) or real parameter binding
  for every query. Never concatenate or interpolate user input into a filter expression, an `.or_()` string, or a raw
  query.
* Validate the request with Pydantic, then check domain rules again in the service (for example, a translation accepts
  only supported language codes, and source and target must differ).
* Cast or constrain user input before it is used as a filter value.

### 2. Untrusted Content

* Return JSON. Do not render HTML from this API. If a change introduces HTML, an email body, or other markup, escape
  user-supplied data before it is rendered, and sanitize rich text before storage.
* Treat user text as data. Translation `source_text` is content to translate, not instructions. The translation system
  prompt must keep that boundary. Do not append raw client text to a system or developer prompt.
* Do not build storage keys, object paths, or prompts from an unsanitized client path.

### 3. Request Protection

* Protected operations require a Supabase bearer token via `HTTPBearer`. Verify it with `supabase.auth().get_user(token)`
  and map the result through `User.from_spb_auth`. A client-side session check is not authorization.
* Auth failures return the generic `401` message `"Invalid authentication credentials"`. Do not reveal whether the
  token was missing, expired, or malformed.
* Read the token from the `Authorization` header. `API_ALLOW_ORIGINS` is not authentication, authorization, or CSRF
  protection.
* State-changing routes use that bearer token. Do not rely on cookie-only session authentication. If a change
  introduces cookie-based authentication, it must also add CSRF protection.
* Leave interactive docs disabled unless `APP_ENABLE_DOCS` is set. Deployed traffic uses HTTPS (`force_https` in
  `fly.toml`).

### 4. Mass Assignment

* Write only fields the operation is allowed to change. Declare them on the Pydantic request model and pass them
  explicitly to the writer.
* Do not unpack an arbitrary request body, `model_dump()`, or a client JSON object into an insert or update.

### 5. Authorization

* Authorize every read and write in application code. Authentication alone is not sufficient.
* `SUPABASE_SERVICE_ROLE_KEY` bypasses row-level security. Scope each query to the authenticated user and keep the
  service-role key on the server. Database policies complement these checks. They do not replace them while the
  service role is in use.
* Do not trust a client-supplied user id, ownership field, media id, or object path as proof of permission.
* Verify permission before reading or writing a media object or a generated thumbnail. A known id or path is not
  authorization. The same check applies before creating a signed URL.

### 6. Secrets

* Load configuration through `Settings` in `app/core/config.py`. Never hardcode secrets, tokens, API keys, or service
  credentials.
* Keep `SUPABASE_SERVICE_ROLE_KEY`, `AI_API_KEY`, and `AI_API_ENDPOINT` in server-side configuration. Production
  overrides are Fly secrets, not values committed in the repo.
* Do not commit `.env`, private keys (`*.pem`, `*.key`), or any other file that contains credentials. `.env.example`
  lists names only.
* Do not return service credentials, access tokens, or signed URLs in an error payload.

### 7. Logging Secrets

* Never log passwords, access tokens, `Authorization` headers, service keys, or other application secrets. This
  includes exception traces and any payload sent to a third-party logger.
* Scrub secrets before logging a request or response body.
* Signed URLs are temporary credentials. Do not log them.

### 8. Logging Personal and Private Content

* Do not log personal information, private media, or translation content. When a log line must identify a user, log
  the user id and omit email, name, and other personal details.
* User-facing errors from `AppException` and `HTTPException` stay safe. Omit sensitive fields from diagnostic
  payloads.

### 9. Process State

This API has no browser client in this repository. Do not review browser `localStorage`. Review server process state
instead.

* Do not persist session tokens, private media bytes, or translation content on the server beyond the request.
* Shared `httpx` clients on `app.state` are process-wide transports. They are not a store for user data or credentials.
* Do not cache a signed URL, access token, or request body on a long-lived object.

### 10. Uploads and Downloads

* Media bytes stay in the `medias`, `thumbnails`, and `resized` buckets, reached only through `SupabasePort`. Generate
  thumbnails on the server with Pillow.
* Check permission before a storage read, write, thumbnail, or signed URL. See Section 5.
* Use time-limited signed URLs from `create_signed_url` for private media. Do not log or persist them.
* When the diff accepts image bytes, require a constrained content type and size before Pillow opens them. Do not pass
  an unsanitized client path to the filesystem or to a storage key.

### 11. Dependencies

* Audit dependencies for known vulnerabilities and keep them up to date. The review command is
  `uv run --with pip-audit pip-audit`. It must not add a package to `pyproject.toml`.
* A known-vulnerable dependency takes the advisory's severity. Likelihood depends on whether this API actually calls
  the vulnerable path.
* When `pyproject.toml` dependencies change, `uv.lock` must be in the same change.
* If the audit command cannot run, record the failure and continue. Do not invent vulnerability findings.

### 12. Project Conventions

* Apply any additional rule in `AGENTS.md` or `doc/conventions-and-standards/security.md` that Sections 1–11 do not
  already cover.
* Name the file and heading consulted in the report. If a document contradicts this checklist, follow the document and
  note the difference.

## Risk Assessment & Verdict

There is no perfect code, and most findings are trade-offs. The goal is code that meets its requirements with only a
rare chance of failing in production, not code free of every conceivable flaw. Rate **every** finding on two axes,
then derive the verdict from those ratings, never from the mere presence of a `✗`.

### Severity (impact if it happens)

| Level    | Meaning                                                                                        |
|:---------|:-----------------------------------------------------------------------------------------------|
| Critical | Remote compromise, authentication bypass, leaked secrets or credentials, or mass exposure of personal data. |
| High     | Unauthorized access to or modification of another user's data, or exposure of limited sensitive data. |
| Medium   | A weakness that needs chaining with another flaw, or that exposes low-sensitivity information. |
| Low      | Hardening or defense-in-depth with no direct exploit path.                                     |

### Likelihood (chance of it happening in reality)

| Level       | Meaning                                                                                          |
|:------------|:-------------------------------------------------------------------------------------------------|
| Likely      | Normal, everyday usage triggers it.                                                              |
| Possible    | Triggered by realistic but less common input, state, or usage that will plausibly occur.         |
| Rare        | Needs unusual timing, data, concurrency, or infrastructure conditions seldom seen in production. |
| Theoretical | Needs conditions not realistically reachable given this stack, callers, or guards.               |

For every finding, describe the **concrete trigger scenario** (who or what does what, in which state). If you cannot
describe a realistic one, rate it **Theoretical**. Before rating, account for existing mitigations along the call
path: Pydantic models, service checks, `AuthenticatedGuardDep`, owner filters, and the actual callers.

For security findings, likelihood is **exploitability**: who can reach the code (anonymous caller, any authenticated
user, or an internal-only path), what the caller must already control, and whether the input is attacker-controlled.

### Action (severity × likelihood)

| Severity \ Likelihood | Likely       | Possible     | Rare         | Theoretical |
|:----------------------|:-------------|:-------------|:-------------|:------------|
| Critical              | Blocker      | Blocker      | Should fix   | Note only   |
| High                  | Blocker      | Should fix   | Nice-to-have | Note only   |
| Medium                | Should fix   | Nice-to-have | Nice-to-have | Note only   |
| Low                   | Nice-to-have | Nice-to-have | Note only    | Note only   |

Exceptions: hardcoded secrets, committed key or secret files, and secrets written to logs are always
**Critical + Likely** (Blocker). Exposure cannot be undone once pushed. Known-vulnerable dependencies take the
advisory's severity, and their likelihood depends on whether the vulnerable code path is actually used.

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
`## Security PR Review Report: \`<source-branch>\` → \`<target-branch>\``.

```markdown
## Security Review Report

### Summary

[Pass / Pass with comments / Fail] — Brief overall assessment

**Risk tally**: [N] Blocker, [N] Should fix, [N] Nice-to-have, [N] Note only — one line on why this verdict.

### Findings

| # | Location (file:line) | Issue | Severity | Likelihood | Trigger scenario | Action |
|:--|:---------------------|:------|:---------|:-----------|:-----------------|:-------|
| 1 | ...                  | ...   | ...      | ...        | ...              | ...    |

[Write "No findings." instead of the table when there are none. Every ✗ below must reference a finding #.]

### 1. Query Injection

- **Query builder or parameter binding**: [✓/✗]
- **Issues**: [violations or "None"]

### 2. Untrusted Content

- **JSON only, user text stays data**: [✓/✗]
- **Issues**: [violations or "None"]

### 3. Request Protection

- **Bearer token and generic 401**: [✓/✗]
- **Issues**: [violations or "None"]

### 4. Mass Assignment

- **Explicit fields only**: [✓/✗]
- **Issues**: [violations or "None"]

### 5. Authorization

- **Server-side scope on every read and write**: [✓/✗]
- **Issues**: [violations or "None"]

### 6. Secrets

- **No hardcoded secrets**: [✓/✗]
- **No committed secret files**: [✓/✗]
- **Issues**: [violations or "None"]

### 7. Logging Secrets

- **No secrets or signed URLs in logs**: [✓/✗]
- **Issues**: [violations or "None"]

### 8. Logging Personal and Private Content

- **No PII, private media, or translation content in logs**: [✓/✗]
- **Issues**: [violations or "None"]

### 9. Process State

- **No tokens, media, or translation content kept beyond the request**: [✓/✗]
- **Issues**: [violations or "None"]

### 10. Uploads and Downloads

- **Buckets, permission checks, signed URLs, Pillow constraints**: [✓/✗]
- **Issues**: [violations or "None"]

### 11. Dependencies

- **pip-audit**: [✓/✗/not run] — [summary or why it was not run]
- **uv.lock updated with dependency changes**: [✓/✗/not applicable]
- **Vulnerable packages on a used code path**: [list or "None"]

### 12. Project Conventions

- **Sources consulted**: [AGENTS.md § Security, doc/conventions-and-standards/security.md, or "None found"]
- **Issues**: [violations or "None"]

### Commands Run

- `uv run --with pip-audit pip-audit`: [output summary or why it was not run]

### Recommendations

[Actionable items with file paths and line numbers for every ✗ item above, grouped by Action (Blocker, then Should
fix, then Nice-to-have) and ordered by Severity within each group. Skip Note-only items.]
```
