# GPON God-Mode Go SDK 🚀

The official, production-ready Go SDK for **GPON God-Mode** (Nokia/Alcatel-Lucent G-240W-F Home Gateways).

Engineered specifically for Go microservices, game server backends, network monitoring daemons, and autonomous agent systems.

---

## Highlights

- ⚡ **Zero Third-Party Dependencies**: Built exclusively on the Go standard library (`net/http`, `context`, `encoding/json`).
- ⏱️ **Context-Aware**: Full `context.Context` propagation across all calls with cancellation and deadline support.
- 🔌 **Default Port 8254**: Automatically targets the local REST API daemon on port `8254` (read from `GPON_API_PORT` or configurable via options).
- 🛡️ **Robust Error Handling**: Idiomatic error wrapping (`fmt.Errorf("%w", err)`) and structured `APIError` with full `errors.Is` support (`ErrDaemonUnreachable`, `ErrRouterAuth`, `ErrRuleNotFound`, etc.).
- 🔄 **Autonomous CLI Fallback**: Optional seamless fallback to executing `gpon <command> --json` via `os/exec` if the REST daemon is offline.

---

## Installation

```bash
go get github.com/bsiamer/gpon-godmode/sdk/go
```

---

## Quick Start

```go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/noecodes/gpon-godmode/sdk/go"
)

func main() {
	// Initialize client (defaults to http://127.0.0.1:8254)
	client := gpon.NewClient(
		gpon.WithCLIFallback(true),
		gpon.WithTimeout(10*time.Second),
	)

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	// 1. Get Gateway Status & System Health
	status, err := client.GetStatus(ctx)
	if err != nil {
		log.Fatalf("Failed to fetch gateway status: %v", err)
	}
	fmt.Printf("Model: %s | Firmware: %s | Uptime: %s\n",
		status.ModelName, status.SoftwareVersion, status.UptimeFormatted)

	// 2. Query Optical Fiber Telemetry (dBm)
	optical, err := client.GetOpticalStatus(ctx)
	if err != nil {
		log.Fatalf("Failed to query optical telemetry: %v", err)
	}
	fmt.Printf("Fiber RX: %.2f dBm | TX: %.2f dBm | Temp: %.1f °C | Quality: %s\n",
		optical.RXPowerDBm, optical.TXPowerDBm, optical.TransceiverTemperature, optical.SignalQuality)

	// 3. List Connected LAN & Wi-Fi Clients
	devices, err := client.GetDevices(ctx)
	if err != nil {
		log.Fatalf("Failed to query devices: %v", err)
	}
	for _, dev := range devices {
		fmt.Printf("Host: %-20s | IP: %-15s | MAC: %s\n", dev.Hostname, dev.IPAddress, dev.MACAddress)
	}
}
```

---

## Daemon & Port Configuration

The SDK connects to the REST daemon using the following resolution order:

1. **Functional Option**: `gpon.WithBaseURL("http://192.168.1.50:8254")` or `gpon.WithAPIPort(8254)`
2. **Environment Variable**: `GPON_API_URL` or `GPON_DAEMON_URL`
3. **Host & Port Environment Variables**: `http://${GPON_API_HOST:-127.0.0.1}:${GPON_API_PORT:-8254}`
4. **Default**: `http://127.0.0.1:8254`

### Starting the Daemon

```bash
# In the gpon-godmode repository:
./gpon.sh daemon --port 8254
# Or using Python directly:
python -m gpon_godmode.api --port 8254
```

---

## Client Options

```go
client := gpon.NewClient(
    // Override the daemon URL
    gpon.WithBaseURL("http://127.0.0.1:8254"),

    // Override the port on 127.0.0.1
    gpon.WithAPIPort(8254),

    // Custom HTTP client (e.g. custom transport or proxy)
    gpon.WithHTTPClient(&http.Client{Timeout: 30 * time.Second}),

    // Custom timeout
    gpon.WithTimeout(10 * time.Second),

    // Enable CLI fallback when the HTTP daemon is down
    gpon.WithCLIFallback(true),

    // Custom path to gpon CLI binary or script
    gpon.WithCLIPath("/usr/local/bin/gpon"),
)
```

---

## API Reference

