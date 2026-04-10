"""test_multi_device_timing.py — 多设备时序功能单元测试。

覆盖：
- 数据模型构造（TimingNode、MultiDeviceTimingSpec）
- build_multi_device_timing_plan() 单/多设备场景
- _normalize_timing_nodes() 验证逻辑
- execute_plan_with_pool() 多设备执行 + 取消
- 配置持久化（save/load 往返测试）
- DeviceService 序列号解析
- DeviceConnectionPool 连接池
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from power_control_host.models import (
    MultiDeviceTimingSpec,
    SequencePlan,
    TelemetrySample,
    TimingNode,
)
from power_control_host.services.device_pool import DeviceConnectionPool
from power_control_host.services.device_service import DeviceService
from power_control_host.services.sequence_service import SequenceService
from power_control_host.services.timing_config import load_timing_config, save_timing_config
from power_control_host.settings import (
    AppSettings,
    AppDirectories,
    DeviceConfig,
    TransportConfig,
)
from power_control_host.models import DeviceVendor, TransportType


# ---------------------------------------------------------------------------
# 测试夹具（Fixtures）
# ---------------------------------------------------------------------------


def _make_device_config(device_id: str, channels: list[str]) -> DeviceConfig:
    return DeviceConfig(
        id=device_id,
        vendor=DeviceVendor.OWON,
        model="ODP3012",
        transport=TransportConfig(
            type=TransportType.SOCKET,
            host="192.168.1.1",
            port=4196,
        ),
        logical_channels=channels,
    )


def _make_settings(device_ids_channels: dict[str, list[str]], tmp_path: Path) -> AppSettings:
    devices = [
        _make_device_config(device_id, channels)
        for device_id, channels in device_ids_channels.items()
    ]
    return AppSettings(
        name="test",
        environment="test",
        base_dir=tmp_path,
        directories=AppDirectories(
            log_dir=tmp_path / "logs",
            export_dir=tmp_path / "exports",
            runtime_dir=tmp_path / "runtime",
        ),
        devices=devices,
    )


def _make_mock_device(device_id: str, channels: list[str]):
    """创建 mock PowerSupplyDevice，connect/disconnect/identify 均为 no-op。"""
    config = _make_device_config(device_id, channels)
    mock = MagicMock()
    mock.config = config
    mock.connect = MagicMock()
    mock.disconnect = MagicMock()
    mock.identify = MagicMock(return_value=f"OWON,ODP3012,SN_{device_id},FV:V3.9.0")
    mock.set_voltage = MagicMock()
    mock.set_current = MagicMock()
    mock.output_on = MagicMock()
    mock.output_off = MagicMock()
    mock.read_measurement = MagicMock(
        return_value=TelemetrySample(device_id=device_id, channel=channels[0])
    )
    return mock


def _make_service(
    device_ids_channels: dict[str, list[str]],
    tmp_path: Path,
    mock_devices: dict[str, Any] | None = None,
) -> SequenceService:
    device_service = MagicMock(spec=DeviceService)

    _mock_devices = mock_devices or {
        did: _make_mock_device(did, chs)
        for did, chs in device_ids_channels.items()
    }

    def get_device(device_id: str):
        if device_id not in _mock_devices:
            raise ValueError(f"未找到设备: {device_id}")
        return _mock_devices[device_id]

    def get_logical_channels(device_id: str) -> list[str]:
        return _mock_devices[device_id].config.logical_channels

    device_service.get_device.side_effect = get_device
    device_service.get_logical_channels.side_effect = get_logical_channels

    return SequenceService(
        device_service=device_service,
        runtime_dir=tmp_path / "runtime",
        sleep_fn=lambda s: None,  # 测试中不实际 sleep
    )


# ---------------------------------------------------------------------------
# 阶段1：数据模型
# ---------------------------------------------------------------------------


class TestTimingNodeModel:
    def test_default_values(self):
        node = TimingNode(
            device_id="odp_01",
            channel="CH1",
            on_time_seconds=0.0,
            off_time_seconds=10.0,
        )
        assert node.enabled is True
        assert node.voltage is None
        assert node.current is None
        assert node.description == ""

    def test_custom_values(self):
        node = TimingNode(
            device_id="psw_01",
            channel="OUT",
            on_time_seconds=5.0,
            off_time_seconds=25.0,
            voltage=24.0,
            current=2.0,
            enabled=False,
            description="测试节点",
        )
        assert node.enabled is False
        assert node.voltage == 24.0


class TestMultiDeviceTimingSpecModel:
    def test_default_values(self):
        spec = MultiDeviceTimingSpec(name="test", nodes=[])
        assert spec.cycles == 1
        assert spec.cycle_period_seconds == 0.0


# ---------------------------------------------------------------------------
# 阶段2：多设备计划构建器
# ---------------------------------------------------------------------------


class TestBuildMultiDevicePlan:
    def test_single_device_two_channels(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1", "CH2"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="two_ch",
            cycles=2,
            nodes=[
                TimingNode("odp_01", "CH1", 0.0, 10.0),
                TimingNode("odp_01", "CH2", 2.0, 8.0),
            ],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        assert isinstance(plan, SequencePlan)
        assert plan.name == "multi_device_two_ch"
        actions = [(s.action, s.channel) for s in plan.steps]
        # 应包含 output_on/off 动作
        assert ("output_on", "CH1") in actions
        assert ("output_on", "CH2") in actions
        assert ("output_off", "CH1") in actions
        assert ("output_off", "CH2") in actions

    def test_multi_device_single_channel_each(self, tmp_path):
        svc = _make_service(
            {"odp_01": ["CH1"], "odp_02": ["CH1"]}, tmp_path
        )
        spec = MultiDeviceTimingSpec(
            name="two_dev",
            cycles=1,
            nodes=[
                TimingNode("odp_01", "CH1", 0.0, 20.0),
                TimingNode("odp_02", "CH1", 5.0, 15.0),
            ],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        device_ids = {s.device_id for s in plan.steps if s.action != "wait"}
        assert "odp_01" in device_ids
        assert "odp_02" in device_ids

    def test_disabled_nodes_excluded(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1", "CH2"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="disabled",
            cycles=1,
            nodes=[
                TimingNode("odp_01", "CH1", 0.0, 10.0, enabled=True),
                TimingNode("odp_01", "CH2", 0.0, 10.0, enabled=False),
            ],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        active_channels = {s.channel for s in plan.steps if s.action != "wait"}
        assert "CH1" in active_channels
        assert "CH2" not in active_channels

    def test_period_auto_calculated(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="auto_period",
            cycles=1,
            cycle_period_seconds=0.0,  # 自动计算
            nodes=[TimingNode("odp_01", "CH1", 0.0, 30.0)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        # 自动期应以 30s 为周期，最后一步应是 tail wait 到 30s
        wait_steps = [s for s in plan.steps if s.action == "wait"]
        assert wait_steps  # 应有 wait 步骤

    def test_explicit_period_used(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="explicit_period",
            cycles=1,
            cycle_period_seconds=60.0,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 30.0)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        assert plan is not None

    def test_explicit_period_shorter_than_off_time_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="short_period",
            cycles=2,
            cycle_period_seconds=5.0,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0)],
        )
        with pytest.raises(ValueError, match="cycle_period_seconds"):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_negative_period_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="negative_period",
            cycles=1,
            cycle_period_seconds=-1.0,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0)],
        )
        with pytest.raises(ValueError, match="cycle_period_seconds"):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_voltage_current_setpoints_included(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="setpoints",
            cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0, voltage=12.0, current=1.0)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        actions = [s.action for s in plan.steps]
        assert "set_voltage" in actions
        assert "set_current" in actions

    def test_cycles_repeat_correctly(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="multicycle",
            cycles=3,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        on_count = sum(1 for s in plan.steps if s.action == "output_on")
        off_count = sum(1 for s in plan.steps if s.action == "output_off")
        assert on_count == 3
        assert off_count == 3

    def test_all_disabled_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="all_disabled",
            cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0, enabled=False)],
        )
        with pytest.raises(ValueError, match="enabled"):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_zero_cycles_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="zero_cycles", cycles=0,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0)],
        )
        with pytest.raises(ValueError, match="cycles"):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_off_not_greater_than_on_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="bad_timing", cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 10.0, 5.0)],
        )
        with pytest.raises(ValueError, match="off_time_seconds"):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_equal_on_off_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="equal_times", cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 5.0, 5.0)],
        )
        with pytest.raises(ValueError):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_duplicate_device_channel_raises(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="duplicate_node", cycles=1,
            nodes=[
                TimingNode("odp_01", "CH1", 0.0, 10.0),
                TimingNode("odp_01", "ch1", 1.0, 9.0),
            ],
        )
        with pytest.raises(ValueError, match="重复节点"):
            svc.build_multi_device_timing_plan(spec=spec)

    def test_custom_plan_name(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="original", cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec, name="custom_name")
        assert plan.name == "custom_name"


# ---------------------------------------------------------------------------
# 阶段3：连接池
# ---------------------------------------------------------------------------


class TestDeviceConnectionPool:
    def _make_pool(self, device_ids_channels: dict[str, list[str]]):
        mock_devices = {
            did: _make_mock_device(did, chs)
            for did, chs in device_ids_channels.items()
        }
        device_service = MagicMock(spec=DeviceService)
        device_service.get_device.side_effect = lambda did: mock_devices[did]
        pool = DeviceConnectionPool(device_service)
        return pool, mock_devices

    def test_connect_and_get(self):
        pool, mocks = self._make_pool({"odp_01": ["CH1"]})
        pool.connect_devices(["odp_01"])
        device = pool.get_device("odp_01")
        mocks["odp_01"].connect.assert_called_once()
        assert device is mocks["odp_01"]

    def test_already_connected_not_reconnected(self):
        pool, mocks = self._make_pool({"odp_01": ["CH1"]})
        pool.connect_devices(["odp_01"])
        pool.connect_devices(["odp_01"])  # 第二次应跳过
        mocks["odp_01"].connect.assert_called_once()

    def test_disconnect_all(self):
        pool, mocks = self._make_pool({"odp_01": ["CH1"], "odp_02": ["CH1"]})
        pool.connect_devices(["odp_01", "odp_02"])
        pool.disconnect_all()
        mocks["odp_01"].disconnect.assert_called_once()
        mocks["odp_02"].disconnect.assert_called_once()
        # 断开后连接池应清空
        with pytest.raises(KeyError):
            pool.get_device("odp_01")

    def test_get_unconnected_raises(self):
        pool, _ = self._make_pool({"odp_01": ["CH1"]})
        with pytest.raises(KeyError):
            pool.get_device("odp_01")

    def test_managed_connections_context(self):
        pool, mocks = self._make_pool({"odp_01": ["CH1"]})
        with pool.managed_connections(["odp_01"]):
            mocks["odp_01"].connect.assert_called_once()
        mocks["odp_01"].disconnect.assert_called_once()

    def test_managed_connections_disconnect_on_exception(self):
        pool, mocks = self._make_pool({"odp_01": ["CH1"]})
        with pytest.raises(RuntimeError):
            with pool.managed_connections(["odp_01"]):
                raise RuntimeError("test error")
        mocks["odp_01"].disconnect.assert_called_once()


# ---------------------------------------------------------------------------
# 阶段4：执行引擎（execute_plan_with_pool + 取消）
# ---------------------------------------------------------------------------


class TestExecutePlanWithPool:
    def test_basic_execution(self, tmp_path):
        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        spec = MultiDeviceTimingSpec(
            name="basic",
            cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 0.1)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        events = svc.execute_plan_with_pool(plan)
        actions = [e.action for e in events]
        assert "output_on" in actions
        assert "output_off" in actions
        assert "cancelled" not in actions

    def test_cancellation_during_wait(self, tmp_path):
        """取消标志在执行时被设置，应在下一个 wait 步骤退出。"""
        calls = []

        def slow_sleep(seconds: float) -> None:
            calls.append(seconds)
            time.sleep(min(seconds, 0.001))

        svc = _make_service({"odp_01": ["CH1"]}, tmp_path)
        svc.sleep_fn = slow_sleep

        # 构建有较长 wait 的计划
        spec = MultiDeviceTimingSpec(
            name="cancel_test",
            cycles=1,
            cycle_period_seconds=10.0,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 1.0)],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)

        # 在后台线程中取消
        def cancel_after_delay():
            time.sleep(0.05)
            svc.cancel_execution()

        t = threading.Thread(target=cancel_after_delay)
        t.start()
        events = svc.execute_plan_with_pool(plan)
        t.join()

        actions = [e.action for e in events]
        assert "cancelled" in actions

    def test_multi_device_all_devices_used(self, tmp_path):
        svc = _make_service(
            {"odp_01": ["CH1"], "odp_02": ["CH1"]}, tmp_path
        )
        spec = MultiDeviceTimingSpec(
            name="two_dev",
            cycles=1,
            nodes=[
                TimingNode("odp_01", "CH1", 0.0, 0.1),
                TimingNode("odp_02", "CH1", 0.05, 0.15),
            ],
        )
        plan = svc.build_multi_device_timing_plan(spec=spec)
        events = svc.execute_plan_with_pool(plan)
        device_ids = {e.device_id for e in events if e.action != "wait"}
        assert "odp_01" in device_ids
        assert "odp_02" in device_ids


# ---------------------------------------------------------------------------
# 阶段5：设备序列号
# ---------------------------------------------------------------------------


class TestDeviceSerialNumber:
    def test_parse_standard_idn(self):
        serial = DeviceService._parse_serial_number("OWON,ODP3012,24320076,FV:V3.9.0")
        assert serial == "24320076"

    def test_parse_gwinstek_idn(self):
        serial = DeviceService._parse_serial_number("GW-INSTEK,PSW30-72,GEW161978,02.53.20220419")
        assert serial == "GEW161978"

    def test_parse_too_few_fields_returns_empty(self):
        serial = DeviceService._parse_serial_number("OWON,ODP3012")
        assert serial == ""

    def test_parse_empty_string(self):
        serial = DeviceService._parse_serial_number("")
        assert serial == ""

    def test_parse_with_whitespace(self):
        serial = DeviceService._parse_serial_number(" OWON , ODP3012 , 24320076 , FW ")
        assert serial == "24320076"

    def test_get_serial_number_connect_failure_returns_device_id(self, tmp_path):
        service = DeviceService(_make_settings({"odp_01": ["CH1"]}, tmp_path))
        mock_device = _make_mock_device("odp_01", ["CH1"])
        mock_device.connect.side_effect = OSError("offline")
        service.devices = [mock_device]
        assert service.get_device_serial_number("odp_01") == "odp_01"

    def test_list_devices_with_serial_connect_failure_returns_unknown(self, tmp_path):
        service = DeviceService(_make_settings({"odp_01": ["CH1"]}, tmp_path))
        mock_device = _make_mock_device("odp_01", ["CH1"])
        mock_device.connect.side_effect = OSError("offline")
        service.devices = [mock_device]
        assert service.list_devices_with_serial() == [
            {
                "device_id": "odp_01",
                "model": "ODP3012",
                "serial_number": "unknown",
            }
        ]


# ---------------------------------------------------------------------------
# 阶段6：配置持久化
# ---------------------------------------------------------------------------


class TestTimingConfigPersistence:
    def _make_spec(self) -> MultiDeviceTimingSpec:
        return MultiDeviceTimingSpec(
            name="测试时序",
            cycles=5,
            cycle_period_seconds=30.0,
            nodes=[
                TimingNode(
                    device_id="odp_01",
                    channel="CH1",
                    on_time_seconds=0.0,
                    off_time_seconds=20.0,
                    voltage=12.0,
                    current=1.0,
                    enabled=True,
                    description="主电源",
                ),
                TimingNode(
                    device_id="odp_02",
                    channel="CH1",
                    on_time_seconds=5.0,
                    off_time_seconds=15.0,
                    voltage=5.0,
                    enabled=False,
                    description="禁用节点",
                ),
            ],
        )

    def test_save_creates_file(self, tmp_path):
        spec = self._make_spec()
        path = tmp_path / "config.json"
        result_path = save_timing_config(spec, path)
        assert result_path.exists()

    def test_save_is_valid_json(self, tmp_path):
        spec = self._make_spec()
        path = tmp_path / "config.json"
        save_timing_config(spec, path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "测试时序"
        assert len(data["nodes"]) == 2

    def test_roundtrip(self, tmp_path):
        spec = self._make_spec()
        path = tmp_path / "config.json"
        save_timing_config(spec, path)
        loaded = load_timing_config(path)
        assert loaded.name == spec.name
        assert loaded.cycles == spec.cycles
        assert loaded.cycle_period_seconds == spec.cycle_period_seconds
        assert len(loaded.nodes) == len(spec.nodes)
        assert loaded.nodes[0].device_id == "odp_01"
        assert loaded.nodes[0].voltage == 12.0
        assert loaded.nodes[1].enabled is False
        assert loaded.nodes[1].description == "禁用节点"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_timing_config(tmp_path / "nonexistent.json")

    def test_load_invalid_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("NOT JSON", encoding="utf-8")
        with pytest.raises((json.JSONDecodeError, ValueError)):
            load_timing_config(path)

    def test_load_missing_required_field_raises(self, tmp_path):
        path = tmp_path / "no_name.json"
        path.write_text('{"nodes": []}', encoding="utf-8")
        with pytest.raises((KeyError, ValueError)):
            load_timing_config(path)

    def test_save_creates_parent_dirs(self, tmp_path):
        spec = self._make_spec()
        path = tmp_path / "subdir" / "nested" / "config.json"
        save_timing_config(spec, path)
        assert path.exists()

    def test_chinese_description_preserved(self, tmp_path):
        spec = self._make_spec()
        path = tmp_path / "config.json"
        save_timing_config(spec, path)
        loaded = load_timing_config(path)
        assert loaded.nodes[0].description == "主电源"

    def test_optional_voltage_current_none(self, tmp_path):
        spec = MultiDeviceTimingSpec(
            name="no_setpoints",
            cycles=1,
            nodes=[TimingNode("odp_01", "CH1", 0.0, 10.0)],
        )
        path = tmp_path / "config.json"
        save_timing_config(spec, path)
        loaded = load_timing_config(path)
        assert loaded.nodes[0].voltage is None
        assert loaded.nodes[0].current is None
