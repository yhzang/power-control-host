from __future__ import annotations

import socket

from power_control_host.models import TransportType
from power_control_host.settings import TransportConfig
from power_control_host.transports.base import BaseTransport


class SocketTransport(BaseTransport):
    def __init__(self, config: TransportConfig) -> None:
        super().__init__(config)
        self._socket: socket.socket | None = None

    def connect(self) -> None:
        if not self.config.host or not self.config.port:
            raise ValueError("Socket 传输缺少 host 或 port 配置。")
        if self.connected:
            return

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.config.timeout_ms / 1000)
        self._socket.connect((self.config.host, self.config.port))
        self.connected = True

    def disconnect(self) -> None:
        if self._socket is not None:
            self._socket.close()
        self._socket = None
        self.connected = False

    def write(self, command: str) -> None:
        self._ensure_connected()
        payload = f"{command}{self.config.write_termination}".encode()
        self._socket.sendall(payload)

    def query(self, command: str) -> str:
        self.write(command)
        return self.read()

    def read(self) -> str:
        self._ensure_connected()
        chunks: list[bytes] = []
        terminator = (
            self.config.read_termination.encode()
            if self.config.read_termination
            else None
        )

        while True:
            try:
                data = self._socket.recv(4096)
            except socket.timeout:
                break

            if not data:
                break

            chunks.append(data)
            joined = b"".join(chunks)

            if terminator and joined.endswith(terminator):
                break

            if not terminator and len(data) < 4096:
                break

        return b"".join(chunks).decode(errors="ignore").strip()

    def _ensure_connected(self) -> None:
        if not self.connected or self._socket is None:
            raise RuntimeError("Socket 连接尚未建立。")


def run_socket_command(
    host: str,
    port: int,
    command: str,
    *,
    timeout_ms: int = 3000,
    write_termination: str = "\n",
    read_termination: str = "\n",
    expect_response: bool = True,
) -> str | None:
    config = TransportConfig(
        type=TransportType.SOCKET,
        host=host,
        port=port,
        timeout_ms=timeout_ms,
        write_termination=write_termination,
        read_termination=read_termination,
    )
    transport = SocketTransport(config)
    transport.connect()
    try:
        if expect_response:
            return transport.query(command)
        transport.write(command)
        return None
    finally:
        transport.disconnect()

