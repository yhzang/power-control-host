"""timing_config.py — 多设备时序配置的 JSON 持久化。

提供将 MultiDeviceTimingSpec 保存为 JSON 文件并重新加载的工具函数。
使用 Python 标准库 json，不依赖额外包。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from power_control_host.models import MultiDeviceTimingSpec, TimingNode


def save_timing_config(spec: MultiDeviceTimingSpec, path: str | Path) -> Path:
    """将多设备时序配置序列化为 JSON 文件。

    Args:
        spec: 要保存的时序配置对象。
        path: 目标 JSON 文件路径（可以不存在，父目录会自动创建）。

    Returns:
        已写入的文件路径（绝对路径）。
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(asdict(spec), handle, indent=2, ensure_ascii=False)
    return target


def load_timing_config(path: str | Path) -> MultiDeviceTimingSpec:
    """从 JSON 文件加载多设备时序配置。

    Args:
        path: 源 JSON 文件路径。

    Returns:
        反序列化后的 MultiDeviceTimingSpec 对象。

    Raises:
        FileNotFoundError: 文件不存在时抛出。
        ValueError: JSON 格式错误或缺少必填字段时抛出。
    """
    source = Path(path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"时序配置文件不存在: {source}")

    with source.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    try:
        nodes = [
            TimingNode(
                device_id=str(node["device_id"]),
                channel=str(node["channel"]),
                on_time_seconds=float(node["on_time_seconds"]),
                off_time_seconds=float(node["off_time_seconds"]),
                voltage=_optional_float(node.get("voltage")),
                current=_optional_float(node.get("current")),
                enabled=bool(node.get("enabled", True)),
                description=str(node.get("description", "")),
            )
            for node in payload.get("nodes", [])
        ]
        return MultiDeviceTimingSpec(
            name=str(payload["name"]),
            nodes=nodes,
            cycles=int(payload.get("cycles", 1)),
            cycle_period_seconds=float(payload.get("cycle_period_seconds", 0.0)),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"时序配置文件格式错误: {source}\n详情: {exc}"
        ) from exc


def _optional_float(value: object) -> float | None:
    """将值转换为 float；None 或缺失字段保持为 None。"""
    if value is None:
        return None
    return float(value)
