from __future__ import annotations

from power_control_host import discovery
from power_control_host.discovery import DiscoveredDevice, devices_to_yaml


def test_scan_subnet_uses_default_odp_and_psw_ports(monkeypatch) -> None:
    probes: list[tuple[str, int, int]] = []

    def fake_probe_idn(host: str, port: int, timeout_ms: int):
        probes.append((host, port, timeout_ms))
        return None

    monkeypatch.setattr(discovery, "_probe_idn", fake_probe_idn)

    result = discovery.scan_subnet(
        "192.168.10",
        timeout_ms=123,
        workers=1,
    )

    assert result == []
    assert ("192.168.10.1", 4196, 123) in probes
    assert ("192.168.10.1", 2268, 123) in probes
    assert ("192.168.10.254", 4196, 123) in probes
    assert ("192.168.10.254", 2268, 123) in probes


def test_scan_subnet_uses_custom_odp_and_psw_ports(monkeypatch) -> None:
    probes: list[tuple[str, int]] = []

    def fake_probe_idn(host: str, port: int, timeout_ms: int):
        probes.append((host, port))
        return None

    monkeypatch.setattr(discovery, "_probe_idn", fake_probe_idn)

    result = discovery.scan_subnet(
        "192.168.10",
        workers=1,
        odp_port=5001,
        psw_port=5002,
    )

    assert result == []
    assert ("192.168.10.1", 5001) in probes
    assert ("192.168.10.1", 5002) in probes
    assert ("192.168.10.1", 4196) not in probes
    assert ("192.168.10.1", 2268) not in probes


def test_parse_idn_respects_custom_device_ports() -> None:
    odp_counter: dict[str, int] = {}
    psw_counter: dict[str, int] = {}

    odp = discovery._parse_idn(
        "192.168.10.10",
        5001,
        "OWON,ODP3012,24320076,FV:V3.9.0",
        odp_counter,
        psw_counter,
        odp_port=5001,
        psw_port=5002,
    )
    psw = discovery._parse_idn(
        "192.168.10.20",
        5002,
        "GW-INSTEK,PSW30-72,GEW161978,02.53.20220419",
        odp_counter,
        psw_counter,
        odp_port=5001,
        psw_port=5002,
    )

    assert odp is not None
    assert odp.vendor == "owon"
    assert odp.port == 5001
    assert odp.suggested_channels == ["CH1", "CH2"]
    assert psw is not None
    assert psw.vendor == "gwinstek"
    assert psw.port == 5002
    assert psw.suggested_channels == ["OUT"]


def test_parse_idn_rejects_vendor_on_wrong_custom_port() -> None:
    result = discovery._parse_idn(
        "192.168.10.10",
        4196,
        "OWON,ODP3012,24320076,FV:V3.9.0",
        {},
        {},
        odp_port=5001,
        psw_port=5002,
    )

    assert result is None


def test_devices_to_yaml_uses_actual_discovered_port() -> None:
    yaml_text = devices_to_yaml(
        [
            DiscoveredDevice(
                host="192.168.10.23",
                port=5001,
                idn="OWON,ODP3012,24320076,FV:V3.9.0",
                vendor="owon",
                model="ODP3012",
                suggested_id="odp_01",
                suggested_channels=["CH1", "CH2"],
            )
        ]
    )

    assert "host: 192.168.10.23" in yaml_text
    assert "port: 5001" in yaml_text
