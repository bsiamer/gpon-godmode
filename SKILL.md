---
name: gpon-godmode
description: Agent-native automation toolkit, Model Context Protocol (MCP) server, and REST API daemon for Nokia/Alcatel GPON Home Gateways (G-240W-F). Use to query connected devices, monitor gateway health, read fiber optic telemetry (RX/TX dBm), optimize Wi-Fi channels, inspect physical Ethernet port link speeds (Gigabit vs 100M bottleneck), configure port forwarding, manage DMZ, set DNS, optimize gaming traffic, run local REST daemon on port 8254, and safely reboot the gateway.
---

# GPON God-Mode Agent Skill

This skill allows AI agents to inspect, manage, and optimize Nokia/Alcatel GPON home gateways (such as the G-240W-F) over pure HTTP without requiring a browser or heavy GUI automation.

## Connection & Environment

The gateway client reads credentials from environment variables or a `.env` file in the project root:
- `ROUTER_IP`: Gateway web interface URL (default: `http://192.168.1.254`).
- `ROUTER_USER`: Web admin username (default: `userAdmin`).
- `ROUTER_PASS`: Web admin password.
- `GPON_API_PORT`: REST API Daemon listen port (default: `8254`).
- `GPON_API_HOST`: REST API Daemon bind host (default: `127.0.0.1`).

---

## Agent Interface 1: MCP Server (`gpon-mcp`)

To provide native tool calls to Claude Desktop, Cursor, Antigravity, or Hermes Agent, register the MCP server:

```json
{
  "mcpServers": {
    "gpon": {
      "command": "/home/noe/Projects/gpon-godmode/venv/bin/gpon-mcp",
      "env": {
        "ROUTER_IP": "http://192.168.1.254",
        "ROUTER_USER": "userAdmin",
        "ROUTER_PASS": "your_password"
      }
    }
  }
}
```

### Registered MCP Tools:

| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| `gpon_get_status` | *(None)* | Returns model, software version, hardware revision, uptime, CPU temperature, and WAN IP/status. |
| `gpon_get_devices` | *(None)* | Returns all active and known LAN and Wi-Fi devices with IP, MAC, hostname, and interface type (`Ethernet` or `802.11`). |
| `gpon_list_devices` | *(None)* | Alias for `gpon_get_devices`. |
| `gpon_get_optical_status` | *(None)* | Returns fiber transceiver telemetry: TX/RX power in dBm, temperature, laser bias current, and health classification. |
| `gpon_get_wifi_config` | *(None)* | Returns 2.4GHz Wi-Fi configuration (SSID, operating channel, transmit power %, WMM state). |
| `gpon_set_wifi_channel` | `channel` | Sets Wi-Fi channel (1–13) to mitigate co-channel congestion. |
| `gpon_get_ethernet_ports`| *(None)* | Returns physical LAN ports 1–4 status, negotiated speed (1000M vs 100M bottleneck), duplex, and error counters. |
| `gpon_list_port_forwards`| *(None)* | Returns active NAT port forwarding rules. |
| `gpon_add_port_forward` | `external_port`, `internal_port`, `server_ip`, `protocol` | Opens WAN port and forwards to LAN IP. |
| `gpon_delete_port_forward`| `external_port` | Deletes an existing rule by external port number. |
| `gpon_get_dmz` | *(None)* | Retrieves current DMZ enabled status and host IP. |
| `gpon_set_dmz` | `target_ip`, `enabled` | Places target LAN device in DMZ or disables DMZ. |
| `gpon_set_dns` | `primary_dns`, `secondary_dns` | Updates LAN DHCP IPv4 DNS servers. |
| `gpon_optimize_gaming` | `target_ip` | One-call macro: sets DMZ for target, disables DoS filter, disables voice-corrupting ALGs (SIP/RTSP), enables UPnP. |
| `gpon_reboot` | *(None)* | Sends soft-reboot signal to gateway. |

---

## Agent Interface 2: CLI Subshell (`--json`)

Autonomous subagents executing shell commands should always use the `--json` flag to receive structured JSON contracts:

### 1. Check Gateway Status
```bash
./gpon.sh status --json
```

### 2. Discover Connected Devices
```bash
./gpon.sh devices --json
```

### 3. Check Fiber Optic Telemetry (RX/TX dBm)
```bash
./gpon.sh optical --json
```

### 4. Wi-Fi Configuration & Channel Switching
```bash
# Query Wi-Fi config
./gpon.sh wifi status --json

# Change Wi-Fi channel to clean frequency (e.g. 6)
./gpon.sh wifi channel 6 --json
```

