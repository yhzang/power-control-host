from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DeviceVendor(StrEnum):
    OWON = "owon"
    GWINSTEK = "gwinstek"
    UNKNOWN = "unknown"


class TransportType(StrEnum):
    VISA = "visa"
    SOCKET = "socket"
    SERIAL = "serial"


@dataclass(slots=True)
class TelemetrySample:
    device_id: str
    channel: str
    voltage: float | None = None
    current: float | None = None
    mode: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SequenceStep:
    device_id: str
    channel: str
    action: str
    delay_seconds: float = 0.0
    voltage: float | None = None
    current: float | None = None


@dataclass(slots=True)
class SequencePlan:
    name: str
    steps: list[SequenceStep]


@dataclass(slots=True)
class SequenceExecutionEvent:
    timestamp: str
    plan_name: str
    step_index: int
    device_id: str
    channel: str
    action: str
    detail: str = ""

