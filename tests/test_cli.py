from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from power_control_host.models import ChannelCycleSpec, RelativeChannelSpec, SequencePlan
from power_control_host.ui import cli
from power_control_host.ui.cli_parsing import (
    parse_parallel_channel_spec,
    parse_relative_channel_spec,
)


class _FakeSequenceService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def build_parallel_channel_cycle_plan(self, **kwargs) -> SequencePlan:
        self.calls.append(("build_parallel", kwargs))
        return SequencePlan(name="parallel_plan", steps=[])

    def build_staggered_channel_cycle_plan(self, **kwargs) -> SequencePlan:
        self.calls.append(("build_staggered", kwargs))
        return SequencePlan(name="staggered_plan", steps=[])

    def execute_plan(self, plan: SequencePlan, *, log_path: str):
        self.calls.append(("execute", {"plan": plan, "log_path": log_path}))
        return []


def test_parse_parallel_channel_spec_success() -> None:
    spec = parse_parallel_channel_spec("CH1:on=10,off=5,cycles=3,voltage=12,current=1")

    assert spec == ChannelCycleSpec(
        channel="CH1",
        on_seconds=10.0,
        off_seconds=5.0,
        cycles=3,
        voltage=12.0,
        current=1.0,
    )


def test_parse_relative_channel_spec_supports_root_defaults() -> None:
    spec = parse_relative_channel_spec("CH1")

    assert spec == RelativeChannelSpec(
        channel="CH1",
        reference_channel=None,
        on_delay_seconds=0.0,
        off_advance_seconds=0.0,
        voltage=None,
        current=None,
    )


def test_parse_parallel_channel_spec_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="未知参数"):
        parse_parallel_channel_spec("CH1:on=10,off=5,cycles=3,bad=1")


def test_run_parallel_cycle_cli_dispatches_to_sequence_service(monkeypatch, capsys) -> None:
    fake_sequence_service = _FakeSequenceService()
    fake_app = SimpleNamespace(sequence_service=fake_sequence_service)

    monkeypatch.setattr(cli, "create_app", lambda _path: fake_app)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "power-control-host",
            "run-parallel-cycle",
            "--device",
            "odp_01",
            "--channel-spec",
            "CH1:on=10,off=5,cycles=3,voltage=12",
            "--channel-spec",
            "CH2:on=8,off=2,cycles=2,current=1",
        ],
    )

    result = cli.main()

    assert result == 0
    assert fake_sequence_service.calls[0][0] == "build_parallel"
    assert fake_sequence_service.calls[0][1]["device_id"] == "odp_01"
    assert fake_sequence_service.calls[0][1]["channel_specs"] == [
        ChannelCycleSpec(channel="CH1", on_seconds=10.0, off_seconds=5.0, cycles=3, voltage=12.0, current=None),
        ChannelCycleSpec(channel="CH2", on_seconds=8.0, off_seconds=2.0, cycles=2, voltage=None, current=1.0),
    ]
    assert fake_sequence_service.calls[1][0] == "execute"
    assert fake_sequence_service.calls[1][1]["log_path"].startswith("sequence_logs/parallel_plan_")

    output = capsys.readouterr().out
    assert "plan_name: parallel_plan" in output


def test_run_staggered_cycle_cli_keeps_backward_compatible_entrypoint(monkeypatch, capsys) -> None:
    fake_sequence_service = _FakeSequenceService()
    fake_app = SimpleNamespace(sequence_service=fake_sequence_service)

    monkeypatch.setattr(cli, "create_app", lambda _path: fake_app)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "power-control-host",
            "run-staggered-cycle",
            "--device",
            "odp_01",
            "--lead-channel",
            "CH1",
            "--lag-channel",
            "CH2",
            "--delay-seconds",
            "5",
            "--hold-seconds",
            "3",
            "--rest-seconds",
            "2",
            "--cycles",
            "4",
        ],
    )

    result = cli.main()

    assert result == 0
    assert fake_sequence_service.calls[0] == (
        "build_staggered",
        {
            "device_id": "odp_01",
            "lead_channel": "CH1",
            "lag_channel": "CH2",
            "delay_seconds": 5.0,
            "hold_seconds": 3.0,
            "rest_seconds": 2.0,
            "cycles": 4,
            "lead_voltage": None,
            "lead_current": None,
            "lag_voltage": None,
            "lag_current": None,
        },
    )
    assert fake_sequence_service.calls[1][0] == "execute"

    output = capsys.readouterr().out
    assert "plan_name: staggered_plan" in output


def test_scan_devices_cli_passes_custom_ports(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_scan_subnet(subnet: str, **kwargs):
        captured["subnet"] = subnet
        captured.update(kwargs)
        return []

    monkeypatch.setattr(cli, "scan_subnet", fake_scan_subnet)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "power-control-host",
            "scan-devices",
            "--subnet",
            "192.168.10",
            "--timeout-ms",
            "1500",
            "--workers",
            "8",
            "--odp-port",
            "5001",
            "--psw-port",
            "5002",
        ],
    )

    result = cli.main()

    assert result == 0
    assert captured == {
        "subnet": "192.168.10",
        "timeout_ms": 1500,
        "workers": 8,
        "odp_port": 5001,
        "psw_port": 5002,
    }

    output = capsys.readouterr().out
    assert "ODP port=5001" in output
    assert "PSW port=5002" in output
