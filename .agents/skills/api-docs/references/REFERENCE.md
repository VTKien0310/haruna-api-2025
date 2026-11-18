# API Documentation (FastAPI OpenAPI) — Reference

> Paths such as `app/...` and `doc/...` are relative to the repository root. Read this before writing route
> documentation.

The API spec is the OpenAPI document FastAPI builds from the application. Swagger UI, ReDoc, and `/openapi.json` are
views of that document. A route is documented when the generated schema describes its path, auth, body, and every
reachable response, including the JSON envelope this app actually returns.

Standards that affect the contract live in [coding.md](../../../../doc/conventions-and-standards/coding.md) and
[restful-api.md](../../../../doc/conventions-and-standards/restful-api.md). Follow those documents when they constrain
paths, query strings, or the envelope.

## Where the spec lives

`bootstrap_application` in `app/core/bootstrap.py` constructs the app with:

* `title=settings.APP_NAME`
* `version=settings.APP_VERSION`
* `docs_url="/docs"`, `redoc_url="/redoc"`, and `openapi_url="/openapi.json"` when `settings.APP_ENABLE_DOCS` is true
* those three URLs set to `None` when docs are disabled (`APP_ENABLE_DOCS` defaults to false)

Leave `title` and `version` on that `FastAPI()` call. Do not add a hand-maintained OpenAPI file or a collection
directory. Routers are registered in `app/http/__init__.py` and mounted at `settings.API_PREFIX` (`/api`).

