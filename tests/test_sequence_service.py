from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from power_control_host.models import ChannelCycleSpec, RelativeChannelSpec, SequencePlan
from power_control_host.services.sequence_service import SequenceService


class _FakeDeviceService:
    def __init__(self, channels: tuple[str, ...] = ("CH1", "CH2", "CH3")) -> None:
        self._device = SimpleNamespace(
            config=SimpleNamespace(
                id="odp_01",
                logical_channels=list(channels),
            )
        )

    def get_device(self, device_id: str):
        if device_id != self._device.config.id:
            raise ValueError(f"未找到设备: {device_id}")
        return self._device

    def get_logical_channels(self, device_id: str) -> list[str]:
        if device_id != self._device.config.id:
            raise ValueError(f"未找到设备: {device_id}")
        return list(self._device.config.logical_channels)


def _make_service(channels: tuple[str, ...] = ("CH1", "CH2", "CH3")) -> SequenceService:
    return SequenceService(
        _FakeDeviceService(channels),
        Path("runtime"),
        sleep_fn=lambda _: None,
    )


def _step_signature(plan) -> list[tuple[str, str, float, float | None, float | None]]:
    return [
        (
            step.action,
            step.channel,
            step.delay_seconds,
            step.voltage,
            step.current,
        )
        for step in plan.steps
    ]


def test_parallel_single_channel_matches_existing_cycle_plan() -> None:
    service = _make_service(("CH1", "CH2"))

    legacy_plan = service.build_single_channel_cycle_plan(
        device_id="odp_01",
        channel="CH1",
        on_seconds=2.0,
        off_seconds=1.0,
        cycles=2,
        voltage=12.0,
    )
    parallel_plan = service.build_parallel_channel_cycle_plan(
        device_id="odp_01",
        channel_specs=[
            ChannelCycleSpec(
                channel="CH1",
                on_seconds=2.0,
                off_seconds=1.0,
                cycles=2,
                voltage=12.0,
            )
        ],
    )

    assert _step_signature(legacy_plan) == _step_signature(parallel_plan)