### 5. Physical Ethernet Port Speed & Cable Bottleneck Detection
```bash
./gpon.sh ethernet --json
```

### 6. Manage Port Forwarding
```bash
# List active rules
./gpon.sh ports list --json

# Add port forward (WAN 25565 -> LAN 192.168.1.154:25565 TCP)
./gpon.sh ports add 25565 25565 192.168.1.154 --proto TCP --json

# Delete port forward by external port
./gpon.sh ports del 25565 --json
```

### 7. DMZ Host Management
```bash
# Check current DMZ
./gpon.sh dmz get --json

# Enable DMZ for device
./gpon.sh dmz set 192.168.1.74 --json

# Disable DMZ
./gpon.sh dmz disable --json
```

### 8. Gaming Latency Optimization
To optimize the network for competitive gaming (Fortnite, Call of Duty, Rocket League) on a console or PC:
```bash
./gpon.sh gaming 192.168.1.74 --json
```

### 9. Set LAN DHCP DNS Servers
```bash
./gpon.sh dns 1.1.1.1 1.0.0.1 --json
```

### 10. Reboot the Gateway
```bash
./gpon.sh reboot --json
```

---

## Agent Interface 3: REST API Daemon (Port 8254)

When autonomous agents or backend services require persistent HTTP connectivity, start the REST daemon:

```bash
# Launch daemon on default niche port 8254
./gpon.sh daemon --port 8254
```

- **Base URL**: `http://127.0.0.1:8254`
- **Interactive Swagger UI**: `http://127.0.0.1:8254/docs`
- **OpenAPI 3.1 Spec**: `http://127.0.0.1:8254/openapi.json`
- **Environment Override**: `export GPON_API_PORT=8254`

### Key Endpoints:
- `GET /api/status`: Router hardware, uptime, and WAN IP
- `GET /api/devices`: Connected LAN and Wi-Fi devices
- `GET /api/optical`: Fiber optic power and signal health
- `GET /api/wifi` & `POST /api/wifi/channel`: Wi-Fi radio and channel configuration
- `GET /api/ethernet`: Physical LAN port speeds (1000M vs 100M bottleneck)
- `GET /api/port-forwards` & `POST /api/port-forwards`: NAT management
- `POST /api/optimize-gaming`: One-click gaming latency macro
- `POST /api/reboot`: Safe soft-reboot

---

## Multi-Language SDK Integration

### 1. Python SDK (Direct Import)
```python
from gpon_godmode import GPONClient

with GPONClient() as client:
    status = client.get_status()
    print(f"Model: {status.model_name}, WAN IP: {status.wan_ip}")
    
    optical = client.get_optical_status()
    print(f"Fiber RX: {optical.rx_power_dbm} dBm ({optical.signal_quality})")
```

### 2. Java SDK (`sdk/java`)
Zero-dependency Java 11+ client with automated REST-to-CLI fallback:
```java
import com.gpon.godmode.GponClient;
import com.gpon.godmode.OpticalStatus;

GponClient client = GponClient.builder().port(8254).fallbackToCli(true).build();

// Read optical health
OpticalStatus optical = client.getOpticalStatus();

// Automatically forward Minecraft port 25565
client.addPortForward(25565, 25565, "192.168.1.154", "TCP");

// Prioritize gaming host with one-click macro
client.optimizeGaming("192.168.1.154");
```

### 3. Go SDK (`sdk/go`)
Context-aware client with functional options and automated CLI fallback:
```go
package main

import (
    "context"
    "fmt"
    "time"
    "github.com/noecodes/gpon-godmode/sdk/go"
)

func main() {
    client := gpon.NewClient(
        gpon.WithAPIPort(8254),
        gpon.WithCLIFallback(true),
    )
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    optical, _ := client.GetOpticalStatus(ctx)
    fmt.Printf("Fiber RX: %.2f dBm (%s)\n", optical.RXPowerDBm, optical.SignalQuality)
}
```

---

## Error Handling Pattern for Agents

All commands return exit code `0` on success and `1` on error. With `--json`, errors are serialized deterministically:

```json
{
  "status": "error",
  "error_type": "ValueError",
  "message": "No active port forward rule found for external port 9999"
}
```

When an error occurs:
- If `error_type` is `PermissionError`: Credentials in `.env` are invalid or expired.
- If `error_type` is `ConnectionError`: Router IP is unreachable (verify physical cable or IP subnet).
- If `error_type` is `ValueError`: Invalid input parameter (e.g. malformed IP address or invalid port range).
