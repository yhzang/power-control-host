from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from power_control_host.logging_config import configure_logging
from power_control_host.services.device_service import DeviceService
from power_control_host.services.sequence_service import SequenceService
from power_control_host.settings import AppSettings, load_settings


@dataclass(slots=True)
class ApplicationContext:
    settings: AppSettings
    device_service: DeviceService
    sequence_service: SequenceService


def create_app(config_path: str | Path) -> ApplicationContext:
    settings = load_settings(config_path)
    configure_logging(settings.directories.log_dir)
    _ensure_directories(settings)
    device_service = DeviceService(settings)
    return ApplicationContext(
        settings=settings,
        device_service=device_service,
        sequence_service=SequenceService(device_service, settings.directories.runtime_dir),
    )


def _ensure_directories(settings: AppSettings) -> None:
    settings.directories.log_dir.mkdir(parents=True, exist_ok=True)
    settings.directories.export_dir.mkdir(parents=True, exist_ok=True)
    settings.directories.runtime_dir.mkdir(parents=True, exist_ok=True)