def test_parallel_cycle_merges_multi_channel_timeline_in_stable_order() -> None:
    service = _make_service(("CH1", "CH2"))

    plan = service.build_parallel_channel_cycle_plan(
        device_id="odp_01",
        channel_specs=[
            ChannelCycleSpec(channel="CH1", on_seconds=2.0, off_seconds=1.0, cycles=2, voltage=12.0),
            ChannelCycleSpec(channel="CH2", on_seconds=1.0, off_seconds=1.0, cycles=2, current=1.0),
        ],
    )

    assert _step_signature(plan) == [
        ("set_voltage", "CH1", 0.0, 12.0, None),
        ("set_current", "CH2", 0.0, None, 1.0),
        ("output_on", "CH1", 0.0, None, None),
        ("output_on", "CH2", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH2", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH1", 0.0, None, None),
        ("output_on", "CH2", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH2", 0.0, None, None),
        ("output_on", "CH1", 0.0, None, None),
        ("wait", "*", 2.0, None, None),
        ("output_off", "CH1", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
    ]


def test_parallel_cycle_supports_three_channels() -> None:
    service = _make_service(("CH1", "CH2", "CH3"))

    plan = service.build_parallel_channel_cycle_plan(
        device_id="odp_01",
        channel_specs=[
            ChannelCycleSpec(channel="CH1", on_seconds=1.0, off_seconds=0.0, cycles=1),
            ChannelCycleSpec(channel="CH2", on_seconds=2.0, off_seconds=0.0, cycles=1),
            ChannelCycleSpec(channel="CH3", on_seconds=3.0, off_seconds=0.0, cycles=1),
        ],
    )

    assert _step_signature(plan) == [
        ("output_on", "CH1", 0.0, None, None),
        ("output_on", "CH2", 0.0, None, None),
        ("output_on", "CH3", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH1", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH2", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH3", 0.0, None, None),
    ]


def test_relative_cycle_builds_two_channel_later_on_earlier_off_timeline() -> None:
    service = _make_service(("CH1", "CH2"))

    plan = service.build_relative_channel_cycle_plan(
        device_id="odp_01",
        on_seconds=13.0,
        off_seconds=2.0,
        cycles=1,
        channel_specs=[
            RelativeChannelSpec(channel="CH1"),
            RelativeChannelSpec(
                channel="CH2",
                reference_channel="CH1",
                on_delay_seconds=5.0,
                off_advance_seconds=5.0,
            ),
        ],
    )

    assert _step_signature(plan) == [
        ("output_on", "CH1", 0.0, None, None),
        ("wait", "*", 5.0, None, None),
        ("output_on", "CH2", 0.0, None, None),
        ("wait", "*", 3.0, None, None),
        ("output_off", "CH2", 0.0, None, None),
        ("wait", "*", 5.0, None, None),
        ("output_off", "CH1", 0.0, None, None),
        ("wait", "*", 2.0, None, None),
    ]


def test_relative_cycle_supports_three_channel_branch_references() -> None:
    service = _make_service(("CH1", "CH2", "CH3"))

    plan = service.build_relative_channel_cycle_plan(
        device_id="odp_01",
        on_seconds=10.0,
        off_seconds=1.0,
        cycles=1,
        channel_specs=[
            RelativeChannelSpec(channel="CH1"),
            RelativeChannelSpec(channel="CH2", reference_channel="CH1", on_delay_seconds=2.0, off_advance_seconds=1.0),
            RelativeChannelSpec(channel="CH3", reference_channel="CH1", on_delay_seconds=4.0, off_advance_seconds=0.0),
        ],
    )

    assert _step_signature(plan) == [
        ("output_on", "CH1", 0.0, None, None),
        ("wait", "*", 2.0, None, None),
        ("output_on", "CH2", 0.0, None, None),
        ("wait", "*", 2.0, None, None),
        ("output_on", "CH3", 0.0, None, None),
        ("wait", "*", 5.0, None, None),
        ("output_off", "CH2", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH1", 0.0, None, None),
        ("output_off", "CH3", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
    ]


def test_relative_cycle_supports_chain_references() -> None:
    service = _make_service(("CH1", "CH2", "CH3"))

    plan = service.build_relative_channel_cycle_plan(
        device_id="odp_01",
        on_seconds=10.0,
        off_seconds=1.0,
        cycles=1,
        channel_specs=[
            RelativeChannelSpec(channel="CH1"),
            RelativeChannelSpec(channel="CH2", reference_channel="CH1", on_delay_seconds=1.0, off_advance_seconds=1.0),
            RelativeChannelSpec(channel="CH3", reference_channel="CH2", on_delay_seconds=2.0, off_advance_seconds=1.0),
        ],
    )

    assert _step_signature(plan) == [
        ("output_on", "CH1", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_on", "CH2", 0.0, None, None),
        ("wait", "*", 2.0, None, None),
        ("output_on", "CH3", 0.0, None, None),
        ("wait", "*", 5.0, None, None),
        ("output_off", "CH3", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH2", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
        ("output_off", "CH1", 0.0, None, None),
        ("wait", "*", 1.0, None, None),
    ]


@pytest.mark.parametrize(
    ("builder", "message"),
    [
        (
            lambda service: service.build_parallel_channel_cycle_plan(
                device_id="odp_01",
                channel_specs=[
                    ChannelCycleSpec(channel="CH1", on_seconds=1.0, off_seconds=0.0, cycles=1),
                    ChannelCycleSpec(channel="CH1", on_seconds=2.0, off_seconds=0.0, cycles=1),
                ],
            ),
            "重复通道",
        ),
        (
            lambda service: service.build_parallel_channel_cycle_plan(
                device_id="odp_01",
                channel_specs=[
                    ChannelCycleSpec(channel="CH9", on_seconds=1.0, off_seconds=0.0, cycles=1),
                ],
            ),
            "未在设备配置中声明",
        ),
        (
            lambda service: service.build_relative_channel_cycle_plan(
                device_id="odp_01",
                on_seconds=5.0,
                off_seconds=1.0,
                cycles=1,
                channel_specs=[
                    RelativeChannelSpec(channel="CH1", reference_channel="CH2"),
                ],
            ),
            "不存在的参考通道",
        ),
        (
            lambda service: service.build_relative_channel_cycle_plan(
                device_id="odp_01",
                on_seconds=5.0,
                off_seconds=1.0,
                cycles=1,
                channel_specs=[
                    RelativeChannelSpec(channel="CH1", reference_channel="CH2"),
                    RelativeChannelSpec(channel="CH2", reference_channel="CH1"),
                ],
            ),
            "循环引用",
        ),
        (
            lambda service: service.build_parallel_channel_cycle_plan(
                device_id="odp_01",
                channel_specs=[
                    ChannelCycleSpec(channel="CH1", on_seconds=-1.0, off_seconds=0.0, cycles=1),
                ],
            ),
            "大于或等于 0",
        ),
        (
            lambda service: service.build_relative_channel_cycle_plan(
                device_id="odp_01",
                on_seconds=5.0,
                off_seconds=1.0,
                cycles=1,
                channel_specs=[
                    RelativeChannelSpec(channel="CH1"),
                    RelativeChannelSpec(channel="CH2", reference_channel="CH1", on_delay_seconds=3.0, off_advance_seconds=2.0),
                ],
            ),
            "有效导通时长必须大于 0",
        ),
    ],
)
def test_sequence_service_validation_errors(builder, message: str) -> None:
    service = _make_service(("CH1", "CH2", "CH3"))

    with pytest.raises(ValueError, match=message):
        builder(service)


def test_build_staggered_channel_cycle_plan_maps_to_relative_cycle(monkeypatch) -> None:
    service = _make_service(("CH1", "CH2"))
    captured: dict[str, object] = {}

    def fake_build_relative_channel_cycle_plan(**kwargs) -> SequencePlan:
        captured.update(kwargs)
        return SequencePlan(name="mapped_plan", steps=[])

    monkeypatch.setattr(service, "build_relative_channel_cycle_plan", fake_build_relative_channel_cycle_plan)

    plan = service.build_staggered_channel_cycle_plan(
        device_id="odp_01",
        lead_channel="CH1",
        lag_channel="CH2",
        delay_seconds=5.0,
        hold_seconds=3.0,
        rest_seconds=2.0,
        cycles=4,
        lead_voltage=12.0,
        lag_current=1.5,
    )

    assert plan.name == "mapped_plan"
    assert captured["device_id"] == "odp_01"
    assert captured["on_seconds"] == 13.0
    assert captured["off_seconds"] == 2.0
    assert captured["cycles"] == 4
    assert captured["name"] == "odp_01_CH1_CH2_staggered_4"

    channel_specs = captured["channel_specs"]
    assert channel_specs == [
        RelativeChannelSpec(channel="CH1", voltage=12.0, current=None),
        RelativeChannelSpec(
            channel="CH2",
            reference_channel="CH1",
            on_delay_seconds=5.0,
            off_advance_seconds=5.0,
            voltage=None,
            current=1.5,
        ),
    ]
