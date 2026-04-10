from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

ODP_PORT = 4196
PSW_PORT = 2268
_WRITE_TERM = b"\n"
_READ_TERM = b"\n"


@dataclass
class DiscoveredDevice:
    host: str
    port: int
    idn: str
    vendor: str
    model: str
    suggested_id: str
    suggested_channels: list[str] = field(default_factory=list)


def scan_subnet(
    subnet: str = "192.168.1",
    *,
    timeout_ms: int = 1000,
    workers: int = 100,
    odp_port: int = ODP_PORT,
    psw_port: int = PSW_PORT,
) -> list[DiscoveredDevice]:
    """Scan all .1–.254 addresses in subnet for ODP and PSW devices."""
    probes: list[tuple[str, int]] = []
    for last in range(1, 255):
        host = f"{subnet}.{last}"
        probes.append((host, odp_port))
        probes.append((host, psw_port))

    found: list[DiscoveredDevice] = []
    odp_counter: dict[str, int] = {}
    psw_counter: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_probe_idn, host, port, timeout_ms): (host, port) for host, port in probes}
        for future in as_completed(futures):
            host, port = futures[future]
            idn = future.result()
            if idn is None:
                continue
            device = _parse_idn(
                host,
                port,
                idn,
                odp_counter,
                psw_counter,
                odp_port=odp_port,
                psw_port=psw_port,
            )
            if device is not None:
                found.append(device)

    found.sort(key=lambda d: (d.host, d.port))
    return found


def _probe_idn(host: str, port: int, timeout_ms: int) -> str | None:
    timeout = timeout_ms / 1000.0
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"*IDN?" + _WRITE_TERM)
            response = b""
            sock.settimeout(timeout)
            while True:
                try:
                    chunk = sock.recv(4096)
                except (socket.timeout, OSError):
                    break
                if not chunk:
                    break
                response += chunk
                if _READ_TERM in response:
                    break
        text = response.decode(errors="ignore").strip()
        return text if text else None
    except OSError:
        return None


def _parse_idn(
    host: str,
    port: int,
    idn: str,
    odp_counter: dict[str, int],
    psw_counter: dict[str, int],
    *,
    odp_port: int = ODP_PORT,
    psw_port: int = PSW_PORT,
) -> DiscoveredDevice | None:
    parts = [p.strip() for p in idn.split(",")]
    if len(parts) < 2:
        return None

    vendor_str = parts[0].upper()
    model = parts[1] if len(parts) > 1 else "UNKNOWN"

    if "OWON" in vendor_str and port == odp_port:
        n = odp_counter.get(model, 0) + 1
        odp_counter[model] = n
        suggested_id = f"odp_{n:02d}"
        channels = _odp_channels(model)
        return DiscoveredDevice(
            host=host,
            port=port,
            idn=idn,
            vendor="owon",
            model=model,
            suggested_id=suggested_id,
            suggested_channels=channels,
        )

    if "GW-INSTEK" in vendor_str or "GWINSTEK" in vendor_str:
        if port == psw_port:
            n = psw_counter.get(model, 0) + 1
            psw_counter[model] = n
            suggested_id = f"psw_{n:02d}"
            return DiscoveredDevice(
                host=host,
                port=port,
                idn=idn,
                vendor="gwinstek",
                model=model,
                suggested_id=suggested_id,
                suggested_channels=["OUT"],
            )

    return None


def _odp_channels(model: str) -> list[str]:
    m = model.upper()
    if "3032" in m or "3033" in m:
        return ["CH1", "CH2", "CH3"]
    # ODP3012 and unknown variants default to 2 channels
    return ["CH1", "CH2"]


def devices_to_yaml(devices: list[DiscoveredDevice]) -> str:
    lines: list[str] = ["devices:"]
    for d in devices:
        lines.append(f"  - id: {d.suggested_id}")
        lines.append(f"    vendor: {d.vendor}")
        lines.append(f"    model: {d.model}")
        lines.append("    transport:")
        lines.append("      type: socket")
        lines.append(f"      host: {d.host}")
        lines.append(f"      port: {d.port}")
        lines.append("      timeout_ms: 3000")
        lines.append("      write_termination: \"\\n\"")
        lines.append("      read_termination: \"\\n\"")
        lines.append("    logical_channels:")
        for ch in d.suggested_channels:
            lines.append(f"      - {ch}")
        lines.append(f"    notes: \"auto-discovered from {d.host}:{d.port} | IDN: {d.idn}\"")
    return "\n".join(lines) + "\n"
