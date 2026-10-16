"""Pydantic v2 data models and schemas for GPON God-Mode."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
import ipaddress


class Device(BaseModel):
    """Connected LAN or Wi-Fi client."""
    oid: int = Field(default=0, description="Internal router object ID")
    hostname: str = Field(default="", description="Hostname or device identifier")
    ip_address: str = Field(..., description="IPv4 address assigned to device")
    mac_address: str = Field(..., description="Physical MAC address")
    active: bool = Field(default=True, description="Whether device is actively communicating")
    interface_type: str = Field(default="Ethernet", description="'Ethernet' or '802.11'")


class PortForwardRule(BaseModel):
    """Active or desired NAT port forwarding rule."""
    oid: Optional[int] = Field(default=None, description="Router internal rule ID")
    enabled: bool = Field(default=True, description="Whether the rule is enabled")
    external_port: int = Field(..., ge=1, le=65535, description="WAN incoming port (1-65535)")
    internal_port: int = Field(..., ge=1, le=65535, description="LAN target port (1-65535)")
    server_ip: str = Field(..., description="Target LAN IP address")
    protocol: Literal["TCP", "UDP", "TCP/UDP"] = Field(default="TCP", description="Protocol")

    @field_validator("server_ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid server_ip '{v}'. Must be a valid IP address.")
        return v


class GatewayStatus(BaseModel):
    """Router hardware, firmware, and link status."""
    model_name: str = Field(default="", description="Model name (e.g. G-240W-F)")
    hardware_version: str = Field(default="", description="Hardware revision ID")
    software_version: str = Field(default="", description="Active firmware version")
    boot_version: str = Field(default="", description="U-Boot bootloader version")
    uptime_seconds: int = Field(default=0, description="System uptime in seconds")
    uptime_formatted: str = Field(default="", description="Human-readable uptime")
    cpu_temperature: Optional[float] = Field(default=None, description="Current CPU temperature in Celsius")
    wan_ip: Optional[str] = Field(default=None, description="Public IPv4 address")
    wan_status: Optional[str] = Field(default=None, description="WAN PPPoE connection status")


class DMZConfig(BaseModel):
    """DMZ host configuration."""
    enabled: bool = Field(default=False, description="Whether DMZ is active")
    ip_address: str = Field(default="0.0.0.0", description="LAN IP address in DMZ")


class OpticalStatus(BaseModel):
    """Fiber optic transceiver signal telemetry."""
    tx_power_dbm: float = Field(..., description="Transmit optical power in dBm")
    rx_power_dbm: float = Field(..., description="Receive optical power in dBm (target: -8 to -25 dBm)")
    transceiver_temperature: float = Field(..., description="Optical transceiver temperature in Celsius")
    bias_current_ua: float = Field(..., description="Laser bias current in microamperes")
    signal_quality: str = Field(default="Good", description="Assessment of fiber signal quality")


class WifiConfig(BaseModel):
    """Wi-Fi 2.4GHz radio configuration."""
    enabled: bool = Field(default=True, description="Wi-Fi radio status")
    ssid: str = Field(default="", description="Broadcasted network name (SSID)")
    channel: str = Field(default="Auto", description="Operating channel (1-13 or Auto)")
    power_percent: int = Field(default=100, description="Transmit power percentage (25, 50, 75, 100)")
    wmm_enabled: bool = Field(default=True, description="Wi-Fi Multimedia QoS enabled")
    broadcast_ssid: bool = Field(default=True, description="SSID broadcast enabled")


class EthernetPortStatus(BaseModel):
    """Physical Ethernet LAN port link speed and stats."""
    port_id: int = Field(..., description="LAN Port number (1-4)")
    status: str = Field(..., description="'Up' or 'NoLink'")
    speed_mbps: int = Field(default=0, description="Negotiated speed (1000 or 100)")
    duplex: str = Field(default="Auto", description="Full or Half duplex")
    bytes_sent: int = Field(default=0)
    bytes_received: int = Field(default=0)
    packets_sent: int = Field(default=0)
    packets_received: int = Field(default=0)
    errors_received: int = Field(default=0)
    drops_received: int = Field(default=0)


class GamingOptimizationResult(BaseModel):
    """Outcome of gaming optimization macro."""
    target_ip: str
    dmz_configured: bool
    dos_protection_disabled: bool
    sip_alg_disabled: bool
    upnp_enabled: bool
    message: str


class PortForwardCreateRequest(BaseModel):
    """Request payload to create a new port forward rule."""
    external_port: int = Field(..., ge=1, le=65535, description="External WAN port (1-65535)")
    internal_port: int = Field(..., ge=1, le=65535, description="Internal LAN port (1-65535)")
    server_ip: str = Field(..., description="Target LAN IP address")
    protocol: Literal["TCP", "UDP", "TCP/UDP"] = Field(default="TCP", description="Protocol")

    @field_validator("server_ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid server_ip '{v}'. Must be a valid IP address.")
        return v


class DMZSetRequest(BaseModel):
    """Request payload to configure DMZ."""
    ip_address: str = Field(..., description="Target LAN IP address")
    enabled: bool = Field(default=True, description="Enable or disable DMZ")


class DNSSetRequest(BaseModel):
    """Request payload to configure DNS."""
    primary_dns: str = Field(default="1.1.1.1", description="Primary DNS server IPv4")
    secondary_dns: str = Field(default="1.0.0.1", description="Secondary DNS server IPv4")


class WifiChannelRequest(BaseModel):
    """Request payload to change Wi-Fi channel."""
    channel: int = Field(..., ge=1, le=13, description="Wi-Fi 2.4GHz channel (1-13)")


class GamingOptimizationRequest(BaseModel):
    """Request payload to optimize router settings for gaming."""
    target_ip: str = Field(..., description="LAN IP address of the gaming PC or console")
    enable_dmz: bool = Field(default=True, description="Whether to place target device in DMZ")


class RebootRequest(BaseModel):
    """Request payload to reboot the router."""
    confirm: bool = Field(default=False, description="Must be true to prevent accidental reboots")

