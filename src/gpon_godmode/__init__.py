"""GPON God-Mode: Agent-native automation toolkit & MCP server for Nokia/Alcatel GPON Gateways."""

__version__ = "2.0.0"

from .client import GPONClient
from .models import Device, PortForwardRule, GatewayStatus, DMZConfig, GamingOptimizationResult

__all__ = [
    "GPONClient",
    "Device",
    "PortForwardRule",
    "GatewayStatus",
    "DMZConfig",
    "GamingOptimizationResult",
]
