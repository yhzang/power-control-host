from __future__ import annotations

from abc import ABC, abstractmethod

from power_control_host.settings import TransportConfig


class BaseTransport(ABC):
    def __init__(self, config: TransportConfig) -> None:
        self.config = config
        self.connected = False

    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def write(self, command: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(self, command: str) -> str:
        raise NotImplementedError

