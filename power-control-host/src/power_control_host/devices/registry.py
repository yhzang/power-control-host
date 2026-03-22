from __future__ import annotations

from power_control_host.devices.odp import OdpPowerSupply
from power_control_host.devices.psw import PswPowerSupply
from power_control_host.models import DeviceVendor, TransportType
from power_control_host.settings import DeviceConfig
from power_control_host.transports.base import BaseTransport
from power_control_host.transports.serial_transport import SerialTransport
from power_control_host.transports.socket_transport import SocketTransport
from power_control_host.transports.visa_transport import VisaTransport


def build_transport(config: DeviceConfig) -> BaseTransport:
    if config.transport.type == TransportType.VISA:
        return VisaTransport(config.transport)
    if config.transport.type == TransportType.SOCKET:
        return SocketTransport(config.transport)
    if config.transport.type == TransportType.SERIAL:
        return SerialTransport(config.transport)
    raise ValueError(f"不支持的传输类型: {config.transport.type}")


def build_device(config: DeviceConfig):
    transport = build_transport(config)
    if config.vendor == DeviceVendor.OWON:
        return OdpPowerSupply(config, transport)
    if config.vendor == DeviceVendor.GWINSTEK:
        return PswPowerSupply(config, transport)
    raise ValueError(f"未知设备厂商，无法创建驱动: {config.vendor}")

