"""device_pool.py — 多设备连接池。

管理多个 PowerSupplyDevice 的持久连接，避免在执行时序时频繁断开/重连带来的延迟。
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from power_control_host.devices.base import PowerSupplyDevice
    from power_control_host.services.device_service import DeviceService

logger = logging.getLogger(__name__)


class DeviceConnectionPool:
    """管理多个设备的持久 TCP 连接，供多设备时序执行引擎使用。

    Args:
        device_service: 提供设备对象查找能力的服务实例。

    Usage::

        pool = DeviceConnectionPool(device_service)
        with pool.managed_connections(["odp_01", "odp_02"]):
            dev = pool.get_device("odp_01")
            dev.output_on("CH1")
    """

    def __init__(self, device_service: DeviceService) -> None:
        self.device_service = device_service
        self._connected: dict[str, PowerSupplyDevice] = {}

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def connect_devices(self, device_ids: list[str]) -> None:
        """预连接指定设备列表；已连接的设备跳过。

        Args:
            device_ids: 需要连接的设备 ID 列表，与 YAML 配置中的 id 字段对应。

        Raises:
            ValueError: 指定的 device_id 在配置中不存在。
            OSError: 网络连接失败。
        """
        for device_id in device_ids:
            if device_id in self._connected:
                continue
            device = self.device_service.get_device(device_id)
            device.connect()
            self._connected[device_id] = device
            logger.debug("pool: connected %s", device_id)

    def get_device(self, device_id: str) -> PowerSupplyDevice:
        """返回已连接的设备实例。

        Args:
            device_id: 目标设备 ID。

        Raises:
            KeyError: 设备尚未通过 connect_devices() 加入连接池。
        """
        if device_id not in self._connected:
            raise KeyError(
                f"设备 {device_id} 未在连接池中，请先调用 connect_devices()。"
            )
        return self._connected[device_id]

    def disconnect_all(self) -> None:
        """断开连接池中所有设备；单个设备断开异常不影响其他设备。"""
        for device_id, device in list(self._connected.items()):
            try:
                device.disconnect()
                logger.debug("pool: disconnected %s", device_id)
            except Exception:  # noqa: BLE001
                logger.warning("pool: 断开设备 %s 时发生异常，已忽略。", device_id, exc_info=True)
        self._connected.clear()

    @contextmanager
    def managed_connections(
        self, device_ids: list[str]
    ) -> Generator[DeviceConnectionPool, None, None]:
        """上下文管理器：自动连接并在退出时断开所有设备连接。

        Args:
            device_ids: 需要连接的设备 ID 列表。

        Yields:
            self — 本连接池实例，可直接调用 get_device()。
        """
        try:
            self.connect_devices(device_ids)
            yield self
        finally:
            self.disconnect_all()
