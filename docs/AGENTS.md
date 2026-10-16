# Agent Integration Manual: GPON God-Mode

This specification is the official integration manual for AI agents (**Claude, Antigravity, Hermes Agent, Cursor, Copilot, ChatGPT**) interfacing with **Nokia/Alcatel-Lucent GPON Home Gateways** (such as the G-240W-F).

GPON God-Mode enables autonomous agents to monitor, configure, and optimize GPON routers using **100% pure HTTP** (reverse-engineered SJCL RSA-1024 + AES-128-CBC encryption). There are no headless browsers, no UI scraping hurdles, and operations execute in **150ms–300ms** with strict typing and deterministic schemas.

---

## 1. High-Level Integration Matrix

Agents can interface with `gpon-godmode` through three complementary execution modes:

```
+-------------------------------------------------------------------------------+
|                                  AI AGENTS                                    |
|         (Claude Desktop, Antigravity, Hermes, Cursor, Copilot, Custom)        |
+-------------------------------------------------------------------------------+
        |                                   |                               |
        v                                   v                               v
 [1. MCP STDIO SERVER]             [2. CLI SUB-PROCESS]           [3. REST API DAEMON]
  - Native agent tools              - Subshell execution           - HTTP microservices
  - Zero network overhead           - Deterministic exit codes     - Port 8254
  - Tool call parameters            - Strict `--json` output       - Multi-language SDKs
  - Command: `gpon-mcp`             - Command: `gpon <cmd> --json` - OpenAPI: `/openapi.json`
        |                                   |                               |
        +-----------------------------------+-------------------------------+
                                            |
                                            v
                             +-----------------------------+
                             |   Pure HTTP Core Engine     |
                             |  - SJCL Encryption         |
                             |  - Session Keepalive (300s) |
                             |  - Concurrency Mutex Lock   |
                             +-----------------------------+
                                            |
                                            v
                             +-----------------------------+
                             | Nokia/Alcatel GPON Gateway  |
                             |       (e.g. G-240W-F)       |
                             +-----------------------------+
```

| Dimension | 1. Model Context Protocol (MCP) | 2. CLI Subshell (`--json`) | 3. REST API Daemon |
| :--- | :--- | :--- | :--- |
| **Primary Use-Case** | Direct LLM Tool-Calling | Shell-enabled Autonomous Agents | Backends, Microservices & Plugins |
| **Protocol** | JSON-RPC 2.0 over `stdio` | POSIX CLI stdout/stderr | HTTP/1.1 JSON (FastAPI) |
| **Port / Transport** | Process pipes (`stdin`/`stdout`) | Fork/exec subshell | TCP `127.0.0.1:8254` |
| **Process Model** | Ephemeral or long-running | One-shot execution per task | Persistent background daemon |
| **Schema Validation**| Native MCP Tool Definition | Pydantic v2 JSON envelope | OpenAPI 3.1 & JSON Schema |

---

## 2. Interface 1: Model Context Protocol (MCP) Server

The GPON MCP Server exposes typed tools directly into the agent's context.

### Server Registration

Add the server to your agent's configuration file (e.g. `claude_desktop_config.json`, `.cursor/mcp.json`, or Antigravity settings):

```json
{
  "mcpServers": {
    "gpon": {
      "command": "/home/noe/Projects/gpon-godmode/venv/bin/gpon-mcp",
      "env": {
        "ROUTER_IP": "http://192.168.1.254",
        "ROUTER_USER": "userAdmin",
        "ROUTER_PASS": "your_secure_password"
      }
    }
  }
}
```

### Complete MCP Tools Catalog

The MCP server provides 12 specialized tools covering status, devices, physical optics, Wi-Fi radio, Ethernet hardware, NAT rules, DMZ, and gaming optimizations:

#### 1. `gpon_get_status`
* **Description**: Returns hardware model, firmware version, bootloader version, uptime, CPU temperature, and WAN connection status.
* **When to Call**: Call at the start of network diagnostic sessions, after router reboots, or when assessing router health and WAN connectivity.
* **Parameters**: *None*
* **Return Type**:
  ```json
  {
    "model_name": "G-240W-F",
    "hardware_version": "3FE46597AAAA",
    "software_version": "3FE46606BGBB24",
    "boot_version": "U-Boot Dec-31-2016--12:00:00",
    "uptime_seconds": 1492750,
    "uptime_formatted": "17d 6h 39m (1492750s)",
    "cpu_temperature": 69.7,
    "wan_ip": "105.99.121.2",
    "wan_status": "Connected"
  }
  ```