`APP_ENABLE_DOCS` is the conditional-docs switch described in
[Conditional OpenAPI](https://fastapi.tiangolo.com/how-to/conditional-openapi/). Disabling docs removes the HTTP
routes. It does not change how `app.openapi()` builds the schema in process.

## Docs UI

FastAPI serves the UIs itself. With the defaults above, `/docs` uses `fastapi.openapi.docs.get_swagger_ui_html` and
`/redoc` uses `get_redoc_html`. Both load `/openapi.json`. `get_swagger_ui_oauth2_redirect_html` is the OAuth2
redirect page. `swagger_ui_default_parameters` is the Swagger UI config those pages start from (`deepLinking`,
`showExtensions`, and the rest).

Reference: [OpenAPI docs](https://fastapi.tiangolo.com/reference/openapi/docs/).

Call `get_swagger_ui_html` or `get_redoc_html` only when the user asks to replace the docs HTML: self-hosted Swagger
or ReDoc assets, an OAuth2 redirect, or custom `swagger_ui_parameters`. See
[Configure Swagger UI](https://fastapi.tiangolo.com/how-to/configure-swagger-ui/) and
[Custom Docs UI Static Assets](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/). Do not reimplement those
pages as part of documenting a route.

## How a route becomes an operation

One path function is one operation. The router already sets the group:

```python
router = APIRouter(prefix="/pto", tags=["pto"], dependencies=[AuthenticatedGuardDep])
```

`tags` is the OpenAPI tag. Keep one tag per router. Add another tag only when the operation truly belongs to a second
group.

On the decorator, set:

* `summary`: a short label with the method and full path, for example `PUT /api/pto/banks/{year}`
* `description`: the spec another developer can read without opening the service. Include the method and path, whether
  the route requires the bearer guard, the body or path parameters, and an index of every status and `error.code`
  from the call graph. When the body carries a credential or other secret, say so in the first line.
* `status_code`: only when the success status is not 200
* `responses`: one entry per non-success status recorded while tracing the call graph
* a return annotation (see below)

FastAPI builds `operationId` from the function name. Keep path-function names unique across the app.

`Path`, `Query`, and Pydantic `Field` need a `description` and their real constraints (`min_length`, `gt`, and so
on). Query strings follow the [JSON:API](https://jsonapi.org/) rules in `doc/conventions-and-standards/restful-api.md`.
Document each query parameter with `Query`; do not read a query from a raw dict.

Sample values use the reserved `example.com` domain, for example `user-email@example.com`, via `Field(..., examples=[...])`.

Protected routers keep `dependencies=[AuthenticatedGuardDep]`. `HTTPBearer` in
`app/features/auth/guards/authenticated_user_guard.py` is what publishes the bearer security scheme. Do not register a
second scheme. A missing or rejected token is HTTP 401. The handler maps that status to `error.code` `unauthorized`.

## Types the schema can see

OpenAPI describes the **inner** value the path function returns. The customizer below wraps that schema in the
envelope. Routers return the inner value and do not build `{"ok": ...}` themselves.

* A domain `@dataclass` stays a dataclass. Annotate the path function with it (`-> PtoBank`, `-> list[Language]`).
  FastAPI emits that type as the inner schema. Do not convert a domain entity to a Pydantic model just to document it.
  Dataclass fields have no `Field(description=...)`. Put field meaning in the operation `description` when the name is
  not enough.
* A shaped dict that is not an entity (`translated_text`, `thumbnail_signed_url`) needs a Pydantic response model.
  `-> dict` and a missing annotation publish an empty object. Put the model in
  `app/features/<feature>/responses/<name>_response.py`, re-export it from the feature package, and use it as the
  return annotation.
* Request bodies stay Pydantic request DTOs in `requests/`, with `Field` constraints and descriptions.

## Response envelope

`_WrapResponseMiddleware` in `app/core/response.py` wraps every `application/json` body:

* success (`status < 400`): `{"ok": true, "content": <inner value>}`
* failure: `{"ok": false, "content": <handler body>}`

Handlers in `app/core/error.py` build the handler body before that wrap:

* `HTTPException`: `{"error": {"code", "message", "path"}}`. `code` comes from the status map: `401` `unauthorized`,
  `403` `forbidden`, `404` `not_found`, `409` `conflict`, `500` `internal_server_error`, otherwise `unknown_error`.
  `message` is `exc.detail`.
* `AppException`: the same object, but `code` is the `code` argument passed at the `raise`. A 404 from an
  `AppException` is not automatically `not_found`. Read the raise. One status can carry several codes (for example
  `pto_bank_not_found` and `profile_not_found`).
* `RequestValidationError`: status `422` (`status.HTTP_422_UNPROCESSABLE_CONTENT`), `code` `validation_error`,
  `message` `Invalid request body`, plus `details`: a list of `{loc, msg, type}` where `loc` is the last segment of
  the Pydantic location.

FastAPI's default schema does not know about this middleware or these handlers. It publishes the inner return type as
the whole body, and it publishes `HTTPValidationError` for 422. The customizer corrects both. Route `responses`
describe the handler body only, never the `ok` / `content` wrapper.

## Error responses

Document each non-success status with `error_response` from `app.core` (defined in `app/core/openapi.py` and
re-exported from the package):

```python
from fastapi import status
from app.core import error_response

@router.put(
    "/banks/{year}",
    summary="PUT /api/pto/banks/{year}",
    description=(
        "Return the caller's PTO bank for the given year, creating the current-year bank when it is missing.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Responses:\n"
        "- 200: the PTO bank\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 404: pto_bank_not_found when a past year has no bank; profile_not_found when the user has no profile\n"
        "- 422: validation_error when year is not an integer\n"
    ),
    responses={
        status.HTTP_404_NOT_FOUND: error_response(
            "A past year has no bank (pto_bank_not_found), or the user has no profile (profile_not_found).",
            "pto_bank_not_found",
            "profile_not_found",
        ),
    },
)
async def put_pto_bank(...) -> PtoBank:
    ...
```

`error_response(description, *codes)` returns an OpenAPI response object whose JSON schema is the handler body
`{"error": {code, message, path}}`. One code uses `const`. Several codes on the same status use `enum`. The
description says when each code is raised. Do not put `ok` or `content` in this object.

Do not hand-write 401 on every protected route or 422 on every validated body. The customizer adds those two from the
security requirement and from FastAPI's generated 422, using `unauthorized` and `validation_error`. Still list them
in the operation `description`. Extra statuses and `AppException` codes belong in `responses`, because the customizer
cannot see which code a service raises.

Document only statuses the call graph can reach. Do not add a generic 500 unless some branch raises it.

## OpenAPI customizer

One customizer owns the envelope. Follow
[Extending OpenAPI](https://fastapi.tiangolo.com/how-to/extending-openapi/). Implement it in `app/core/openapi.py` and
call `apply_openapi_schema(app)` from `bootstrap_application` **after** `_load_routes`, so every mounted route is
visible. Cache the result on `app.openapi_schema`.

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def apply_openapi_schema(app: FastAPI) -> None:
    def openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )
        _rewrite(schema)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
```

`_rewrite` walks `schema["paths"]` and each method in `_METHODS`:

1. **422.** FastAPI adds a `422` response whose schema is `#/components/schemas/HTTPValidationError`. Replace that
   inner schema with the validation handler body (`error.code` const `validation_error`, `message` const
   `Invalid request body`, `path` string, `details` array of `{loc, msg, type}`). `loc` has no single JSON type.
2. **401 on secured operations.** If the operation's `security` list is non-empty and it has no `401` response, add
   one with `error_response("Missing or rejected bearer token.", "unauthorized")`.
3. **Wrap `application/json`.** For every response that has an `application/json` schema, if that schema is not already
   an object with `ok` and `content` properties, replace it with:

```python
{
    "type": "object",
    "required": ["ok", "content"],
    "properties": {
        "ok": {"type": "boolean", "const": status_code < 400},
        "content": inner_schema,
    },
}
```

   Leave a `$ref` as the `content` schema. That `$ref` is the inner model or the handler body. Wrap responses with no
   JSON schema only when step 1 or 2 just added one. Do not invent a body for 204 or for a non-JSON response.
4. **Drop unused stock names.** After the walk, remove `components.schemas.HTTPValidationError` and
   `ValidationError` when nothing still references them.

Wrapping is idempotent: a schema that already has `ok` and `content` stays as it is. Route code never builds the
envelope, so a second wrap means the customizer ran twice on an uncached schema. Fix that instead of unwrapping at
the router.

Add `error_response` in the same module and re-export it from `app/core/__init__.py`:

```python
from .openapi import error_response as error_response
```

## When to add, update, or remove an operation

* A new route needs its summary, description, return type, and `responses` in the same change.
* A changed path, auth dependency, body, or response shape updates that operation and its models in the same change.
* A removed route deletes the path function and any response model that only that route used.
* The first change that documents a route also adds `apply_openapi_schema` if it is not wired yet. The customizer then
  wraps every operation, including ones this change does not otherwise edit. Leave their summaries alone unless the
  user asked to document the whole API.
* Shared error components inside the customizer change in the same change that changes the handler shape in
  `app/core/error.py` or the envelope in `app/core/response.py`.
