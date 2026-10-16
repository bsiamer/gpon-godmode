"""FastAPI REST API Daemon for GPON God-Mode.

Provides a fast, typed, browserless REST interface on a niche port (default 8254)
for external backends (Java, Go, Python, Node, Minecraft plugins, etc.).

Supports on-demand socket activation and automatic idle timeout shutdown
so it stays hot for 1 minute after calls, then frees 100% of its RAM.
"""

import os
import sys
import time
import signal
import ctypes
import asyncio
import argparse
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from .client import GPONClient
from .models import (
    GatewayStatus,
    Device,
    OpticalStatus,
    WifiConfig,
    EthernetPortStatus,
    PortForwardRule,
    PortForwardCreateRequest,
    DMZConfig,
    DMZSetRequest,
    DNSSetRequest,
    WifiChannelRequest,
    GamingOptimizationRequest,
    GamingOptimizationResult,
    RebootRequest,
)

load_dotenv()

# Niche default port: 8254 (easily configurable via GPON_API_PORT or CLI --port)
DEFAULT_PORT = int(os.getenv("GPON_API_PORT", "8254"))
DEFAULT_HOST = os.getenv("GPON_API_HOST", "127.0.0.1")


class IdleTimeoutManager:
    """Monitors activity and triggers graceful shutdown after N seconds of silence."""

    def __init__(self, timeout_seconds: int = 0):
        self.timeout = timeout_seconds
        self.last_activity = time.time()
        self._task: Optional[asyncio.Task] = None

    def touch(self):
        """Resets the idle timer on incoming request."""
        self.last_activity = time.time()

    async def _monitor_loop(self):
        if self.timeout <= 0:
            return
        while True:
            await asyncio.sleep(2)
            idle_time = time.time() - self.last_activity
            if idle_time >= self.timeout:
                print(f"\n[IdleTimeout] No requests received for {int(idle_time)}s (timeout={self.timeout}s).")
                print("[IdleTimeout] Gracefully shutting down daemon to release 100% RAM...")
                try:
                    # Release unused glibc heap memory back to Linux OS
                    ctypes.CDLL("libc.so.6").malloc_trim(0)
                except Exception:
                    pass
                # Trigger graceful uvicorn shutdown
                os.kill(os.getpid(), signal.SIGINT)
                break

    def start(self):
        if self.timeout > 0:
            self.last_activity = time.time()
            self._task = asyncio.create_task(self._monitor_loop())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for GPON client pool and idle timer."""
    client = GPONClient()
    app.state.client = client

    # Configure idle timeout (default 0 = persistent, or from GPON_IDLE_TIMEOUT)
    timeout_sec = int(os.getenv("GPON_IDLE_TIMEOUT", "0"))
    idle_manager = IdleTimeoutManager(timeout_seconds=timeout_sec)
    app.state.idle_manager = idle_manager
    idle_manager.start()

    yield

    idle_manager.stop()
    client.close()


app = FastAPI(
    title="GPON God-Mode REST API Daemon",
    description="Local agent-native & backend REST API for Nokia/Alcatel-Lucent GPON Gateways.",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for local backends, web frontends, and Minecraft server bridges
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_activity(request: Request, call_next):
    """Refreshes idle timer on every request and trims memory."""
    idle_manager: Optional[IdleTimeoutManager] = getattr(app.state, "idle_manager", None)
    if idle_manager:
        idle_manager.touch()

    response = await call_next(request)

    if idle_manager:
        idle_manager.touch()
        try:
            # Tell Linux glibc to release unused heap pages back to OS
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass

    return response


def get_client() -> GPONClient:
    """Dependency injector for GPONClient."""
    return app.state.client


@app.get("/", summary="Daemon Metadata")
def root(client: GPONClient = Depends(get_client)) -> Dict[str, Any]:
    """Returns daemon info, configured router, and documentation endpoints."""
    idle_manager: Optional[IdleTimeoutManager] = getattr(app.state, "idle_manager", None)
    timeout_val = idle_manager.timeout if idle_manager else 0
    return {
        "service": "GPON God-Mode REST API Daemon",
        "version": "2.0.0",
        "router_ip": client.ip,
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "idle_timeout_seconds": timeout_val,
        "status": "online",
    }


@app.get("/health", summary="Health Check")
def health(client: GPONClient = Depends(get_client)) -> Dict[str, str]:
    """Simple liveness probe."""
    return {
        "status": "healthy",
        "router": client.ip,
    }


@app.get("/api/status", response_model=GatewayStatus, summary="Gateway Status")
def get_gateway_status(client: GPONClient = Depends(get_client)):
    """Hardware information, firmware version, uptime, and WAN IP."""
    try:
        return client.get_status()
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query router: {e}")


@app.get("/api/devices", response_model=List[Device], summary="Connected Devices")
def get_connected_devices(client: GPONClient = Depends(get_client)):
    """List of all active LAN and Wi-Fi devices with IP, MAC, and interface type."""
    try:
        return client.get_devices()
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query devices: {e}")


@app.get("/api/optical", response_model=OpticalStatus, summary="Optical Signal Telemetry")
def get_optical_status(client: GPONClient = Depends(get_client)):
    """GPON laser transceiver telemetry: TX/RX power in dBm, temperature, and quality."""
    try:
        return client.get_optical_status()
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query optical telemetry: {e}")


@app.get("/api/wifi", response_model=WifiConfig, summary="Wi-Fi Configuration")
def get_wifi_config(client: GPONClient = Depends(get_client)):
    """Wi-Fi 2.4GHz radio status, SSID, channel, and transmit power."""
    try:
        return client.get_wifi_config()
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query Wi-Fi config: {e}")


@app.post("/api/wifi/channel", summary="Set Wi-Fi Channel")
def set_wifi_channel(req: WifiChannelRequest, client: GPONClient = Depends(get_client)) -> Dict[str, Any]:
    """Switches the 2.4GHz Wi-Fi channel (1-13) to avoid interference."""
    try:
        success = client.set_wifi_channel(req.channel)
        return {"success": success, "channel": req.channel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ethernet", response_model=List[EthernetPortStatus], summary="Ethernet Port Status")
def get_ethernet_ports(client: GPONClient = Depends(get_client)):
    """Physical Ethernet LAN ports (1-4) link status, negotiated speed, and packet stats."""
    try:
        return client.get_ethernet_ports()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/port-forwards", response_model=List[PortForwardRule], summary="List Port Forwards")
def list_port_forwards(client: GPONClient = Depends(get_client)):
    """Retrieves all active virtual host / NAT port forwarding rules."""
    try:
        return client.list_port_forwards()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/port-forwards", summary="Add Port Forward")
def add_port_forward(rule: PortForwardCreateRequest, client: GPONClient = Depends(get_client)) -> Dict[str, Any]:
    """Creates a new NAT port forwarding rule."""
    try:
        success = client.add_port_forward(
            external_port=rule.external_port,
            internal_port=rule.internal_port,
            server_ip=rule.server_ip,
            protocol=rule.protocol,
        )
        return {
            "success": success,
            "rule": rule.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/port-forwards/{external_port}", summary="Delete Port Forward")
def delete_port_forward(
    external_port: int = Path(..., ge=1, le=65535, description="External port number of the rule to delete"),
    client: GPONClient = Depends(get_client),
) -> Dict[str, Any]:
    """Deletes an active NAT port forwarding rule by its external port."""
    try:
        success = client.delete_port_forward(external_port)
        return {"success": success, "deleted_port": external_port}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dmz", response_model=DMZConfig, summary="Get DMZ Configuration")
def get_dmz(client: GPONClient = Depends(get_client)):
    """Retrieves the current DMZ host state and target IP address."""
    try:
        return client.get_dmz()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dmz", summary="Set DMZ Configuration")
def set_dmz(req: DMZSetRequest, client: GPONClient = Depends(get_client)) -> Dict[str, Any]:
    """Enables or disables DMZ forwarding to a specific target LAN IP."""
    try:
        success = client.set_dmz(ip_address=req.ip_address, enable=req.enabled)
        return {"success": success, "ip_address": req.ip_address, "enabled": req.enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dns", summary="Set DNS Servers")
def set_dns(req: DNSSetRequest, client: GPONClient = Depends(get_client)) -> Dict[str, Any]:
    """Updates LAN DHCP DNS servers (e.g. 1.1.1.1 / 8.8.8.8)."""
    try:
        success = client.set_dns(primary=req.primary_dns, secondary=req.secondary_dns)
        return {"success": success, "primary_dns": req.primary_dns, "secondary_dns": req.secondary_dns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/optimize-gaming", response_model=GamingOptimizationResult, summary="Optimize for Gaming")
def optimize_gaming(req: GamingOptimizationRequest, client: GPONClient = Depends(get_client)):
    """One-shot latency and packet drop optimization macro for gaming (DMZ, UPnP, disable DoS filter, disable ALGs)."""
    try:
        return client.optimize_gaming(target_ip=req.target_ip, enable_dmz=req.enable_dmz)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reboot", summary="Reboot Router")
def reboot_gateway(req: RebootRequest, client: GPONClient = Depends(get_client)) -> Dict[str, Any]:
    """Gracefully reboots the GPON Gateway (requires confirm=true)."""
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Reboot requires 'confirm': true")
    try:
        success = client.reboot()
        return {"success": success, "message": "Router reboot command transmitted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_daemon():
    """Command-line entrypoint to run the GPON God-Mode REST API Daemon."""
    parser = argparse.ArgumentParser(
        description=f"Run GPON God-Mode REST API Daemon (Default port: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind the REST daemon (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_HOST,
        help=f"Host address to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=int(os.getenv("GPON_IDLE_TIMEOUT", "0")),
        help="Shut down daemon after N seconds of inactivity to free RAM (0 = persistent)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    args = parser.parse_args()

    # Pass idle timeout to environment so lifespan picks it up
    if args.idle_timeout > 0:
        os.environ["GPON_IDLE_TIMEOUT"] = str(args.idle_timeout)

    # Detect systemd socket activation
    listen_fds = int(os.getenv("LISTEN_FDS", "0"))
    listen_pid = int(os.getenv("LISTEN_PID", "0"))
    is_socket_activated = (listen_fds > 0 and (listen_pid == 0 or listen_pid == os.getpid()))

    if is_socket_activated:
        # Default to 60s idle timeout if activated via systemd socket and not explicitly set
        if "GPON_IDLE_TIMEOUT" not in os.environ or os.environ["GPON_IDLE_TIMEOUT"] == "0":
            os.environ["GPON_IDLE_TIMEOUT"] = "60"

        timeout_sec = os.environ.get("GPON_IDLE_TIMEOUT", "60")
        print("\n==================================================")
        print("  GPON God-Mode REST API Daemon (Socket Activated)")
        print("  Bound to: systemd socket (fd=3)")
        print(f"  Idle Timeout: {timeout_sec}s (auto-sleeps to 0 MB RAM)")
        print("==================================================\n")

        uvicorn.run(
            "gpon_godmode.api:app",
            fd=3,
            reload=args.reload,
        )
    else:
        timeout_sec = os.getenv("GPON_IDLE_TIMEOUT", "0")
        timeout_str = f"{timeout_sec}s (auto-sleep)" if timeout_sec != "0" else "disabled (persistent)"

        print("\n==================================================")
        print("  GPON God-Mode REST API Daemon v2.0.0")
        print(f"  Binding: http://{args.host}:{args.port}")
        print(f"  Idle Timeout: {timeout_str}")
        print(f"  Docs:    http://{args.host}:{args.port}/docs")
        print(f"  OpenAPI: http://{args.host}:{args.port}/openapi.json")
        print("==================================================\n")

        uvicorn.run(
            "gpon_godmode.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    run_daemon()
