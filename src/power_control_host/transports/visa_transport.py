from __future__ import annotations

from typing import Any

from power_control_host.settings import TransportConfig
from power_control_host.transports.base import BaseTransport

try:
    import pyvisa
except ImportError as exc:  # pragma: no cover - runtime guard
    pyvisa = None
    PYVISA_IMPORT_ERROR = exc
else:
    PYVISA_IMPORT_ERROR = None


def list_visa_resources() -> tuple[str, ...]:
    resource_manager = _build_resource_manager()
    try:
        return tuple(str(item) for item in resource_manager.list_resources())
    finally:
        close = getattr(resource_manager, "close", None)
        if callable(close):
            close()


def probe_visa_resource(
    resource: str,
    command: str = "*IDN?",
    timeout_ms: int = 3000,
    write_termination: str = "\n",
    read_termination: str = "\n",
) -> str:
    resource_manager = _build_resource_manager()
    handle: Any = None
    try:
        handle = resource_manager.open_resource(resource)
        handle.timeout = timeout_ms
        handle.write_termination = write_termination
        handle.read_termination = read_termination
        return str(handle.query(command)).strip()
    finally:
        if handle is not None:
            handle.close()
        close = getattr(resource_manager, "close", None)
        if callable(close):
            close()


class VisaTransport(BaseTransport):
    def __init__(self, config: TransportConfig) -> None:
        super().__init__(config)
        self._resource_manager: Any = None
        self._resource: Any = None

    def connect(self) -> None:
        if pyvisa is None:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "缺少 pyvisa，请先安装项目依赖。"
            ) from PYVISA_IMPORT_ERROR
        if not self.config.resource:
            raise ValueError("VISA 传输缺少 resource 配置。")
        if self.connected:
            return

        self._resource_manager = _build_resource_manager()
        self._resource = self._resource_manager.open_resource(self.config.resource)
        self._resource.timeout = self.config.timeout_ms
        self._resource.write_termination = self.config.write_termination
        self._resource.read_termination = self.config.read_termination
        self.connected = True

    def disconnect(self) -> None:
        if self._resource is not None:
            self._resource.close()
        self._resource = None
        self.connected = False

    def write(self, command: str) -> None:
        self._ensure_connected()
        self._resource.write(command)

    def query(self, command: str) -> str:
        self._ensure_connected()
        return str(self._resource.query(command)).strip()

    def _ensure_connected(self) -> None:
        if not self.connected or self._resource is None:
            raise RuntimeError("VISA 连接尚未建立。")


def _build_resource_manager():
    if pyvisa is None:  # pragma: no cover - runtime guard
        raise RuntimeError(
            "缺少 pyvisa，请先安装项目依赖。"
        ) from PYVISA_IMPORT_ERROR
    return pyvisa.ResourceManager()