### 1. Gateway Status & Health
```go
status, err := client.GetStatus(ctx)
// Returns *GatewayStatus:
// - ModelName: e.g. "G-240W-F"
// - HardwareVersion: e.g. "3FE46597AAAA"
// - SoftwareVersion: e.g. "3FE46606BGBB24"
// - UptimeSeconds: int64
// - UptimeFormatted: "17d 6h 39m (1492750s)"
// - CPUTemperature: *float64
// - WANIP: *string
// - WANStatus: *string
```

### 2. Connected Devices Discovery
```go
devices, err := client.GetDevices(ctx)
// Returns []Device:
// - OID: router internal index
// - Hostname: device identifier
// - IPAddress: e.g. "192.168.1.154"
// - MACAddress: e.g. "b0:83:fe:5d:29:29"
// - Active: true/false
// - InterfaceType: "Ethernet" or "802.11"
```

### 3. Optical Fiber Telemetry
```go
optical, err := client.GetOpticalStatus(ctx)
// Returns *OpticalStatus:
// - TXPowerDBm: Transmit laser power in dBm
// - RXPowerDBm: Receive optical power in dBm (target: -8 to -25 dBm)
// - TransceiverTemperature: Sensor temperature in Celsius
// - BiasCurrentUA: Laser bias current in microamperes
// - SignalQuality: ITU-T G.984 assessment (e.g. "Excellent / Healthy")
```

### 4. NAT Port Forwarding

```go
// List active rules
rules, err := client.ListPortForwards(ctx)

// Add a new port forward rule (e.g. Minecraft server WAN 25565 -> LAN 192.168.1.154:25565 TCP)
err = client.AddPortForward(ctx, gpon.PortForwardRequest{
    ExternalPort: 25565,
    InternalPort: 25565,
    ServerIP:     "192.168.1.154",
    Protocol:     "TCP", // "TCP", "UDP", or "TCP/UDP"
})

// Delete a port forward rule by external port number or name
err = client.DeletePortForward(ctx, "25565")
```

### 5. DMZ Host Configuration
```go
// Put gaming rig or reverse proxy into DMZ
err := client.SetDMZ(ctx, "192.168.1.74", true)

// Disable DMZ
err := client.SetDMZ(ctx, "0.0.0.0", false)
```

### 6. One-Click Gaming Optimization Macro
```go
// Places target IP in DMZ, disables DoS firewall filter false-positives,
// disables SIP/RTSP ALGs that corrupt voice packets, and enables UPnP.
res, err := client.OptimizeGaming(ctx, "192.168.1.74")
if err != nil {
    log.Fatalf("Optimization failed: %v", err)
}
fmt.Println(res.Message)
```

### 7. Safe Remote Reboot
```go
// Soft-reboots the GPON Gateway
err := client.Reboot(ctx)
```

---

## Error Handling

All errors returned by the SDK wrap sentinel errors or the `APIError` type:

```go
status, err := client.GetStatus(ctx)
if err != nil {
    switch {
    case errors.Is(err, gpon.ErrDaemonUnreachable):
        // HTTP daemon is not running and CLI fallback is disabled or failed
        log.Println("Daemon offline. Please launch via: ./gpon.sh daemon")

    case errors.Is(err, gpon.ErrRouterAuth):
        // Invalid ROUTER_USER / ROUTER_PASS credentials
        log.Println("Router authentication rejected (HTTP 401)")

    case errors.Is(err, gpon.ErrRuleNotFound):
        // Requested port forward rule does not exist (HTTP 404)
        log.Println("Target port forward rule not found")

    case errors.Is(err, gpon.ErrInvalidParameter):
        // Invalid port range, malformed IP address, etc. (HTTP 400/422)
        log.Println("Invalid parameters supplied")

    default:
        var apiErr *gpon.APIError
        if errors.As(err, &apiErr) {
            log.Printf("Daemon returned status %d: %s\n", apiErr.StatusCode, apiErr.Detail)
        } else {
            log.Printf("Unexpected error: %v\n", err)
        }
    }
}
```

---

## Running the Example

An executable microservice example is included in `example/`:

```bash
cd sdk/go
go run ./example/main.go
```

To test adding a sample port forward:
```bash
go run ./example/main.go --test-forward
```

---

## Running SDK Unit Tests

```bash
cd sdk/go
go test -v ./...
```