#### 2. `gpon_get_devices` (or alias `gpon_list_devices`)
* **Description**: Lists all active and historically known LAN and Wi-Fi devices, including IP addresses, MAC addresses, hostnames, and interface types.
* **When to Call**: Call prior to creating port forwarding rules or configuring DMZ to discover target IPs and verify device presence.
* **Parameters**: *None*
* **Return Type**:
  ```json
  [
    {
      "oid": 2,
      "hostname": "archlinux",
      "ip_address": "192.168.1.154",
      "mac_address": "b0:83:fe:5d:29:29",
      "active": true,
      "interface_type": "Ethernet"
    },
    {
      "oid": 6,
      "hostname": "PlayStation-5",
      "ip_address": "192.168.1.74",
      "mac_address": "2c:cc:44:0c:8b:ae",
      "active": true,
      "interface_type": "802.11"
    }
  ]
  ```

#### 3. `gpon_get_optical_status`
* **Description**: Returns real-time fiber optic transceiver telemetry: TX/RX optical power (dBm), transceiver temperature (°C), laser bias current ($\mu$A), and signal health classification.
* **When to Call**: Call when diagnosing unexplained packet drops, jitter, latency spikes, or intermittent Internet connection drops.
* **Parameters**: *None*
* **Return Type**:
  ```json
  {
    "tx_power_dbm": 2.45,
    "rx_power_dbm": -18.72,
    "transceiver_temperature": 48.25,
    "bias_current_ua": 14200.0,
    "signal_quality": "Excellent / Healthy"
  }
  ```

#### 4. `gpon_get_wifi_config`
* **Description**: Retrieves current 2.4GHz Wi-Fi configuration (SSID, operating channel, transmit power %, WMM QoS state, broadcast state).
* **When to Call**: Call when investigating Wi-Fi speed issues or inspecting current RF configuration.
* **Parameters**: *None*
* **Return Type**:
  ```json
  {
    "enabled": true,
    "ssid": "FIBRE-HOME-2.4G",
    "channel": "6",
    "power_percent": 100,
    "wmm_enabled": true,
    "broadcast_ssid": true
  }
  ```

#### 5. `gpon_set_wifi_channel`
* **Description**: Sets the Wi-Fi operating channel (1–13) to eliminate co-channel interference from neighboring networks.
* **When to Call**: Call to shift Wi-Fi away from congested frequencies onto non-overlapping channels (1, 6, or 11).
* **Parameters**:
  * `channel` (*integer*, required): Channel number between 1 and 13.
* **Return Type**:
  ```json
  {
    "success": true,
    "channel": 1,
    "message": "Wi-Fi channel set to 1."
  }
  ```

#### 6. `gpon_get_ethernet_ports`
* **Description**: Retrieves link state and physical negotiated bitrates for all physical LAN ports (LAN1–LAN4).
* **When to Call**: Call when troubleshooting local speed caps (e.g. distinguishing a 100 Mbps Fast Ethernet cable bottleneck from a 1000 Mbps Gigabit link) or detecting high RX discard/error rates.
* **Parameters**: *None*
* **Return Type**:
  ```json
  [
    {
      "port_id": 1,
      "status": "Up",
      "speed_mbps": 1000,
      "duplex": "Full",
      "bytes_sent": 89412040,
      "bytes_received": 194810204,
      "packets_sent": 128941,
      "packets_received": 249012,
      "errors_received": 0,
      "drops_received": 0
    },
    {
      "port_id": 2,
      "status": "Up",
      "speed_mbps": 100,
      "duplex": "Full",
      "bytes_sent": 104201,
      "bytes_received": 204910,
      "packets_sent": 1024,
      "packets_received": 1490,
      "errors_received": 12,
      "drops_received": 0
    }
  ]
  ```

#### 7. `gpon_list_port_forwards`
* **Description**: Lists all active NAT port forwarding rules on the router.
* **When to Call**: Call before adding rules to verify that the port is not already bound, or to audit exposed internal services.
* **Parameters**: *None*
* **Return Type**:
  ```json
  [
    {
      "oid": 1,
      "enabled": true,
      "external_port": 25565,
      "internal_port": 25565,
      "server_ip": "192.168.1.154",
      "protocol": "TCP"
    }
  ]
  ```

#### 8. `gpon_add_port_forward`
* **Description**: Creates an external WAN to internal LAN port forwarding rule.
* **When to Call**: Call when user wants to host a public game server (Minecraft, Valheim), web server, or remote access daemon.
* **Parameters**:
  * `external_port` (*integer*, 1–65535, required): Inbound WAN port.
  * `internal_port` (*integer*, 1–65535, required): Target LAN host port.
  * `server_ip` (*string*, valid IPv4, required): Internal IP address of host.
  * `protocol` (*string*, default `"TCP"`): `"TCP"`, `"UDP"`, or `"TCP/UDP"`.
