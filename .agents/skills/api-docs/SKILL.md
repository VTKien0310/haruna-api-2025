---
name: api-docs
description: >-
  Add, update, or remove this project's FastAPI OpenAPI documentation whenever
  a route is added, removed, or its path, auth, request body, or response
  shape changes. Use when writing or editing path operations, response models,
  or the OpenAPI schema customizer, or when checking that a route change ships
  with docs. Swagger UI (`/docs`), ReDoc (`/redoc`), and `/openapi.json` are
  generated from the app. Do not use for publishing a hosted spec or for
  writing a separate OpenAPI or collection file.
metadata:
  usage: "@api-docs route-or-change"
  example: "@api-docs document the new PUT /api/pto/banks/{year} endpoint"
  conventions: "@ref ./references/REFERENCE.md"
compatibility: >-
  Requires uv. Schema checks run `create_app().openapi()` with
  `ENVIRONMENT=testing` and `APP_ENABLE_DOCS=true`.
allowed-tools: Bash(uv:*) Read Grep Glob Edit Write
---

## What I Do

Keep the OpenAPI schema FastAPI generates from this app in sync with the routes. Swagger UI (`/docs`), ReDoc
(`/redoc`), and `/openapi.json` all load that schema. They are served only when `APP_ENABLE_DOCS` is true.

Follow [REFERENCE.md](./references/REFERENCE.md). It is the source of truth for where the spec lives, how an operation
is authored, and how the response envelope is published. Read it before changing route documentation or the schema
customizer.

## When to Use Me

* A route is added, removed, or its path, auth dependency, request body, or response shape changes. The docs change
  belongs in the **same change**.
* The user asks to document, fix, or review the OpenAPI docs of an endpoint.

Do not use this skill to publish the schema to an external host, or to add a hand-written OpenAPI document or a
request-collection tree.

## My procedures

### Step 1: Scope the change

* List the affected routes from `app/http/*_router.py` and `router_registry` in `app/http/__init__.py`: method, full
  path, path function, and dependencies.
* The full path is `settings.API_PREFIX` (`/api`) plus the router `prefix` plus the path on the decorator.
* Read a sibling operation on the same router before writing a new one.

### Step 2: Trace every reachable response

* Follow the call graph from the path function through its dependencies (including `AuthenticatedGuardDep`), the
  service `handle()`, and any readers, writers, or ports that call raises.
* Record every reachable HTTP status and body: `422` from request validation, `401` from the bearer guard, and every
  `AppException` or `HTTPException`, including the `code` string each one produces.

### Step 3: Update the schema in code

* Apply [REFERENCE.md](./references/REFERENCE.md): operation metadata, a return type OpenAPI can see, `responses` for
  each non-success status from Step 2, and the shared OpenAPI customizer.
* If `apply_openapi_schema` is not wired yet, add it in this change. It is global. Do not backfill summaries or
  descriptions on routes this change does not touch.
* Removing a route removes its path operation. Do not leave a stub behind. The operation disappears from the schema
  when the function is deleted.

### Step 4: Check and report

Generate the schema and confirm each affected operation's path, method, success `content` schema, and error statuses.
`ENVIRONMENT=testing` skips `.env`. `APP_ENABLE_DOCS=true` matches the configuration that serves the docs routes.
`create_app().openapi()` still builds the schema when docs are disabled; use the flag so the check matches production
docs settings.

```bash
ENVIRONMENT=testing APP_ENABLE_DOCS=true uv run python -c "
from app import create_app
import json
schema = create_app().openapi()
print(json.dumps(schema['paths'].get('/api/pto/banks/{year}'), indent=2))
"
```

Replace the path with each operation this change touches. A success JSON schema must be the envelope
`{ok, content}`. A `422` schema must not be `HTTPValidationError`.

Then report:

* Files added, changed, and deleted.
* Operations added, changed, and removed, as method plus full path.
* That `/docs`, `/redoc`, and `/openapi.json` are available only when `APP_ENABLE_DOCS` is true.
