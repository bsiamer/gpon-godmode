"""Agent-native CLI interface for Nokia/Alcatel GPON Gateway."""

import sys
import os
import json
import argparse
from typing import Any, Dict
from .client import GPONClient
from .models import (
    Device,
    PortForwardRule,
    GatewayStatus,
    DMZConfig,
    GamingOptimizationResult,
    OpticalStatus,
    WifiConfig,
    EthernetPortStatus,
)


def output_result(data: Any, as_json: bool = False, text_formatter=None):
    """Outputs data either as structured JSON or human-readable text."""
    if as_json:
        if hasattr(data, "model_dump"):
            payload = {"status": "ok", "data": data.model_dump()}
        elif isinstance(data, list) and len(data) > 0 and hasattr(data[0], "model_dump"):
            payload = {"status": "ok", "data": [item.model_dump() for item in data]}
        elif isinstance(data, dict):
            payload = {"status": "ok", **data}
        else:
            payload = {"status": "ok", "result": data}
        print(json.dumps(payload, indent=2))
    else:
        if text_formatter:
            text_formatter(data)
        else:
            print(data)


def output_error(error: Exception, as_json: bool = False):
    """Outputs error either as structured JSON or standard error text."""
    if as_json:
        payload = {
            "status": "error",
            "error_type": type(error).__name__,
            "message": str(error),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Error [{type(error).__name__}]: {error}", file=sys.stderr)
    sys.exit(1)


def confirm_exposure(target_ip: str, is_gaming: bool = False, auto_yes: bool = False, as_json: bool = False) -> bool:
    """Prompts for user confirmation before exposing a target device directly to the internet."""
    if auto_yes:
        return True

    action_desc = "Gaming macro (DMZ + disabled DoS filter)" if is_gaming else "DMZ"
    warning = (
        f"\n[!] SAFETY WARNING: {action_desc} routes all unsolicited incoming internet traffic directly to {target_ip} with router firewalling disabled.\n"
        f"    This exposes the target machine fully to the internet. Ensure {target_ip} has an active host firewall (e.g. UFW, Windows Defender).\n"
    )

    if as_json:
        if not sys.stdin.isatty():
            print(json.dumps({"error": "Confirmation required. Pass -y/--yes to confirm exposure.", "target_ip": target_ip}), file=sys.stderr)
            sys.exit(1)

    print(warning, file=sys.stderr if as_json else sys.stdout)
    try:
        prompt = f"Are you sure you want to expose {target_ip}? [y/N]: "
        choice = input(prompt).strip().lower()
        return choice in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.", file=sys.stderr if as_json else sys.stdout)
        return False


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        help="Emit output as strict machine-readable JSON for AI agents",
    )
    common.add_argument(
        "--ip",
        help="Gateway IP (defaults to ROUTER_IP or http://192.168.1.254)",
    )
    common.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip safety confirmation prompts",
    )

    parser = argparse.ArgumentParser(
        prog="gpon",
        description="Agent-native GPON Gateway automation toolkit",
        parents=[common],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Status
    subparsers.add_parser("status", parents=[common], help="Get gateway hardware, uptime, and WAN status")

    # 2. Devices
    subparsers.add_parser("devices", parents=[common], help="List all active and known LAN/Wi-Fi devices")

    # 3. Ports
    ports_parser = subparsers.add_parser("ports", parents=[common], help="Manage NAT port forwardings")
    ports_sub = ports_parser.add_subparsers(dest="ports_action", required=True)

    ports_sub.add_parser("list", parents=[common], help="List active port forwarding rules")

    add_port = ports_sub.add_parser("add", parents=[common], help="Add a port forwarding rule")
    add_port.add_argument("ext_port", type=int, help="External WAN port (1-65535)")
    add_port.add_argument("int_port", type=int, help="Internal LAN port (1-65535)")
    add_port.add_argument("ip", help="Internal target IP address")
    add_port.add_argument(
        "--proto",
        choices=["TCP", "UDP", "TCP/UDP"],
        default="TCP",
        help="Protocol (default: TCP)",
    )

    del_port = ports_sub.add_parser("del", parents=[common], help="Delete a port forwarding rule")
    del_port.add_argument("ext_port", type=int, help="External port of rule to delete")

    # 4. DMZ
    dmz_parser = subparsers.add_parser("dmz", parents=[common], help="Manage DMZ host")
    dmz_sub = dmz_parser.add_subparsers(dest="dmz_action", required=True)
    dmz_sub.add_parser("get", parents=[common], help="Show current DMZ status")
    dmz_set = dmz_sub.add_parser("set", parents=[common], help="Enable DMZ for a target IP")
    dmz_set.add_argument("ip", help="LAN IP address to put in DMZ")
    dmz_sub.add_parser("disable", parents=[common], help="Disable DMZ")

    # 5. DNS
    dns_parser = subparsers.add_parser("dns", parents=[common], help="Set LAN IPv4 DNS servers")
    dns_parser.add_argument("primary", help="Primary DNS (e.g. 1.1.1.1)")
    dns_parser.add_argument("secondary", help="Secondary DNS (e.g. 1.0.0.1)")

    # 6. Gaming macro
    gaming_parser = subparsers.add_parser(
        "gaming", parents=[common], help="Apply gaming optimizations (DMZ + disable DoS filter + disable SIP ALG + UPnP)"
    )
    gaming_parser.add_argument("ip", help="Target console/PC IP address")

    # 7. Reboot
    subparsers.add_parser("reboot", parents=[common], help="Soft-reboot the gateway")

    # 8. Optical
    subparsers.add_parser("optical", parents=[common], help="Get fiber optic transceiver telemetry")

    # 9. Wi-Fi
    wifi_parser = subparsers.add_parser("wifi", parents=[common], help="View or modify 2.4GHz Wi-Fi settings")
    wifi_sub = wifi_parser.add_subparsers(dest="wifi_action")
    wifi_sub.add_parser("status", parents=[common], help="Show Wi-Fi configuration and channel")
    wifi_chan = wifi_sub.add_parser("channel", parents=[common], help="Set Wi-Fi channel (1-13)")
    wifi_chan.add_argument("channel", type=int, choices=range(1, 14), help="Channel number (1-13)")

    # 10. Ethernet
    subparsers.add_parser("ethernet", parents=[common], help="Get physical Ethernet LAN port statuses and link speeds")

    # 11. REST API Daemon
    daemon_parser = subparsers.add_parser("daemon", help="Start the local FastAPI REST API daemon")
    daemon_parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("GPON_API_PORT", 8254)),
        help="Port to bind daemon (default: 8254, or GPON_API_PORT env)",
    )
    daemon_parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("GPON_API_HOST", "127.0.0.1"),
        help="Host to bind daemon (default: 127.0.0.1)",
    )
    daemon_parser.add_argument(
        "--idle-timeout",
        type=int,
        default=int(os.environ.get("GPON_IDLE_TIMEOUT", "0")),
        help="Shut down daemon after N seconds of inactivity to free RAM (default: 0 = disabled)",
    )
    daemon_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # 12. MCP Server
    subparsers.add_parser("mcp", parents=[common], help="Launch the stdio FastMCP server for AI agents")

    args = parser.parse_args()

    # Route MCP invocation immediately
    if args.command == "mcp":
        from .mcp_server import main as run_mcp
        run_mcp()
        return

    # Route Daemon invocation immediately
    if args.command == "daemon":
        from .api import run_daemon
        # Set sys.argv so run_daemon's parser sees the daemon-specific flags
        sys.argv = [sys.argv[0]]
        if args.port:
            sys.argv.extend(["--port", str(args.port)])
        if args.host:
            sys.argv.extend(["--host", str(args.host)])
        if args.idle_timeout:
            sys.argv.extend(["--idle-timeout", str(args.idle_timeout)])
        if args.reload:
            sys.argv.append("--reload")
        run_daemon()
        return

    client = GPONClient(ip=args.ip)

    try:
        if args.command == "status":
            st = client.get_status()

            def format_status(s: GatewayStatus):
                print("=========================================")
                print(f"  Model:       {s.model_name}")
                print(f"  Hardware:    {s.hardware_version}")
                print(f"  Software:    {s.software_version}")
                print(f"  Bootloader:  {s.boot_version}")
                print(f"  Uptime:      {s.uptime_formatted}")
                if s.cpu_temperature is not None:
                    print(f"  CPU Temp:    {s.cpu_temperature} °C")
                print(f"  WAN Status:  {s.wan_status or 'N/A'}")
                print(f"  WAN IP:      {s.wan_ip or 'N/A'}")
                print("=========================================")

            output_result(st, as_json=args.json, text_formatter=format_status)

        elif args.command == "devices":
            devs = client.get_devices()

            def format_devices(devices):
                print(f"{'IP Address':<16} | {'MAC Address':<18} | {'Type':<9} | {'Active':<7} | {'Hostname'}")
                print("-" * 75)
                for d in devices:
                    act_str = "Yes" if d.active else "No"
                    print(f"{d.ip_address:<16} | {d.mac_address:<18} | {d.interface_type:<9} | {act_str:<7} | {d.hostname}")

            output_result(devs, as_json=args.json, text_formatter=format_devices)

        elif args.command == "ports":
            if args.ports_action == "list":
                rules = client.list_port_forwards()

                def format_ports(r_list):
                    print(f"{'WAN Port':<10} | {'LAN Port':<10} | {'Proto':<8} | {'Target IP':<16} | {'Enabled'}")
                    print("-" * 60)
                    for r in r_list:
                        en_str = "Yes" if r.enabled else "No"
                        print(f"{r.external_port:<10} | {r.internal_port:<10} | {r.protocol:<8} | {r.server_ip:<16} | {en_str}")

                output_result(rules, as_json=args.json, text_formatter=format_ports)

            elif args.ports_action == "add":
                ok = client.add_port_forward(
                    external_port=args.ext_port,
                    internal_port=args.int_port,
                    server_ip=args.ip,
                    protocol=args.proto,
                )
                res = {
                    "action": "add_port_forward",
                    "success": ok,
                    "external_port": args.ext_port,
                    "internal_port": args.int_port,
                    "server_ip": args.ip,
                    "protocol": args.proto,
                }
                output_result(res, as_json=args.json, text_formatter=lambda r: print(f"Port forward created: WAN {r['external_port']} -> LAN {r['server_ip']}:{r['internal_port']} [{r['protocol']}]"))

            elif args.ports_action == "del":
                ok = client.delete_port_forward(args.ext_port)
                res = {
                    "action": "delete_port_forward",
                    "success": ok,
                    "external_port": args.ext_port,
                }
                output_result(res, as_json=args.json, text_formatter=lambda r: print(f"Port forward for WAN {r['external_port']} deleted successfully."))

        elif args.command == "dmz":
            if args.dmz_action == "get":
                dmz_cfg = client.get_dmz()
                output_result(dmz_cfg, as_json=args.json, text_formatter=lambda d: print(f"DMZ Enabled: {d.enabled} | Target IP: {d.ip_address}"))
            elif args.dmz_action == "set":
                if not confirm_exposure(args.ip, is_gaming=False, auto_yes=args.yes, as_json=args.json):
                    output_result({"action": "set_dmz", "cancelled": True, "message": "Operation cancelled by user."}, as_json=args.json, text_formatter=lambda r: print(r["message"]))
                    sys.exit(0)
                ok = client.set_dmz(args.ip, enabled=True)
                res = {"action": "set_dmz", "success": ok, "ip": args.ip, "enabled": True}
                output_result(res, as_json=args.json, text_formatter=lambda r: print(f"DMZ successfully enabled for IP {r['ip']}"))
            elif args.dmz_action == "disable":
                ok = client.set_dmz("0.0.0.0", enabled=False)
                res = {"action": "set_dmz", "success": ok, "enabled": False}
                output_result(res, as_json=args.json, text_formatter=lambda r: print("DMZ successfully disabled."))

        elif args.command == "dns":
            ok = client.set_dns(args.primary, args.secondary)
            res = {"action": "set_dns", "success": ok, "primary": args.primary, "secondary": args.secondary}
            output_result(res, as_json=args.json, text_formatter=lambda r: print(f"DNS servers set to {r['primary']}, {r['secondary']}"))

        elif args.command == "gaming":
            if not confirm_exposure(args.ip, is_gaming=True, auto_yes=args.yes, as_json=args.json):
                output_result({"action": "gaming", "cancelled": True, "message": "Operation cancelled by user."}, as_json=args.json, text_formatter=lambda r: print(r["message"]))
                sys.exit(0)
            res = client.optimize_gaming(args.ip)
            output_result(res, as_json=args.json, text_formatter=lambda r: print(r.message))

        elif args.command == "optical":
            opt = client.get_optical_status()

            def format_optical(o: OpticalStatus):
                print("=========================================")
                print(f"  TX Power:    {o.tx_power_dbm:.2f} dBm")
                print(f"  RX Power:    {o.rx_power_dbm:.2f} dBm")
                print(f"  Transceiver: {o.transceiver_temperature:.1f} °C")
                print(f"  Laser Bias:  {o.bias_current_ua:.1f} µA")
                print(f"  Quality:     {o.signal_quality}")
                print("=========================================")

            output_result(opt, as_json=args.json, text_formatter=format_optical)

        elif args.command == "wifi":
            if getattr(args, "wifi_action", None) == "channel":
                ok = client.set_wifi_channel(args.channel)
                res = {"action": "set_wifi_channel", "success": ok, "channel": args.channel}
                output_result(res, as_json=args.json, text_formatter=lambda r: print(f"Wi-Fi channel set to {r['channel']}."))
            else:
                w = client.get_wifi_config()

                def format_wifi(cfg: WifiConfig):
                    print("=========================================")
                    print(f"  SSID:        {cfg.ssid}")
                    print(f"  Enabled:     {'Yes' if cfg.enabled else 'No'}")
                    print(f"  Channel:     {cfg.channel}")
                    print(f"  TX Power:    {cfg.power_percent}%")
                    print(f"  WMM QoS:     {'Enabled' if cfg.wmm_enabled else 'Disabled'}")
                    print(f"  Broadcast:   {'Enabled' if cfg.broadcast_ssid else 'Disabled'}")
                    print("=========================================")

                output_result(w, as_json=args.json, text_formatter=format_wifi)

        elif args.command == "ethernet":
            ports = client.get_ethernet_ports()

            def format_ethernet(p_list):
                print(f"{'Port':<7} | {'Status':<8} | {'Speed':<10} | {'Duplex':<6} | {'Bytes Sent':<12} | {'Bytes Recv':<12}")
                print("-" * 66)
                for p in p_list:
                    speed_str = f"{p.speed_mbps} Mbps" if p.status == "Up" else "No Link"
                    print(f"LAN {p.port_id:<3} | {p.status:<8} | {speed_str:<10} | {p.duplex:<6} | {p.bytes_sent:<12} | {p.bytes_received:<12}")

            output_result(ports, as_json=args.json, text_formatter=format_ethernet)

        elif args.command == "reboot":
            ok = client.reboot()
            res = {"action": "reboot", "success": ok, "message": "Reboot command sent to gateway."}
            output_result(res, as_json=args.json, text_formatter=lambda r: print(r["message"]))

    except Exception as e:
        output_error(e, as_json=args.json)


if __name__ == "__main__":
    main()
