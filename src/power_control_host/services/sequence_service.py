from __future__ import annotations

import csv
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from power_control_host.devices.base import PowerSupplyDevice
from power_control_host.models import (
    SequenceExecutionEvent,
    SequencePlan,
    SequenceStep,
)
from power_control_host.services.device_service import DeviceService


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
        self._validate_cycles(cycles)
        steps: list[SequenceStep] = []

        if voltage is not None:
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=channel,
                    action="set_voltage",
                    voltage=voltage,
                )
            )
        if current is not None:
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=channel,
                    action="set_current",
                    current=current,
                )
            )

        for index in range(cycles):
            steps.append(SequenceStep(device_id=device_id, channel=channel, action="output_on"))
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=channel,
                    action="wait",
                    delay_seconds=on_seconds,
                )
            )
            steps.append(SequenceStep(device_id=device_id, channel=channel, action="output_off"))
            if off_seconds > 0 or index < cycles - 1:
                steps.append(
                    SequenceStep(
                        device_id=device_id,
                        channel=channel,
                        action="wait",
                        delay_seconds=off_seconds,
                    )
                )

        return SequencePlan(
            name=f"{device_id}_{channel}_cycle_{cycles}",
            steps=steps,
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
        self._validate_cycles(cycles)
        steps: list[SequenceStep] = []

        if lead_voltage is not None:
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lead_channel,
                    action="set_voltage",
                    voltage=lead_voltage,
                )
            )
        if lead_current is not None:
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lead_channel,
                    action="set_current",
                    current=lead_current,
                )
            )
        if lag_voltage is not None:
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lag_channel,
                    action="set_voltage",
                    voltage=lag_voltage,
                )
            )
        if lag_current is not None:
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lag_channel,
                    action="set_current",
                    current=lag_current,
                )
            )

        for index in range(cycles):
            steps.append(SequenceStep(device_id=device_id, channel=lead_channel, action="output_on"))
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lead_channel,
                    action="wait",
                    delay_seconds=delay_seconds,
                )
            )
            steps.append(SequenceStep(device_id=device_id, channel=lag_channel, action="output_on"))
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lag_channel,
                    action="wait",
                    delay_seconds=hold_seconds,
                )
            )
            steps.append(SequenceStep(device_id=device_id, channel=lag_channel, action="output_off"))
            steps.append(
                SequenceStep(
                    device_id=device_id,
                    channel=lag_channel,
                    action="wait",
                    delay_seconds=delay_seconds,
                )
            )
            steps.append(SequenceStep(device_id=device_id, channel=lead_channel, action="output_off"))
            if rest_seconds > 0 or index < cycles - 1:
                steps.append(
                    SequenceStep(
                        device_id=device_id,
                        channel=lead_channel,
                        action="wait",
                        delay_seconds=rest_seconds,
                    )
                )

        return SequencePlan(
            name=f"{device_id}_{lead_channel}_{lag_channel}_staggered_{cycles}",
            steps=steps,
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
