from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from power_control_host.models import DeviceVendor, TransportType

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime guard
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


@dataclass(slots=True)
class TransportConfig:
    type: TransportType
    resource: str | None = None
    host: str | None = None
    port: int | None = None
    serial_port: str | None = None
    baudrate: int = 9600
    timeout_ms: int = 3000
    write_termination: str = "\n"
    read_termination: str = "\n"


@dataclass(slots=True)
class DeviceConfig:
    id: str
    vendor: DeviceVendor
    model: str
    transport: TransportConfig
    logical_channels: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class AppDirectories:
    log_dir: Path
    export_dir: Path
    runtime_dir: Path


@dataclass(slots=True)
class AppSettings:
    name: str
    environment: str
    base_dir: Path
    directories: AppDirectories
    devices: list[DeviceConfig]


def load_settings(config_path: str | Path) -> AppSettings:
    if yaml is None:  # pragma: no cover - runtime guard
        raise RuntimeError(
            "缺少 PyYAML，请先执行 `pip install -e .` 或 `pip install PyYAML`。"
        ) from YAML_IMPORT_ERROR

    path = Path(config_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}

    app_section = payload.get("app", {})
    base_dir = path.parent.parent.resolve()
    directories = AppDirectories(
        log_dir=base_dir / app_section.get("log_dir", "logs"),
        export_dir=base_dir / app_section.get("export_dir", "exports"),
        runtime_dir=base_dir / app_section.get("runtime_dir", "runtime"),
    )

    devices = [_build_device_config(item) for item in payload.get("devices", [])]
    if not devices:
        raise ValueError("配置文件中没有 devices 节点，无法启动工程骨架。")

    return AppSettings(
        name=app_section.get("name", "Reliability Power Host"),
        environment=app_section.get("environment", "dev"),
        base_dir=base_dir,
        directories=directories,
        devices=devices,
    )


def _build_device_config(payload: dict[str, Any]) -> DeviceConfig:
    transport_payload = payload.get("transport", {})
    transport = TransportConfig(
        type=TransportType(transport_payload["type"]),
        resource=transport_payload.get("resource"),
        host=transport_payload.get("host"),
        port=transport_payload.get("port"),
        serial_port=transport_payload.get("serial_port"),
        baudrate=int(transport_payload.get("baudrate", 9600)),
        timeout_ms=int(transport_payload.get("timeout_ms", 3000)),
        write_termination=str(transport_payload.get("write_termination", "\n")),
        read_termination=str(transport_payload.get("read_termination", "\n")),
    )

    return DeviceConfig(
        id=str(payload["id"]),
        vendor=DeviceVendor(payload.get("vendor", "unknown")),
        model=str(payload["model"]),
        transport=transport,
        logical_channels=list(payload.get("logical_channels", [])),
        notes=str(payload.get("notes", "")),
    )

