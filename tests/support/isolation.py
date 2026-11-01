_violations: list[str] = []


def unexpected_interaction(operation: str) -> None:
    message = (
        f"Unexpected external interaction: {operation}. Configure an in-memory fake."
    )
    _violations.append(message)
    raise RuntimeError(message)


def assert_no_unexpected_interactions() -> None:
    messages = list(_violations)
    _violations.clear()
    if messages:
        raise AssertionError("\n".join(messages))
