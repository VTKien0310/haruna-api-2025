import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_core_does_not_import_features_http_or_ports() -> None:
    assert _imports_under("app/core", ("app.features", "app.http", "app.ports")) == []


def test_features_do_not_import_http() -> None:
    assert _imports_under("app/features", ("app.http",)) == []


def test_ports_do_not_import_features_or_http() -> None:
    assert _imports_under("app/ports", ("app.features", "app.http")) == []


def test_create_client_is_only_used_by_the_supabase_port() -> None:
    found = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "app").rglob("*.py")
        if "create_client" in path.read_text(encoding="utf-8")
    ]
    assert found == ["app/ports/supabase/spb.py"]


def _imports_under(directory: str, forbidden: tuple[str, ...]) -> list[str]:
    violations = []
    for path in (ROOT / directory).rglob("*.py"):
        for module in _imported_modules(path):
            if any(
                module == name or module.startswith(f"{name}.") for name in forbidden
            ):
                violations.append(f"{path.relative_to(ROOT).as_posix()}: {module}")
    return violations


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package_parts = path.relative_to(ROOT).with_suffix("").parts[:-1]
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.ImportFrom) and node.level > 0:
            parent = package_parts[: len(package_parts) - (node.level - 1)]
            if node.module:
                modules.append(".".join((*parent, node.module)))
            else:
                modules.append(".".join(parent))
    return modules