* **Return Type**:
  ```json
  {
    "success": true,
    "external_port": 25565,
    "internal_port": 25565,
    "server_ip": "192.168.1.154",
    "protocol": "TCP",
    "message": "Port forward created: WAN 25565 -> LAN 192.168.1.154:25565 [TCP]"
  }
  ```

#### 9. `gpon_delete_port_forward`
* **Description**: Deletes an active port forwarding rule by its external WAN port.
* **When to Call**: Call when taking a service offline or closing exposed ports.
* **Parameters**:
  * `external_port` (*integer*, required): The external port of the rule to remove.
* **Return Type**:
  ```json
  {
    "success": true,
    "external_port": 25565,
    "message": "Port forward for external port 25565 deleted successfully."
  }
  ```

#### 10. `gpon_set_dmz`
* **Description**: Places a LAN host into the Demilitarized Zone (DMZ), forwarding all unmatched incoming WAN traffic to it, or disables DMZ.
* **When to Call**: Call to achieve Open NAT on consoles or when exposing complex multi-port game servers.
* **Parameters**:
  * `target_ip` (*string*, required): Target LAN IPv4 address (or `"0.0.0.0"` when disabling).
  * `enabled` (*boolean*, default `true`): `true` to enable, `false` to disable.
* **Return Type**:
  ```json
  {
    "success": true,
    "target_ip": "192.168.1.74",
    "enabled": true,
    "message": "DMZ enabled for 192.168.1.74."
  }
  ```

#### 11. `gpon_optimize_gaming`
* **Description**: One-click gaming macro executing 4 router modifications:
  1. Assigns target IP to DMZ (bypasses port collision / Moderate NAT).
  2. Disables naive DoS firewall filter (which causes false-positive packet drops during rapid UDP multiplayer state synchronization).
  3. Disables problematic Application Layer Gateways (SIP, RTSP, H.323) that corrupt voice chat and game packets.
  4. Enables UPnP for dynamic peer-to-peer matchmaking.
* **When to Call**: Call immediately whenever a user reports high in-game latency, packet bursts, "Strict NAT", or voice chat disconnection in games like Call of Duty, Fortnite, or Rocket League.
* **Parameters**:
  * `target_ip` (*string*, required): IPv4 address of the gaming rig or console.
* **Return Type**:
  ```json
  {
    "target_ip": "192.168.1.74",
    "dmz_configured": true,
    "dos_protection_disabled": true,
    "sip_alg_disabled": true,
    "upnp_enabled": true,
    "message": "Gaming optimizations successfully applied to target 192.168.1.74!"
  }
  ```

#### 12. `gpon_reboot`
* **Description**: Sends a software reboot signal to the GPON gateway.
* **When to Call**: Call when the gateway reports high uptime with memory leaks, or when requested by the user. Note: The connection will drop for ~90 seconds during reboot.
* **Parameters**: *None*
* **Return Type**:
  ```json
  {
    "success": true,
    "message": "Reboot signal successfully sent to the gateway. Connection will drop temporarily."
  }
  ```

---

## 3. Interface 2: CLI Subshell (`--json`)

Agents operating in bash environments (Antigravity terminal, Cursor terminal, Claude Code) should execute commands using `./gpon.sh <command> --json` (or `gpon <command> --json` when installed in PATH).

### Why Agents Prefer `--json`
- **Zero parsing fragility**: No regex scraping or ASCII table formatting.
- **Deterministic exit codes**:
  * `0`: Command succeeded. Output is valid JSON matching the success schema.
  * `1`: Command failed (runtime exception, auth error, network timeout). Output is valid JSON error object on stdout (or stderr text if process crashed before Python initialization).
  * `2`: Argument syntax error (missing required parameter).

### Success Envelope Schema
Every successful command wraps payload in a top-level `"status": "ok"` envelope:
```json
{
  "status": "ok",
  "data": { ... }
}
```

### Error Envelope Schema
When an error occurs during execution, a structured JSON error object is returned:
```json
{
  "status": "error",
  "error_type": "ValueError",
  "message": "No active port forward rule found for external port 9999"
}
```

### CLI Command Reference Table

