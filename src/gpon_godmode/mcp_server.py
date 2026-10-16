"""Model Context Protocol (MCP) server for GPON Gateway automation.

Exposes native tools for AI agents (Claude Desktop, Antigravity, Cursor, Hermes Agent).
"""

import sys
from typing import List, Dict, Any, Optional

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        raise ImportError(
            "The 'mcp' SDK is required to run the MCP server. Run 'pip install mcp' to install it."
        )

from .client import GPONClient

mcp = MCPServer(
    name="gpon",
    description="Agent-native tools for monitoring, diagnosing, and automating Nokia/Alcatel GPON Gateways",
)


@mcp.tool()
def gpon_get_status() -> Dict[str, Any]:
    """Get the GPON gateway hardware model, firmware version, uptime, CPU temperature, and WAN connection status."""
    with GPONClient() as client:
        status = client.get_status()
        return status.model_dump()


@mcp.tool()
def gpon_get_devices() -> List[Dict[str, Any]]:
    """List all connected LAN and Wi-Fi devices, including IP addresses, MAC addresses, hostnames, and interface types."""
    with GPONClient() as client:
        devices = client.get_devices()
        return [d.model_dump() for d in devices]


@mcp.tool()
def gpon_list_devices() -> List[Dict[str, Any]]:
    """List all connected LAN and Wi-Fi devices (alias for gpon_get_devices)."""
    return gpon_get_devices()


@mcp.tool()
def gpon_get_optical_status() -> Dict[str, Any]:
    """Get fiber optic transceiver telemetry: TX/RX optical power (dBm), temperature, laser bias current, and signal quality."""
    with GPONClient() as client:
        optical = client.get_optical_status()
        return optical.model_dump()


@mcp.tool()
def gpon_get_wifi_config() -> Dict[str, Any]:
    """Get 2.4GHz Wi-Fi configuration including SSID, current channel, transmit power, and WMM status."""
    with GPONClient() as client:
        wifi = client.get_wifi_config()
        return wifi.model_dump()


@mcp.tool()
def gpon_set_wifi_channel(channel: int) -> Dict[str, Any]:
    """Change the 2.4GHz Wi-Fi channel (1-13) to eliminate channel interference.

    Args:
        channel: Operating Wi-Fi channel number (1-13).
    """
    with GPONClient() as client:
        success = client.set_wifi_channel(channel)
        return {
            "success": success,
            "channel": channel,
            "message": f"Wi-Fi channel set to {channel}.",
        }


@mcp.tool()
def gpon_get_ethernet_ports() -> List[Dict[str, Any]]:
    """Get physical Ethernet LAN port statuses (LAN1-LAN4), negotiated bitrates (1000M vs 100M bottleneck), duplex, and packet error counters."""
    with GPONClient() as client:
        ports = client.get_ethernet_ports()
        return [p.model_dump() for p in ports]


@mcp.tool()
def gpon_list_port_forwards() -> List[Dict[str, Any]]:
    """List all currently active NAT port forwarding rules on the router."""
    with GPONClient() as client:
        rules = client.list_port_forwards()
        return [r.model_dump() for r in rules]


@mcp.tool()
def gpon_add_port_forward(
    external_port: int,
    internal_port: int,
    server_ip: str,
    protocol: str = "TCP",
) -> Dict[str, Any]:
    """Open an external port and forward it to a specific internal LAN IP address.

    Args:
        external_port: Incoming WAN port number (1-65535).
        internal_port: Target LAN port number (1-65535).
        server_ip: Target device IPv4 address (e.g. 192.168.1.154).
        protocol: Traffic protocol: 'TCP', 'UDP', or 'TCP/UDP'. Defaults to 'TCP'.
    """
    with GPONClient() as client:
        success = client.add_port_forward(
            external_port=external_port,
            internal_port=internal_port,
            server_ip=server_ip,
            protocol=protocol,
        )
        return {
            "success": success,
            "external_port": external_port,
            "internal_port": internal_port,
            "server_ip": server_ip,
            "protocol": protocol,
            "message": f"Port forward created: WAN {external_port} -> LAN {server_ip}:{internal_port} [{protocol}]",
        }


@mcp.tool()
def gpon_delete_port_forward(external_port: int) -> Dict[str, Any]:
    """Delete an active port forwarding rule by its external port number.

    Args:
        external_port: The external WAN port of the rule to delete.
    """
    with GPONClient() as client:
        success = client.delete_port_forward(external_port)
        return {
            "success": success,
            "external_port": external_port,
            "message": f"Port forward for external port {external_port} deleted successfully.",
        }


@mcp.tool()
def gpon_get_dmz() -> Dict[str, Any]:
    """Get the current DMZ (Demilitarized Zone) configuration and active host IP."""
    with GPONClient() as client:
        dmz = client.get_dmz()
        return dmz.model_dump()


@mcp.tool()
def gpon_set_dmz(target_ip: str, enabled: bool = True) -> Dict[str, Any]:
    """Enable or disable DMZ (Demilitarized Zone) for a specific LAN device.

    Args:
        target_ip: The LAN IPv4 address to place in the DMZ (e.g. 192.168.1.74).
        enabled: Set to True to enable DMZ for this IP, or False to disable DMZ.
    """
    with GPONClient() as client:
        success = client.set_dmz(target_ip, enabled=enabled)
        return {
            "success": success,
            "target_ip": target_ip,
            "enabled": enabled,
            "message": f"DMZ {'enabled for ' + target_ip if enabled else 'disabled'}.",
        }


@mcp.tool()
def gpon_set_dns(primary_dns: str, secondary_dns: str) -> Dict[str, Any]:
    """Set the primary and secondary IPv4 DNS servers for the gateway's LAN DHCP server.

    Args:
        primary_dns: Primary DNS IP address (e.g. '1.1.1.1').
        secondary_dns: Secondary DNS IP address (e.g. '1.0.0.1').
    """
    with GPONClient() as client:
        success = client.set_dns(primary_dns, secondary_dns)
        return {
            "success": success,
            "primary_dns": primary_dns,
            "secondary_dns": secondary_dns,
            "message": f"LAN DNS servers set to {primary_dns}, {secondary_dns}.",
        }


@mcp.tool()
def gpon_optimize_gaming(target_ip: str) -> Dict[str, Any]:
    """One-click gaming macro: puts target console/PC into DMZ, disables DoS filter false-positives, disables voice-corrupting SIP/RTSP ALGs, and enables UPnP.

    Args:
        target_ip: The LAN IP address of the gaming PC or console (e.g. 192.168.1.74).
    """
    with GPONClient() as client:
        result = client.optimize_gaming(target_ip)
        return result.model_dump()


@mcp.tool()
def gpon_reboot() -> Dict[str, Any]:
    """Soft-reboot the GPON gateway."""
    with GPONClient() as client:
        success = client.reboot()
        return {
            "success": success,
            "message": "Reboot signal successfully sent to the gateway. Connection will drop temporarily.",
        }


def main():
    """Runs the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
