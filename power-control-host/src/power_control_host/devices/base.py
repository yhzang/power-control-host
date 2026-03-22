from __future__ import annotations

from abc import ABC, abstractmethod
from logging import getLogger

from power_control_host.models import TelemetrySample
from power_control_host.settings import DeviceConfig
from power_control_host.transports.base import BaseTransport


class PowerSupplyDevice(ABC):
    def __init__(self, config: DeviceConfig, transport: BaseTransport) -> None:
        self.config = config
        self.transport = transport
        self.logger = getLogger(f"{self.__class__.__name__}.{config.id}")

    def connect(self) -> None:
        self.transport.connect()
        self.logger.info("connected")

    def disconnect(self) -> None:
        self.transport.disconnect()
        self.logger.info("disconnected")

    def identify(self) -> str:
        return self.transport.query("*IDN?")

    @abstractmethod
    def set_voltage(self, channel: str, value: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_current(self, channel: str, value: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def output_on(self, channel: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def output_off(self, channel: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_measurement(self, channel: str) -> TelemetrySample:
        raise NotImplementedError

