from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from power_control_host.app import create_app
from power_control_host.devices.odp import OdpPowerSupply
from power_control_host.models import DeviceVendor, TransportType
from power_control_host.settings import DeviceConfig, TransportConfig
from power_control_host.transports.socket_transport import (
    SocketTransport,
    run_socket_command,
)
from power_control_host.transports.visa_transport import (
    list_visa_resources,
    probe_visa_resource,
)
from power_control_host.discovery import devices_to_yaml, scan_subnet
from power_control_host.ui.cli_parsing import (
    parse_parallel_channel_specs,
    parse_relative_channel_specs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reliability power host")
    parser.add_argument(
        "--config",
        default="config/devices.local.yaml",
        help="Path to YAML configuration file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show-plan", help="Show the current development checklist.")
    subparsers.add_parser("check-config", help="Validate config and print a summary.")
    subparsers.add_parser("show-devices", help="Print configured devices.")
    subparsers.add_parser(
        "list-visa-resources",
        help="List VISA resources currently visible on this computer.",
    )

    probe_visa_parser = subparsers.add_parser(
        "probe-visa",
        help="Send *IDN? or a custom command to a raw VISA resource without YAML config.",
    )
    probe_visa_parser.add_argument("--resource", required=True, help="Exact VISA resource string.")
    probe_visa_parser.add_argument("--scpi", default="*IDN?", help="SCPI command to send.")
    probe_visa_parser.add_argument("--timeout-ms", type=int, default=3000, help="Timeout in milliseconds.")

    socket_parser = subparsers.add_parser(
        "socket-scpi",
        help="Send one SCPI command directly to a TCP socket.",
    )
    socket_parser.add_argument("--host", required=True, help="Socket host or device IP.")
    socket_parser.add_argument("--port", required=True, type=int, help="Socket port.")
    socket_parser.add_argument("--scpi", required=True, help="SCPI command to send.")
    socket_parser.add_argument("--timeout-ms", type=int, default=3000, help="Timeout in milliseconds.")
    socket_parser.add_argument(
        "--write-only",
        action="store_true",
        help="Only send the command, do not wait for a response.",
    )

    odp_smoke_parser = subparsers.add_parser(
        "odp-socket-smoke",
        help="Run a guided ODP socket smoke test without YAML config.",
    )
    odp_smoke_parser.add_argument("--host", required=True, help="ODP IP address.")
    odp_smoke_parser.add_argument("--port", required=True, type=int, help="ODP socket port.")
    odp_smoke_parser.add_argument("--channel", default="CH1", help="ODP logical channel.")
    odp_smoke_parser.add_argument("--timeout-ms", type=int, default=3000, help="Timeout in milliseconds.")
    odp_smoke_parser.add_argument("--voltage", type=float, help="Optional voltage setpoint.")
    odp_smoke_parser.add_argument("--current", type=float, help="Optional current setpoint.")
    odp_smoke_parser.add_argument("--output-on", action="store_true", help="Turn output on.")
    odp_smoke_parser.add_argument("--measure", action="store_true", help="Read measurement.")
    odp_smoke_parser.add_argument("--output-off", action="store_true", help="Turn output off at the end.")

    scan_parser = subparsers.add_parser(
        "scan-devices",
        help="Scan subnet for ODP and PSW devices via *IDN? and print results.",
    )
    scan_parser.add_argument(
        "--subnet",
        default="192.168.1",
        help="Subnet prefix to scan, e.g. 192.168.1",
    )
    scan_parser.add_argument(
        "--timeout-ms",
        type=int,
        default=1000,
        help="Per-probe socket timeout in milliseconds.",
    )
    scan_parser.add_argument(
        "--workers",
        type=int,
        default=100,
        help="Concurrent worker threads.",
    )
    scan_parser.add_argument(
        "--emit-yaml",
        action="store_true",
        help="Also print a devices.yaml snippet for the discovered devices.",
    )

    probe_parser = subparsers.add_parser("probe-idn", help="Query *IDN? from one configured device.")
    probe_parser.add_argument("--device", required=True, help="Configured device id.")

    measure_parser = subparsers.add_parser("measure", help="Read voltage/current from one configured device.")
    measure_parser.add_argument("--device", required=True, help="Configured device id.")
    measure_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    set_voltage_parser = subparsers.add_parser("set-voltage", help="Set output voltage on one configured device.")
    set_voltage_parser.add_argument("--device", required=True, help="Configured device id.")
    set_voltage_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")
    set_voltage_parser.add_argument("--value", required=True, type=float, help="Target voltage.")

    set_current_parser = subparsers.add_parser("set-current", help="Set output current on one configured device.")
    set_current_parser.add_argument("--device", required=True, help="Configured device id.")
    set_current_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")
    set_current_parser.add_argument("--value", required=True, type=float, help="Target current.")

    output_on_parser = subparsers.add_parser("output-on", help="Turn output on for one configured device.")
    output_on_parser.add_argument("--device", required=True, help="Configured device id.")
    output_on_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    output_off_parser = subparsers.add_parser("output-off", help="Turn output off for one configured device.")
    output_off_parser.add_argument("--device", required=True, help="Configured device id.")
    output_off_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    cycle_parser = subparsers.add_parser(
        "run-cycle",
        help="Run a single-channel on/off cycle on one configured device.",
    )
    cycle_parser.add_argument("--device", required=True, help="Configured device id.")
    cycle_parser.add_argument("--channel", required=True, help="Logical channel name, for example CH1.")
    cycle_parser.add_argument("--on-seconds", required=True, type=float, help="Output-on duration in seconds.")
    cycle_parser.add_argument("--off-seconds", required=True, type=float, help="Output-off duration in seconds.")
    cycle_parser.add_argument("--cycles", required=True, type=int, help="Cycle count.")
    cycle_parser.add_argument("--voltage", type=float, help="Optional preset voltage before running.")
    cycle_parser.add_argument("--current", type=float, help="Optional preset current before running.")
    cycle_parser.add_argument(
        "--log-file",
        help="Optional CSV log path. Defaults to runtime/sequence_logs/<timestamp>.csv",
    )

    parallel_parser = subparsers.add_parser(
        "run-parallel-cycle",
        help="Run multiple channels from a shared start time, each with its own cycle settings.",
    )
    parallel_parser.add_argument("--device", required=True, help="Configured device id.")
    parallel_parser.add_argument(
        "--channel-spec",
        dest="channel_specs",
        action="append",
        required=True,
        help=(
            "Channel spec in the form CH1:on=10,off=5,cycles=3,voltage=12,current=1. "
            "Repeat this option for each channel."
        ),
    )
    parallel_parser.add_argument(
        "--log-file",
        help="Optional CSV log path. Defaults to runtime/sequence_logs/<timestamp>.csv",
    )

    relative_parser = subparsers.add_parser(
        "run-relative-cycle",
        help="Run multi-channel relative timing with shared group cycle settings.",
    )
    relative_parser.add_argument("--device", required=True, help="Configured device id.")
    relative_parser.add_argument("--on-seconds", required=True, type=float, help="Group on duration.")
    relative_parser.add_argument("--off-seconds", required=True, type=float, help="Group off duration.")
    relative_parser.add_argument("--cycles", required=True, type=int, help="Group cycle count.")
    relative_parser.add_argument(
        "--channel-spec",
        dest="channel_specs",
        action="append",
        required=True,
        help=(
            "Channel spec in the form CH2:ref=CH1,on_delay=5,off_advance=5,voltage=50,current=2. "
            "Repeat this option for each channel."
        ),
    )
    relative_parser.add_argument(
        "--log-file",
        help="Optional CSV log path. Defaults to runtime/sequence_logs/<timestamp>.csv",
    )

    staggered_parser = subparsers.add_parser(
        "run-staggered-cycle",
        help="Run a two-channel delayed cycle with later-on-earlier-off behavior.",
    )
    staggered_parser.add_argument("--device", required=True, help="Configured device id.")
    staggered_parser.add_argument("--lead-channel", required=True, help="First channel to turn on.")
    staggered_parser.add_argument("--lag-channel", required=True, help="Second channel to turn on after delay.")
    staggered_parser.add_argument("--delay-seconds", required=True, type=float, help="Delay between channels.")
    staggered_parser.add_argument(
        "--hold-seconds",
        required=True,
        type=float,
        help="Duration to keep both channels on before the lag channel turns off.",
    )
    staggered_parser.add_argument(
        "--rest-seconds",
        type=float,
        default=0.0,
        help="Rest duration after both channels turn off.",
    )
    staggered_parser.add_argument("--cycles", required=True, type=int, help="Cycle count.")
    staggered_parser.add_argument("--lead-voltage", type=float, help="Optional preset voltage for lead channel.")
    staggered_parser.add_argument("--lead-current", type=float, help="Optional preset current for lead channel.")
    staggered_parser.add_argument("--lag-voltage", type=float, help="Optional preset voltage for lag channel.")
    staggered_parser.add_argument("--lag-current", type=float, help="Optional preset current for lag channel.")
    staggered_parser.add_argument(
        "--log-file",
        help="Optional CSV log path. Defaults to runtime/sequence_logs/<timestamp>.csv",
    )

    args = parser.parse_args()

    try:
        if args.command == "show-plan":
            print_stage_plan()
            return 0

        if args.command == "list-visa-resources":
            resources = list_visa_resources()
            if not resources:
                print("No VISA resources found.")
                return 0
            print("Visible VISA resources:")
            for item in resources:
                print(f"- {item}")
            return 0

        if args.command == "probe-visa":
            response = probe_visa_resource(
                resource=args.resource,
                command=args.scpi,
                timeout_ms=args.timeout_ms,
            )
            print(f"resource: {args.resource}")
            print(f"command: {args.scpi}")
            print(f"response: {response}")
            return 0

        if args.command == "socket-scpi":
            response = run_socket_command(
                host=args.host,
                port=args.port,
                command=args.scpi,
                timeout_ms=args.timeout_ms,
                expect_response=not args.write_only,
            )
            print(f"host: {args.host}")
            print(f"port: {args.port}")
            print(f"command: {args.scpi}")
            if args.write_only:
                print("result: sent")
            else:
                print(f"response: {response}")
            return 0

        if args.command == "odp-socket-smoke":
            run_odp_socket_smoke(args)
            return 0

        if args.command == "scan-devices":
            print(f"Scanning {args.subnet}.1-254 (timeout={args.timeout_ms}ms, workers={args.workers}) ...")
            devices = scan_subnet(args.subnet, timeout_ms=args.timeout_ms, workers=args.workers)
            if not devices:
                print("No devices found.")
                return 0
            print(f"Found {len(devices)} device(s):")
            for d in devices:
                print(f"  {d.suggested_id}  {d.host}:{d.port}  {d.idn}")
            if args.emit_yaml:
                print("\n--- yaml snippet ---")
                print(devices_to_yaml(devices))
            return 0

        app = create_app(Path(args.config))

        if args.command == "check-config":
            print_config_summary(app)
            return 0

        if args.command == "show-devices":
            for item in app.device_service.list_devices():
                print(item)
            return 0

        if args.command == "probe-idn":
            identity = app.device_service.identify(args.device)
            print(f"{identity.device_id} ({identity.model}) -> {identity.identity}")
            return 0

        if args.command == "measure":
            sample = app.device_service.read_measurement(args.device, args.channel)
            print_measurement(sample)
            return 0

        if args.command == "set-voltage":
            channel = app.device_service.set_voltage(args.device, args.channel, args.value)
            print(f"set_voltage: device={args.device}, channel={channel}, voltage={args.value}")
            return 0

        if args.command == "set-current":
            channel = app.device_service.set_current(args.device, args.channel, args.value)
            print(f"set_current: device={args.device}, channel={channel}, current={args.value}")
            return 0

        if args.command == "output-on":
            channel = app.device_service.output_on(args.device, args.channel)
            print(f"output_on: device={args.device}, channel={channel}")
            return 0

        if args.command == "output-off":
            channel = app.device_service.output_off(args.device, args.channel)
            print(f"output_off: device={args.device}, channel={channel}")
            return 0

        if args.command == "run-cycle":
            plan = app.sequence_service.build_single_channel_cycle_plan(
                device_id=args.device,
                channel=args.channel,
                on_seconds=args.on_seconds,
                off_seconds=args.off_seconds,
                cycles=args.cycles,
                voltage=args.voltage,
                current=args.current,
            )
            return _execute_sequence_plan(app, plan, args.log_file)

        if args.command == "run-parallel-cycle":
            plan = app.sequence_service.build_parallel_channel_cycle_plan(
                device_id=args.device,
                channel_specs=parse_parallel_channel_specs(args.channel_specs),
            )
            return _execute_sequence_plan(app, plan, args.log_file)

        if args.command == "run-relative-cycle":
            plan = app.sequence_service.build_relative_channel_cycle_plan(
                device_id=args.device,
                on_seconds=args.on_seconds,
                off_seconds=args.off_seconds,
                cycles=args.cycles,
                channel_specs=parse_relative_channel_specs(args.channel_specs),
            )
            return _execute_sequence_plan(app, plan, args.log_file)

        if args.command == "run-staggered-cycle":
            plan = app.sequence_service.build_staggered_channel_cycle_plan(
                device_id=args.device,
                lead_channel=args.lead_channel,
                lag_channel=args.lag_channel,
                delay_seconds=args.delay_seconds,
                hold_seconds=args.hold_seconds,
                rest_seconds=args.rest_seconds,
                cycles=args.cycles,
                lead_voltage=args.lead_voltage,
                lead_current=args.lead_current,
                lag_voltage=args.lag_voltage,
                lag_current=args.lag_current,
            )
            return _execute_sequence_plan(app, plan, args.log_file)

        return 0
    except ValueError as exc:
        parser.error(str(exc))


def print_stage_plan() -> None:
    lines = [
        "Current target: finish one ODP first, then expand.",
        "",
        "Suggested order:",
        "1. Lock down ODP socket commands and parsing.",
        "2. Verify single-channel cycle.",
        "3. Verify two-channel staggered cycle on one ODP.",
        "4. Add runtime event logs.",
        "5. Add PSW after ODP behavior is stable.",
        "6. Then add multi-device sampling, export, and timing control.",
    ]
    print("\n".join(lines))


def print_config_summary(app) -> None:
    settings = app.settings
    print(f"app_name: {settings.name}")
    print(f"environment: {settings.environment}")
    print(f"base_dir: {settings.base_dir}")
    print(f"log_dir: {settings.directories.log_dir}")
    print(f"export_dir: {settings.directories.export_dir}")
    print(f"runtime_dir: {settings.directories.runtime_dir}")
    print("")
    print("devices:")
    for device in settings.devices:
        print(
            f"- {device.id} | vendor={device.vendor} | model={device.model} "
            f"| transport={device.transport.type}"
        )


def print_measurement(sample) -> None:
    print(f"device_id: {sample.device_id}")
    print(f"channel: {sample.channel}")
    print(f"voltage: {sample.voltage}")
    print(f"current: {sample.current}")
    if sample.raw:
        print(f"raw: {sample.raw}")


def print_sequence_summary(plan_name: str, events, log_path: str) -> None:
    print(f"plan_name: {plan_name}")
    print(f"step_count: {len(events)}")
    print(f"log_file: {log_path}")
    print("last_events:")
    for event in events[-5:]:
        print(f"- {event.timestamp} | {event.channel} | {event.action} | {event.detail}")


def resolve_sequence_log_path(log_path: str | None, plan_name: str) -> str:
    if log_path:
        return log_path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"sequence_logs/{plan_name}_{timestamp}.csv"


def _execute_sequence_plan(app, plan, log_file: str | None) -> int:
    log_path = resolve_sequence_log_path(log_file, plan.name)
    events = app.sequence_service.execute_plan(plan, log_path=log_path)
    print_sequence_summary(plan.name, events, log_path)
    return 0


def run_odp_socket_smoke(args) -> None:
    device = _build_temp_odp_device(
        host=args.host,
        port=args.port,
        channel=args.channel,
        timeout_ms=args.timeout_ms,
    )
    print(f"host: {args.host}")
    print(f"port: {args.port}")
    print(f"channel: {args.channel}")

    device.connect()
    try:
        identity = device.identify()
        print(f"idn: {identity}")

        if args.voltage is not None:
            device.set_voltage(args.channel, args.voltage)
            print(f"set_voltage: ok ({args.voltage})")

        if args.current is not None:
            device.set_current(args.channel, args.current)
            print(f"set_current: ok ({args.current})")

        if args.output_on:
            device.output_on(args.channel)
            print("output_on: ok")

        if args.measure:
            sample = device.read_measurement(args.channel)
            print("measure: ok")
            print_measurement(sample)

        if args.output_off:
            device.output_off(args.channel)
            print("output_off: ok")
    finally:
        device.disconnect()


def _build_temp_odp_device(
    *,
    host: str,
    port: int,
    channel: str,
    timeout_ms: int,
) -> OdpPowerSupply:
    transport_config = TransportConfig(
        type=TransportType.SOCKET,
        host=host,
        port=port,
        timeout_ms=timeout_ms,
        write_termination="\n",
        read_termination="\n",
    )
    device_config = DeviceConfig(
        id="odp_socket_tmp",
        vendor=DeviceVendor.OWON,
        model="ODP",
        transport=transport_config,
        logical_channels=[channel],
    )
    return OdpPowerSupply(device_config, SocketTransport(transport_config))
