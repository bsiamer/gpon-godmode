package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/noecodes/gpon-godmode/sdk/go"
)

func main() {
	fmt.Println("==================================================")
	fmt.Println("  GPON God-Mode Go SDK - Microservice Example")
	fmt.Println("==================================================")

	// Initialize the client. By default, it connects to http://127.0.0.1:8254
	// (or the port set in GPON_API_PORT). CLI fallback is enabled so it can
	// fall back to executing `gpon <cmd> --json` if the daemon is offline.
	client := gpon.NewClient(
		gpon.WithCLIFallback(true),
		gpon.WithTimeout(10*time.Second),
	)

	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	fmt.Printf("[i] Target Daemon URL: %s\n\n", client.BaseURL())

	// 1. Query Gateway Health & Hardware Telemetry
	fmt.Println("--> [1/4] Querying Gateway Status...")
	status, err := client.GetStatus(ctx)
	if err != nil {
		if errors.Is(err, gpon.ErrDaemonUnreachable) {
			log.Printf("[-] Daemon is not running on %s. (Tip: start daemon with `python -m gpon_godmode.api`)\n", client.BaseURL())
		} else if errors.Is(err, gpon.ErrRouterAuth) {
			log.Printf("[-] Router authentication failed. Please verify ROUTER_USER and ROUTER_PASS in .env\n")
		} else {
			log.Printf("[-] Error retrieving gateway status: %v\n", err)
		}
	} else {
		fmt.Printf("    Model:       %s\n", status.ModelName)
		fmt.Printf("    Firmware:    %s\n", status.SoftwareVersion)
		fmt.Printf("    Hardware:    %s\n", status.HardwareVersion)
		fmt.Printf("    Uptime:      %s\n", status.UptimeFormatted)
		if status.CPUTemperature != nil {
			fmt.Printf("    CPU Temp:    %.1f °C\n", *status.CPUTemperature)
		}
		if status.WANIP != nil {
			fmt.Printf("    WAN IP:      %s\n", *status.WANIP)
		}
	}
	fmt.Println()

	// 2. Query Optical Fiber Transceiver Telemetry
	fmt.Println("--> [2/4] Querying GPON Optical Telemetry...")
	optical, err := client.GetOpticalStatus(ctx)
	if err != nil {
		log.Printf("[-] Error retrieving optical status: %v\n", err)
	} else {
		fmt.Printf("    Transmit Power (TX): %.2f dBm\n", optical.TXPowerDBm)
		fmt.Printf("    Receive Power (RX):  %.2f dBm\n", optical.RXPowerDBm)
		fmt.Printf("    Transceiver Temp:    %.1f °C\n", optical.TransceiverTemperature)
		fmt.Printf("    Laser Bias Current:  %.1f µA\n", optical.BiasCurrentUA)
		fmt.Printf("    Signal Quality:      %s\n", optical.SignalQuality)
	}
	fmt.Println()

	// 3. Query Connected Devices
	fmt.Println("--> [3/4] Querying Connected Devices...")
	devices, err := client.GetDevices(ctx)
	if err != nil {
		log.Printf("[-] Error retrieving connected devices: %v\n", err)
	} else {
		fmt.Printf("    Found %d connected/known devices:\n", len(devices))
		fmt.Printf("    %-16s | %-18s | %-8s | %-6s | %s\n", "IP Address", "MAC Address", "Type", "Active", "Hostname")
		fmt.Printf("    %s\n", "----------------------------------------------------------------------")
		for _, d := range devices {
			activeStr := "Yes"
			if !d.Active {
				activeStr = "No"
			}
			fmt.Printf("    %-16s | %-18s | %-8s | %-6s | %s\n", d.IPAddress, d.MACAddress, d.InterfaceType, activeStr, d.Hostname)
		}
	}
	fmt.Println()

	// 4. Query NAT Port Forwarding Rules
	fmt.Println("--> [4/4] Querying Active NAT Port Forwarding Rules...")
	rules, err := client.ListPortForwards(ctx)
	if err != nil {
		log.Printf("[-] Error listing port forwards: %v\n", err)
	} else {
		fmt.Printf("    Found %d active port forward rules:\n", len(rules))
		if len(rules) > 0 {
			fmt.Printf("    %-10s | %-10s | %-6s | %-16s | %s\n", "WAN Port", "LAN Port", "Proto", "Target IP", "Enabled")
			fmt.Printf("    %s\n", "-------------------------------------------------------------")
			for _, r := range rules {
				enabledStr := "Yes"
				if !r.Enabled {
					enabledStr = "No"
				}
				fmt.Printf("    %-10d | %-10d | %-6s | %-16s | %s\n", r.ExternalPort, r.InternalPort, r.Protocol, r.ServerIP, enabledStr)
			}
		} else {
			fmt.Println("    (No port forwarding rules currently configured)")
		}
	}
	fmt.Println()

	// Optional: Demonstrate port forward creation if test flag provided
	if len(os.Args) > 1 && os.Args[1] == "--test-forward" {
		fmt.Println("--> [Bonus] Adding test port forward (WAN 25565 -> 192.168.1.100:25565 TCP)...")
		err := client.AddPortForward(ctx, gpon.PortForwardRequest{
			ExternalPort: 25565,
			InternalPort: 25565,
			ServerIP:     "192.168.1.100",
			Protocol:     "TCP",
		})
		if err != nil {
			log.Printf("[-] Failed to create port forward: %v\n", err)
		} else {
			fmt.Println("    [+] Port forward rule created successfully!")
		}
	}

	fmt.Println("==================================================")
	fmt.Println("  Execution complete.")
	fmt.Println("==================================================")
}
