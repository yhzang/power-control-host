from __future__ import annotations

from typing import Any

from power_control_host.settings import TransportConfig
from power_control_host.transports.base import BaseTransport

try:
    import serial
except ImportError as exc:  # pragma: no cover - runtime guard
    serial = None
    SERIAL_IMPORT_ERROR = exc
else:
    SERIAL_IMPORT_ERROR = None


class SerialTransport(BaseTransport):
    def __init__(self, config: TransportConfig) -> None:
        super().__init__(config)
        self._client: Any = None

    def connect(self) -> None:
        if serial is None:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "缺少 pyserial，请先安装项目依赖。"
            ) from SERIAL_IMPORT_ERROR
        if not self.config.serial_port:
            raise ValueError("串口传输缺少 serial_port 配置。")
        if self.connected:
            return

        self._client = serial.Serial(
            port=self.config.serial_port,
            baudrate=self.config.baudrate,
            timeout=self.config.timeout_ms / 1000,
        )
        self.connected = True

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self.connected = False

    def write(self, command: str) -> None:
        self._ensure_connected()
        payload = f"{command}{self.config.write_termination}".encode()
        self._client.write(payload)

    def query(self, command: str) -> str:
        self.write(command)
        self._ensure_connected()
        return self._client.readline().decode(errors="ignore").strip()

    def _ensure_connected(self) -> None:
        if not self.connected or self._client is None:
            raise RuntimeError("串口连接尚未建立。")