| Subcommand | Arguments | Example Invocation |
| :--- | :--- | :--- |
| `status` | *(None)* | `./gpon.sh status --json` |
| `devices` | *(None)* | `./gpon.sh devices --json` |
| `optical` | *(None)* | `./gpon.sh optical --json` |
| `wifi status` | *(None)* | `./gpon.sh wifi status --json` |
| `wifi channel` | `<channel>` | `./gpon.sh wifi channel 6 --json` |
| `ethernet` | *(None)* | `./gpon.sh ethernet --json` |
| `ports list` | *(None)* | `./gpon.sh ports list --json` |
| `ports add` | `<ext> <int> <ip> [--proto TCP\|UDP]` | `./gpon.sh ports add 25565 25565 192.168.1.154 --proto TCP --json` |
| `ports del` | `<ext>` | `./gpon.sh ports del 25565 --json` |
| `dmz get` | *(None)* | `./gpon.sh dmz get --json` |
| `dmz set` | `<ip>` | `./gpon.sh dmz set 192.168.1.74 --json` |
| `dmz disable` | *(None)* | `./gpon.sh dmz disable --json` |
| `dns` | `<primary> <secondary>` | `./gpon.sh dns 1.1.1.1 1.0.0.1 --json` |
| `gaming` | `<ip>` | `./gpon.sh gaming 192.168.1.74 --json` |
| `reboot` | *(None)* | `./gpon.sh reboot --json` |
| `daemon` | `[--port 8254] [--host 127.0.0.1]` | `./gpon.sh daemon --port 8254` |

### Scripting & Piping Recipes with `jq`

Agents can compose quick diagnostics in bash subshells using `jq`:

```bash
# 1. Extract Public WAN IPv4
WAN_IP=$(./gpon.sh status --json | jq -r '.data.wan_ip')

# 2. Locate IP address of a gaming console by partial hostname
TARGET_IP=$(./gpon.sh devices --json | jq -r '.data[] | select(.hostname | test("playstation|xbox|switch"; "i")) | .ip_address')

# 3. Check if Optical Signal is in the Healthy range (between -8 and -25 dBm)
./gpon.sh optical --json | jq -e '.data.rx_power_dbm <= -8.0 and .data.rx_power_dbm >= -25.0'

# 4. Identify any active Ethernet link limited to 100 Mbps (cable bottleneck)
./gpon.sh ethernet --json | jq -r '.data[] | select(.status == "Up" and .speed_mbps < 1000) | "Port \(.port_id) is capped at \(.speed_mbps) Mbps!"'
```

---

## 4. Interface 3: REST API Daemon (Port 8254)

The REST API Daemon provides a persistent, typed HTTP microservice for external tools, multi-language SDKs (Java, Go, Python), and background processes.

### Niche Port Rationale: 8254
Standard ports like `5000` (macOS AirPlay), `8000` (dev servers), `8080` (Java / Tomcat / Spring), and `3000` (Node/Next.js) frequently collide in developer environments. GPON God-Mode binds to niche port **`8254`** (`http://127.0.0.1:8254`) by default.

### Launching the Daemon
```bash
# Via shell wrapper
./gpon.sh daemon --port 8254

# Via entrypoint script
gpon-api --port 8254

# Overriding port via environment variable
export GPON_API_PORT=8254
gpon-api
```

### Endpoints Specification

| Method | Endpoint | Request Body | Response Model | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | *None* | `Metadata` | Daemon info, status, doc links |
| `GET` | `/health` | *None* | `HealthCheck` | Fast liveness probe |
| `GET` | `/api/status` | *None* | `GatewayStatus` | Hardware, firmware, uptime, WAN IP |
| `GET` | `/api/devices` | *None* | `List[Device]` | Connected LAN/Wi-Fi devices |
| `GET` | `/api/optical` | *None* | `OpticalStatus` | GPON optical RX/TX telemetry |
| `GET` | `/api/wifi` | *None* | `WifiConfig` | 2.4GHz Wi-Fi configuration |
| `POST` | `/api/wifi/channel`| `{"channel": 6}` | `{"success": true}` | Change Wi-Fi channel (1–13) |
| `GET` | `/api/ethernet` | *None* | `List[EthernetPortStatus]` | Physical LAN port link speeds |
| `GET` | `/api/port-forwards` | *None* | `List[PortForwardRule]` | Active NAT port forwards |
| `POST` | `/api/port-forwards` | `PortForwardCreateRequest` | `{"success": true}` | Create new NAT port forward |
| `DELETE` | `/api/port-forwards/{port}` | *None* | `{"success": true}` | Delete rule by external port |
| `GET` | `/api/dmz` | *None* | `DMZConfig` | Query DMZ host status |
| `POST` | `/api/dmz` | `{"ip_address": "...", "enabled": true}` | `{"success": true}` | Configure DMZ host |
| `POST` | `/api/dns` | `{"primary_dns": "...", "secondary_dns": "..."}` | `{"success": true}` | Set DHCP DNS servers |
| `POST` | `/api/optimize-gaming` | `{"target_ip": "..."}` | `GamingOptimizationResult` | One-click gaming macro |
| `POST` | `/api/reboot` | `{"confirm": true}` | `{"success": true}` | Soft-reboot the gateway |

