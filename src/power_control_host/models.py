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
class ChannelCycleSpec:
    channel: str
    on_seconds: float
    off_seconds: float
    cycles: int
    voltage: float | None = None
    current: float | None = None


@dataclass(slots=True)
class RelativeChannelSpec:
    channel: str
    reference_channel: str | None = None
    on_delay_seconds: float = 0.0
    off_advance_seconds: float = 0.0
    voltage: float | None = None
    current: float | None = None


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


@dataclass(slots=True)
class TimingNode:
    """多设备时序中的单个通道节点。

    Args:
        device_id: 设备 ID，与 YAML 配置中的 id 字段对应。
        channel: 通道名，如 CH1、CH2、OUT。
        on_time_seconds: 上电时刻（相对周期开始的绝对偏移，单位秒）。
        off_time_seconds: 下电时刻（相对周期开始的绝对偏移，单位秒）。
        voltage: 可选的预设电压值。
        current: 可选的预设限流值。
        enabled: 是否启用该节点，False 时跳过。
        description: 人工备注，不影响执行。
    """

    device_id: str
    channel: str
    on_time_seconds: float
    off_time_seconds: float
    voltage: float | None = None
    current: float | None = None
    enabled: bool = True
    description: str = ""


@dataclass(slots=True)
class MultiDeviceTimingSpec:
    """多设备时序配置，描述一组跨设备通道时序节点的完整执行计划。

    Args:
        name: 配置名称，用于日志文件命名。
        nodes: 时序节点列表，每个节点对应一个设备通道。
        cycles: 循环次数，0 表示无限循环（当前执行引擎不支持，保留字段）。
        cycle_period_seconds: 单次周期时长（秒）。
            0.0 表示自动计算为所有启用节点 off_time_seconds 的最大值。
    """

    name: str
    nodes: list[TimingNode]
    cycles: int = 1
    cycle_period_seconds: float = 0.0

