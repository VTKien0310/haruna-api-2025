# **SECURITY**

- **Authentication**
    - Must require a Supabase Bearer token, via `HTTPBearer`, for protected operations. Verify it with
      `supabase.auth().get_user(token)` and map the result through `User.from_spb_auth`. Client-side session checks
      are not authorization
    - Must return the generic `401` message `"Invalid authentication credentials"` for auth failures, and must not
      reveal whether the token was missing, expired, or malformed
- **Authorization and data access**
    - Must authorize every read and write in application code. Authentication alone is not sufficient.
      `SUPABASE_SERVICE_ROLE_KEY` bypasses Row Level Security, so scope each query to the authenticated user, and
      keep the service-role key on the server. _Ex: `DeleteOldestTranslationHistoriesWriter` filters by `owner_id`_
    - Must not trust a client-supplied user id, ownership field, or object path as proof of permission
    - See the [Supabase RLS guide](https://supabase.com/docs/guides/database/postgres/row-level-security). Database
      policies complement these checks. They do not replace them while the service role is in use
- **Query injection**
    - Must use the Supabase query builder (`.eq()`, `.insert()`, `.in_()`, and related methods) or parameter binding
      for every query (Eloquent parameter binding). Never concatenate or interpolate raw user input into filter
      expressions or raw query strings
    - Should validate and cast user input types before using them in a query
    - Must validate request bodies with Pydantic, then check domain rules again in the service. _Ex: `TranslateService`
      accepts only supported language codes, and source and target must differ_
- **Mass assignment**
    - Must write only fields the operation is allowed to change (Eloquent `$fillable`). Declare them on the Pydantic
      request model and pass them explicitly to the writer. Do not unpack an arbitrary request body into an insert
      or update. _Ex: `CreateTranslationHistoryWriter` inserts named columns_
- **Untrusted content**
    - Must return JSON. Escape user-supplied data before it is rendered as HTML, and sanitize rich text before
      storage when that content will be rendered as HTML
    - Must treat user text as data. Translation `source_text` is content to translate, not instructions. The
      translation system prompt must keep that boundary
    - Must not build prompts or storage paths from unsanitized client paths
- **Uploads, previews, and downloads**
    - Must keep media bytes in the `medias`, `thumbnails`, and `resized` buckets, reached only through `SupabasePort`.
      Generate thumbnails on the server with Pillow
    - Must verify permission before reading or writing a media object or a generated thumbnail. A known media id or
      object path is not authorization
    - Must use time-limited signed URLs for private media (`create_signed_url`). They are temporary credentials:
      do not log them or persist them
- **Request protection**
    - Must read the Supabase token from the `Authorization` header (see Authentication). `API_ALLOW_ORIGINS` is not
      authentication, authorization, or CSRF protection
    - Must use that Bearer token for state-changing routes. Do not rely on cookie-only session authentication. If
      cookie-based authentication is introduced, add CSRF protection (Laravel `VerifyCsrfToken`)
    - Must leave interactive docs disabled unless `APP_ENABLE_DOCS` is set
    - Must use HTTPS for deployed traffic. `force_https` is set in `fly.toml`
- **Secrets and configuration**
    - Must load configuration from environment variables through `Settings` in `app/core/config.py`. Never hardcode
      secrets, tokens, or service credentials
    - Must not commit `.env` or any file that contains credentials. `.env.example` lists names only
    - Must keep `SUPABASE_SERVICE_ROLE_KEY` (see Authorization), `AI_API_KEY`, and `AI_API_ENDPOINT` in server-side
      configuration. Production overrides are set with Fly secrets
    - See the [Supabase API key guide](https://supabase.com/docs/guides/getting-started/api-keys)
- **Logging and error messages**
    - Must never log passwords, access tokens, authorization headers, service keys, or other application secrets.
      Scrub secrets and personal fields before logging a request or response payload
    - Must not log personal information, private media, or translation content. When a log line needs to identify a
      user, log the user id and omit email, name, and other personal details
    - Must return safe user-facing errors through `AppException` and `HTTPException`. Omit sensitive fields from
      diagnostic payloads
- **Process state and temporary credentials**
    - Must not persist session tokens, private media, or translation content on the server beyond the request.
      Signed URLs are covered under Uploads
    - Must treat the shared `httpx` clients on `app.state` as process-wide transports. They are not a store for
      user data or credentials
- **Dependency vulnerabilities**
    - Should regularly audit dependencies for known vulnerabilities and keep them up to date (`uv`, the equivalent
      of Composer)
    - Must commit `uv.lock` alongside dependency updates

Sensitive environment fields and files that must never be committed are listed above. These rules describe required
practices. They do not certify that deployed Supabase policies have been audited.
