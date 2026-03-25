from __future__ import annotations

import csv
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from power_control_host.devices.base import PowerSupplyDevice
from power_control_host.models import (
    ChannelCycleSpec,
    RelativeChannelSpec,
    SequenceExecutionEvent,
    SequencePlan,
    SequenceStep,
)
from power_control_host.services.device_service import DeviceService

WAIT_CHANNEL = "*"
TIME_PRECISION = 9
ACTION_PRIORITY = {
    "set_voltage": 0,
    "set_current": 1,
    "output_off": 2,
    "output_on": 3,
}


@dataclass(slots=True)
class _ScheduledAction:
    time_offset_seconds: float
    device_id: str
    channel: str
    action: str
    voltage: float | None = None
    current: float | None = None


class SequenceService:
    def __init__(
        self,
        device_service: DeviceService,
        runtime_dir: Path,
        *,
        sleep_fn=time.sleep,
    ) -> None:
        self.device_service = device_service
        self.runtime_dir = runtime_dir
        self.sleep_fn = sleep_fn

    def build_simple_startup_plan(self) -> SequencePlan:
        return SequencePlan(
            name="placeholder_startup_plan",
            steps=[
                SequenceStep(device_id="odp_01", channel="CH1", action="set_voltage", voltage=12.0),
                SequenceStep(device_id="odp_01", channel="CH1", action="output_on"),
            ],
        )

    def build_single_channel_cycle_plan(
        self,
        *,
        device_id: str,
        channel: str,
        on_seconds: float,
        off_seconds: float,
        cycles: int,
        voltage: float | None = None,
        current: float | None = None,
    ) -> SequencePlan:
        return self.build_parallel_channel_cycle_plan(
            device_id=device_id,
            channel_specs=[
                ChannelCycleSpec(
                    channel=channel,
                    on_seconds=on_seconds,
                    off_seconds=off_seconds,
                    cycles=cycles,
                    voltage=voltage,
                    current=current,
                )
            ],
            name=f"{device_id}_{channel}_cycle_{cycles}",
        )

    def build_parallel_channel_cycle_plan(
        self,
        *,
        device_id: str,
        channel_specs: list[ChannelCycleSpec],
        name: str | None = None,
    ) -> SequencePlan:
        normalized_specs = self._normalize_channel_cycle_specs(device_id, channel_specs)
        actions: list[_ScheduledAction] = []
        plan_end_offset = 0.0

        for spec in normalized_specs:
            self._validate_channel_cycle_spec(spec)
            actions.extend(self._build_setpoint_actions(device_id, spec.channel, spec.voltage, spec.current))

            period_seconds = self._round_time(spec.on_seconds + spec.off_seconds)
            plan_end_offset = max(
                plan_end_offset,
                self._round_time(spec.cycles * period_seconds),
            )
            for index in range(spec.cycles):
                cycle_start = self._round_time(index * period_seconds)
                actions.append(
                    _ScheduledAction(
                        time_offset_seconds=cycle_start,
                        device_id=device_id,
                        channel=spec.channel,
                        action="output_on",
                    )
                )
                actions.append(
                    _ScheduledAction(
                        time_offset_seconds=self._round_time(cycle_start + spec.on_seconds),
                        device_id=device_id,
                        channel=spec.channel,
                        action="output_off",
                    )
                )

        plan_name = name or self._make_parallel_plan_name(device_id, normalized_specs)
        return self._build_plan_from_actions(plan_name, actions, plan_end_offset=plan_end_offset)

    def build_relative_channel_cycle_plan(
        self,
        *,
        device_id: str,
        on_seconds: float,
        off_seconds: float,
        cycles: int,
        channel_specs: list[RelativeChannelSpec],
        name: str | None = None,
    ) -> SequencePlan:
        self._validate_cycles(cycles)
        self._validate_non_negative("on_seconds", on_seconds)
        self._validate_non_negative("off_seconds", off_seconds)

        normalized_specs = self._normalize_relative_channel_specs(device_id, channel_specs)
        relative_windows = self._resolve_relative_windows(normalized_specs, on_seconds)

        actions: list[_ScheduledAction] = []
        for spec in normalized_specs:
            actions.extend(self._build_setpoint_actions(device_id, spec.channel, spec.voltage, spec.current))

        period_seconds = self._round_time(on_seconds + off_seconds)
        for index in range(cycles):
            cycle_start = self._round_time(index * period_seconds)
            for spec in normalized_specs:
                on_offset, off_offset = relative_windows[spec.channel]
                actions.append(
                    _ScheduledAction(
                        time_offset_seconds=self._round_time(cycle_start + on_offset),
                        device_id=device_id,
                        channel=spec.channel,
                        action="output_on",
                    )
                )
                actions.append(
                    _ScheduledAction(
                        time_offset_seconds=self._round_time(cycle_start + off_offset),
                        device_id=device_id,
                        channel=spec.channel,
                        action="output_off",
                    )
                )

        plan_name = name or self._make_relative_plan_name(device_id, normalized_specs, cycles)
        return self._build_plan_from_actions(
            plan_name,
            actions,
            plan_end_offset=self._round_time(cycles * period_seconds),
        )

    def build_staggered_channel_cycle_plan(
        self,
        *,
        device_id: str,
        lead_channel: str,
        lag_channel: str,
        delay_seconds: float,
        hold_seconds: float,
        rest_seconds: float,
        cycles: int,
        lead_voltage: float | None = None,
        lead_current: float | None = None,
        lag_voltage: float | None = None,
        lag_current: float | None = None,
    ) -> SequencePlan:
        return self.build_relative_channel_cycle_plan(
            device_id=device_id,
            on_seconds=(delay_seconds * 2) + hold_seconds,
            off_seconds=rest_seconds,
            cycles=cycles,
            channel_specs=[
                RelativeChannelSpec(
                    channel=lead_channel,
                    voltage=lead_voltage,
                    current=lead_current,
                ),
                RelativeChannelSpec(
                    channel=lag_channel,
                    reference_channel=lead_channel,
                    on_delay_seconds=delay_seconds,
                    off_advance_seconds=delay_seconds,
                    voltage=lag_voltage,
                    current=lag_current,
                ),
            ],
            name=f"{device_id}_{lead_channel}_{lag_channel}_staggered_{cycles}",
        )

    def execute_plan(
        self,
        plan: SequencePlan,
        *,
        log_path: str | Path | None = None,
    ) -> list[SequenceExecutionEvent]:
        events: list[SequenceExecutionEvent] = []
        current_device: PowerSupplyDevice | None = None

        try:
            for index, step in enumerate(plan.steps, start=1):
                if step.action == "wait":
                    self.sleep_fn(step.delay_seconds)
                    events.append(
                        self._make_event(
                            plan_name=plan.name,
                            step_index=index,
                            device_id=step.device_id,
                            channel=step.channel,
                            action="wait",
                            detail=f"seconds={step.delay_seconds}",
                        )
                    )
                    continue

                device = self.device_service.get_device(step.device_id)
                if current_device is None or current_device.config.id != device.config.id:
                    if current_device is not None:
                        current_device.disconnect()
                    current_device = device
                    current_device.connect()

                detail = self._execute_device_step(current_device, step)
                events.append(
                    self._make_event(
                        plan_name=plan.name,
                        step_index=index,
                        device_id=step.device_id,
                        channel=step.channel,
                        action=step.action,
                        detail=detail,
                    )
                )
        finally:
            if current_device is not None:
                current_device.disconnect()

        if log_path is not None:
            self.write_event_log(events, log_path)

        return events

    def write_event_log(
        self,
        events: list[SequenceExecutionEvent],
        log_path: str | Path,
    ) -> Path:
        path = Path(log_path)
        if not path.is_absolute():
            path = self.runtime_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp",
                    "plan_name",
                    "step_index",
                    "device_id",
                    "channel",
                    "action",
                    "detail",
                ],
            )
            writer.writeheader()
            for event in events:
                writer.writerow(asdict(event))

        return path

    def _execute_device_step(
        self,
        device: PowerSupplyDevice,
        step: SequenceStep,
    ) -> str:
        if step.action == "set_voltage":
            if step.voltage is None:
                raise ValueError("set_voltage step 缺少 voltage")
            device.set_voltage(step.channel, step.voltage)
            return f"voltage={step.voltage}"

        if step.action == "set_current":
            if step.current is None:
                raise ValueError("set_current step 缺少 current")
            device.set_current(step.channel, step.current)
            return f"current={step.current}"

        if step.action == "output_on":
            device.output_on(step.channel)
            return "state=on"

        if step.action == "output_off":
            device.output_off(step.channel)
            return "state=off"

        raise ValueError(f"未知步骤动作: {step.action}")

    def _normalize_channel_cycle_specs(
        self,
        device_id: str,
        channel_specs: list[ChannelCycleSpec],
    ) -> list[ChannelCycleSpec]:
        if not channel_specs:
            raise ValueError("至少需要提供一个 channel spec")

        channel_map = self._build_channel_map(device_id)
        normalized_specs: list[ChannelCycleSpec] = []
        for spec in channel_specs:
            normalized_specs.append(
                ChannelCycleSpec(
                    channel=self._resolve_channel_name(spec.channel, channel_map),
                    on_seconds=spec.on_seconds,
                    off_seconds=spec.off_seconds,
                    cycles=spec.cycles,
                    voltage=spec.voltage,
                    current=spec.current,
                )
            )
        self._validate_unique_channels(item.channel for item in normalized_specs)
        return normalized_specs

    def _normalize_relative_channel_specs(
        self,
        device_id: str,
        channel_specs: list[RelativeChannelSpec],
    ) -> list[RelativeChannelSpec]:
        if not channel_specs:
            raise ValueError("至少需要提供一个 channel spec")

        channel_map = self._build_channel_map(device_id)
        normalized_specs: list[RelativeChannelSpec] = []
        for spec in channel_specs:
            normalized_specs.append(
                RelativeChannelSpec(
                    channel=self._resolve_channel_name(spec.channel, channel_map),
                    reference_channel=(
                        self._resolve_channel_name(spec.reference_channel, channel_map)
                        if spec.reference_channel
                        else None
                    ),
                    on_delay_seconds=spec.on_delay_seconds,
                    off_advance_seconds=spec.off_advance_seconds,
                    voltage=spec.voltage,
                    current=spec.current,
                )
            )
        self._validate_unique_channels(item.channel for item in normalized_specs)
        return normalized_specs

    def _build_channel_map(self, device_id: str) -> dict[str, str]:
        channels = self.device_service.get_logical_channels(device_id)
        if not channels:
            raise ValueError(f"设备 {device_id} 未配置 logical_channels，无法执行多通道时序。")

        channel_map: dict[str, str] = {}
        for item in channels:
            normalized = self._normalize_channel_name(item)
            if normalized:
                channel_map[normalized] = item
        return channel_map

    def _resolve_channel_name(
        self,
        channel: str | None,
        channel_map: dict[str, str],
    ) -> str:
        if channel is None:
            raise ValueError("通道名不能为空")

        normalized = self._normalize_channel_name(channel)
        if normalized not in channel_map:
            available = ", ".join(channel_map.values())
            raise ValueError(f"通道 {channel} 未在设备配置中声明，可用通道: {available}")
        return channel_map[normalized]

    def _normalize_channel_name(self, channel: str) -> str:
        return channel.strip().upper()

    def _validate_unique_channels(self, channels) -> None:
        seen: set[str] = set()
        duplicates: list[str] = []
        for channel in channels:
            if channel in seen and channel not in duplicates:
                duplicates.append(channel)
            seen.add(channel)
        if duplicates:
            joined = ", ".join(sorted(duplicates))
            raise ValueError(f"channel spec 中存在重复通道: {joined}")

    def _validate_channel_cycle_spec(self, spec: ChannelCycleSpec) -> None:
        self._validate_cycles(spec.cycles)
        self._validate_non_negative("on_seconds", spec.on_seconds)
        self._validate_non_negative("off_seconds", spec.off_seconds)
        if spec.on_seconds <= 0:
            raise ValueError(f"通道 {spec.channel} 的有效导通时长必须大于 0")

    def _resolve_relative_windows(
        self,
        channel_specs: list[RelativeChannelSpec],
        group_on_seconds: float,
    ) -> dict[str, tuple[float, float]]:
        spec_by_channel = {item.channel: item for item in channel_specs}
        resolved: dict[str, tuple[float, float]] = {}
        visiting: set[str] = set()

        def visit(channel: str) -> tuple[float, float]:
            if channel in resolved:
                return resolved[channel]
            if channel in visiting:
                raise ValueError("relative_offset 通道依赖存在循环引用")

            visiting.add(channel)
            spec = spec_by_channel[channel]
            self._validate_non_negative("on_delay_seconds", spec.on_delay_seconds)
            self._validate_non_negative("off_advance_seconds", spec.off_advance_seconds)

            if spec.reference_channel is None:
                on_offset = self._round_time(spec.on_delay_seconds)
                off_offset = self._round_time(group_on_seconds - spec.off_advance_seconds)
            else:
                if spec.reference_channel not in spec_by_channel:
                    raise ValueError(
                        f"通道 {spec.channel} 引用了不存在的参考通道 {spec.reference_channel}"
                    )
                ref_on, ref_off = visit(spec.reference_channel)
                on_offset = self._round_time(ref_on + spec.on_delay_seconds)
                off_offset = self._round_time(ref_off - spec.off_advance_seconds)

            if off_offset <= on_offset:
                raise ValueError(f"通道 {spec.channel} 的有效导通时长必须大于 0")

            resolved[channel] = (on_offset, off_offset)
            visiting.remove(channel)
            return resolved[channel]

        for channel in spec_by_channel:
            visit(channel)

        return resolved

    def _build_setpoint_actions(
        self,
        device_id: str,
        channel: str,
        voltage: float | None,
        current: float | None,
    ) -> list[_ScheduledAction]:
        actions: list[_ScheduledAction] = []
        if voltage is not None:
            actions.append(
                _ScheduledAction(
                    time_offset_seconds=0.0,
                    device_id=device_id,
                    channel=channel,
                    action="set_voltage",
                    voltage=voltage,
                )
            )
        if current is not None:
            actions.append(
                _ScheduledAction(
                    time_offset_seconds=0.0,
                    device_id=device_id,
                    channel=channel,
                    action="set_current",
                    current=current,
                )
            )
        return actions

    def _build_plan_from_actions(
        self,
        plan_name: str,
        actions: list[_ScheduledAction],
        *,
        plan_end_offset: float | None = None,
    ) -> SequencePlan:
        if not actions:
            raise ValueError("序列计划没有可执行动作")

        sorted_actions = sorted(
            actions,
            key=lambda item: (
                item.time_offset_seconds,
                ACTION_PRIORITY[item.action],
                item.channel,
            ),
        )

        steps: list[SequenceStep] = []
        current_offset = 0.0
        for action in sorted_actions:
            wait_seconds = self._round_time(action.time_offset_seconds - current_offset)
            if wait_seconds > 0:
                steps.append(
                    SequenceStep(
                        device_id=action.device_id,
                        channel=WAIT_CHANNEL,
                        action="wait",
                        delay_seconds=wait_seconds,
                    )
                )
                current_offset = action.time_offset_seconds

            steps.append(
                SequenceStep(
                    device_id=action.device_id,
                    channel=action.channel,
                    action=action.action,
                    voltage=action.voltage,
                    current=action.current,
                )
            )

        if plan_end_offset is not None:
            tail_wait = self._round_time(plan_end_offset - current_offset)
            if tail_wait > 0:
                steps.append(
                    SequenceStep(
                        device_id=sorted_actions[-1].device_id,
                        channel=WAIT_CHANNEL,
                        action="wait",
                        delay_seconds=tail_wait,
                    )
                )

        return SequencePlan(name=plan_name, steps=steps)

    def _make_parallel_plan_name(
        self,
        device_id: str,
        channel_specs: list[ChannelCycleSpec],
    ) -> str:
        channels = "_".join(item.channel for item in channel_specs)
        return f"{device_id}_{channels}_parallel"

    def _make_relative_plan_name(
        self,
        device_id: str,
        channel_specs: list[RelativeChannelSpec],
        cycles: int,
    ) -> str:
        channels = "_".join(item.channel for item in channel_specs)
        return f"{device_id}_{channels}_relative_{cycles}"

    def _make_event(
        self,
        *,
        plan_name: str,
        step_index: int,
        device_id: str,
        channel: str,
        action: str,
        detail: str,
    ) -> SequenceExecutionEvent:
        return SequenceExecutionEvent(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            plan_name=plan_name,
            step_index=step_index,
            device_id=device_id,
            channel=channel,
            action=action,
            detail=detail,
        )

    def _validate_cycles(self, cycles: int) -> None:
        if cycles <= 0:
            raise ValueError("cycles 必须大于 0")

    def _validate_non_negative(self, field_name: str, value: float) -> None:
        if value < 0:
            raise ValueError(f"{field_name} 必须大于或等于 0")

    def _round_time(self, value: float) -> float:
        return round(value, TIME_PRECISION)