* **Interactive Swagger UI**: `http://127.0.0.1:8254/docs`
* **Raw OpenAPI 3.1 Spec**: `http://127.0.0.1:8254/openapi.json`

---

## 5. Agent Troubleshooting Recipes

Autonomous agents should follow these deterministic decision trees when resolving common user issues:

### Recipe A: Resolving Gaming Lag, High Ping, and Strict NAT

```
[User reports Gaming Lag / Strict NAT]
                   │
                   ▼
       1. Locate Device IP Address
          Call: `gpon_get_devices`
          Filter by Hostname or MAC
                   │
                   ▼
       2. Check Physical Link Speed
          Call: `gpon_get_ethernet_ports`
          Is port speed == 1000 Mbps?
          ├── No (100 Mbps) ──> Warn user: "Physical cable or switch limits link to 100M"
          └── Yes (Gigabit) ──> Proceed
                   │
                   ▼
       3. Inspect Optical Line Telemetry
          Call: `gpon_get_optical_status`
          Is RX power < -25 dBm?
          ├── Yes ──> Warn user: "Fiber attenuation is high (-X dBm); ISP line issue detected"
          └── No  ──> Optical link is healthy
                   │
                   ▼
       4. Apply One-Click Optimization
          Call: `gpon_optimize_gaming(target_ip)`
          - Puts target IP in DMZ (Open NAT)
          - Disables DoS filter false-positives
          - Disables SIP/RTSP voice chat ALGs
          - Enables UPnP for matchmaking
                   │
                   ▼
       5. Verify & Report Success to User
```

### Recipe B: Diagnosing Fiber Degradation from Optical RX dBm

The Nokia GPON optical transceiver uses an ITU-T G.984 GPON Class B+ optical module. The agent must evaluate the received optical power (`rx_power_dbm`) against standard optical thresholds:

| RX Power ($\text{dBm}$) | Status | Diagnosis & Agent Advice |
| :--- | :--- | :--- |
| **$> -8.0\text{ dBm}$** | ⚠️ **Optical Overload** | Signal is too hot. Optical receiver saturation may cause bit errors. Recommend an optical attenuator (3dB–5dB). |
| **$-8.0\text{ to } -24.9\text{ dBm}$** | ✅ **Healthy / Nominal** | Optical budget is optimal. Line operates with zero packet loss and maximum GPON downstream capacity (2.488 Gbps). |
| **$-25.0\text{ to } -27.9\text{ dBm}$** | 🟡 **Marginal / High Loss** | Increased packet jitter, micro-drops during weather events or OLT peak load. Recommend inspecting the fiber patch cord for bends or dust. |
| **$< -28.0\text{ dBm}$** | 🚨 **Critical Degradation** | Below optical sensitivity threshold (BER exceeds $10^{-4}$). The connection will frequently drop PPPoE sessions. Recommend immediate ISP technician dispatch to re-splice fiber or clean SC/APC connector. |

### Recipe C: Resolving Unknown LAN Devices & Port Mapping Conflicts

When configuring port forwards:
1. Call `gpon_get_devices` to map hostnames to IP addresses.
2. If hostname is `"Unknown"`, identify device manufacturer by matching the first 3 octets of `mac_address` (OUI):
   * `2c:cc:44` / `f8:46:1b` / `00:d9:d1`: Sony Interactive Entertainment (PlayStation)
   * `58:2f:40` / `7c:1e:52`: Microsoft (Xbox)
   * `98:b6:e9` / `e0:e7:51`: Nintendo Switch
   * `3c:22:fb` / `b0:83:fe`: PC Ethernet / Intel NIC
3. Call `gpon_list_port_forwards` before adding a rule. If target port is already mapped to another internal IP, prompt the user or choose an alternate external port (e.g. mapping external `25566` to internal `25565`).

---

## 6. Security Considerations for Autonomous Agents

1. **Localhost Bound**: The REST daemon defaults to `127.0.0.1`. Never expose port `8254` to public interfaces without a reverse-proxy enforcing TLS and Bearer authentication.
2. **Deterministic Validation**: All IP parameters are strictly parsed using Python `ipaddress`. Malformed strings or shell injection characters are rejected at the Pydantic schema layer before reaching router payloads.
3. **Session Protection**: Passwords are never stored in plaintext within tool outputs or daemon logs. Auth handshakes are strictly encrypted using SJCL RSA/AES.
