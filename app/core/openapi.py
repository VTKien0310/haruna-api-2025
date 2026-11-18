from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
_STOCK_SCHEMAS = ("HTTPValidationError", "ValidationError")


def error_response(description: str, *codes: str) -> dict:
    if len(codes) == 1:
        code_schema: dict = {"type": "string", "const": codes[0]}
    else:
        code_schema = {"type": "string", "enum": list(codes)}

    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["error"],
                    "properties": {
                        "error": {
                            "type": "object",
                            "required": ["code", "message", "path"],
                            "properties": {
                                "code": code_schema,
                                "message": {"type": "string"},
                                "path": {"type": "string"},
                            },
                        }
                    },
                }
            }
        },
    }


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


def _rewrite(schema: dict) -> None:
    for path_item in schema.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in _METHODS or not isinstance(operation, dict):
                continue
            responses = operation.setdefault("responses", {})
            _replace_validation_error(responses)
            _add_unauthorized(operation, responses)
            for status_code, response in responses.items():
                if isinstance(response, dict):
                    _wrap_json(response, status_code)
    _drop_unused_stock_schemas(schema)


def _replace_validation_error(responses: dict) -> None:
    response = responses.get("422")
    if not isinstance(response, dict):
        return
    media = (response.get("content") or {}).get("application/json")
    if not isinstance(media, dict):
        return
    schema = media.get("schema")
    if not isinstance(schema, dict):
        return
    ref = schema.get("$ref", "")
    if not ref.endswith("/HTTPValidationError"):
        return
    media["schema"] = _validation_handler_body()


def _validation_handler_body() -> dict:
    return {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message", "details", "path"],
                "properties": {
                    "code": {"type": "string", "const": "validation_error"},
                    "message": {"type": "string", "const": "Invalid request body"},
                    "details": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["loc", "msg", "type"],
                            "properties": {
                                "loc": {},
                                "msg": {"type": "string"},
                                "type": {"type": "string"},
                            },
                        },
                    },
                    "path": {"type": "string"},
                },
            }
        },
    }


def _add_unauthorized(operation: dict, responses: dict) -> None:
    if not operation.get("security") or "401" in responses:
        return
    responses["401"] = error_response(
        "Missing or rejected bearer token.",
        "unauthorized",
    )


def _wrap_json(response: dict, status_code: object) -> None:
    media = (response.get("content") or {}).get("application/json")
    if not isinstance(media, dict):
        return
    schema = media.get("schema")
    if not isinstance(schema, dict) or _is_envelope(schema):
        return
    try:
        code = int(status_code)
    except TypeError, ValueError:
        return
    media["schema"] = {
        "type": "object",
        "required": ["ok", "content"],
        "properties": {
            "ok": {"type": "boolean", "const": code < 400},
            "content": schema,
        },
    }


def _is_envelope(schema: dict) -> bool:
    properties = schema.get("properties")
    return (
        isinstance(properties, dict) and "ok" in properties and "content" in properties
    )


def _drop_unused_stock_schemas(schema: dict) -> None:
    components = schema.get("components")
    if not isinstance(components, dict):
        return
    schemas = components.get("schemas")
    if not isinstance(schemas, dict):
        return
    for name in _STOCK_SCHEMAS:
        if name not in schemas:
            continue
        held = schemas.pop(name)
        if _contains_ref(schema, f"#/components/schemas/{name}"):
            schemas[name] = held


def _contains_ref(node: object, ref: str) -> bool:
    if isinstance(node, dict):
        if node.get("$ref") == ref:
            return True
        return any(_contains_ref(value, ref) for value in node.values())
    if isinstance(node, list):
        return any(_contains_ref(item, ref) for item in node)
    return False
