import socket

from pytest import MonkeyPatch

from tests.support.isolation import unexpected_interaction


def install_network_guard(monkeypatch: MonkeyPatch) -> None:
    def refuse_connect(self: socket.socket, address: object) -> None:
        unexpected_interaction(f"network connection to {address}")

    def refuse_create_connection(
        address: object, *args: object, **kwargs: object
    ) -> None:
        unexpected_interaction(f"network connection to {address}")

    def refuse_getaddrinfo(*args: object, **kwargs: object) -> None:
        host = args[0] if args else "unknown host"
        unexpected_interaction(f"name resolution for {host}")

    monkeypatch.setattr(socket.socket, "connect", refuse_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse_connect)
    monkeypatch.setattr(socket, "create_connection", refuse_create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", refuse_getaddrinfo)
