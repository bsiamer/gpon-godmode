package com.gpon.godmode;

import java.util.List;

/**
 * Standalone demo application showing how any Java backend or standalone service
 * integrates with GPON God-Mode via {@link GponClient}.
 */
public class StandaloneExample {

    public static void main(String[] args) {
        System.out.println("==================================================");
        System.out.println("  GPON God-Mode Java SDK - Standalone Demo");
        System.out.println("==================================================\n");

        // 1. Initialize client (defaults to http://127.0.0.1:8254 with CLI fallback)
        GponClient client = GponClient.builder()
                .host("127.0.0.1")
                .port(8254)
                .fallbackToCli(true)
                .build();

        System.out.println("[*] Target API Daemon: " + client.getBaseUrl());
        System.out.println("[*] CLI Fallback: " + (client.isFallbackToCliEnabled() ? "Enabled" : "Disabled"));
        System.out.println();

        try {
            // 2. Gateway Status
            System.out.println(">>> 1. Fetching Gateway Status...");
            GatewayStatus status = client.getStatus();
            System.out.println("  Model:        " + status.getModelName());
            System.out.println("  Hardware:     " + status.getHardwareVersion());
            System.out.println("  Software:     " + status.getSoftwareVersion());
            System.out.println("  Bootloader:   " + status.getBootVersion());
            System.out.println("  Uptime:       " + status.getUptimeFormatted() + " (" + status.getUptimeSeconds() + "s)");
            if (status.getCpuTemperature() != null) {
                System.out.println("  CPU Temp:     " + status.getCpuTemperature() + " °C");
            }
            System.out.println("  WAN IP:       " + (status.getWanIp().isEmpty() ? "N/A" : status.getWanIp()));
            System.out.println("  WAN Status:   " + status.getWanStatus());
            System.out.println();

            // 3. Fiber Optic Telemetry
            System.out.println(">>> 2. Checking Fiber Optical Health...");
            OpticalStatus optical = client.getOpticalStatus();
            System.out.printf("  RX Power:     %.2f dBm (Optimal: -8 to -25 dBm)%n", optical.getRxPowerDbm());
            System.out.printf("  TX Power:     %.2f dBm%n", optical.getTxPowerDbm());
            System.out.printf("  Laser Temp:   %.1f °C%n", optical.getTransceiverTemperature());
            System.out.printf("  Bias Current: %.1f µA%n", optical.getBiasCurrentUa());
            System.out.println("  Quality:      " + optical.getSignalQuality());
            if (optical.isSignalOptimal()) {
                System.out.println("  Assessment:   [OPTIMAL] Fiber link is healthy.");
            } else {
                System.out.println("  Assessment:   [WARNING] Signal is outside normal range. Check fiber patch cable.");
            }
            System.out.println();

            // 4. Connected Devices
            System.out.println(">>> 3. Discovering Connected LAN / Wi-Fi Devices...");
            List<Device> devices = client.getDevices();
            System.out.printf("  Found %d connected devices:%n", devices.size());
            for (Device dev : devices) {
                System.out.printf("  - %-15s | %-17s | %-8s | %s%n",
                        dev.getIpAddress(),
                        dev.getMacAddress(),
                        dev.getInterfaceType(),
                        dev.getHostname().isEmpty() ? "<unknown>" : dev.getHostname());
            }
            System.out.println();

            // 5. Port Forwarding
            System.out.println(">>> 4. Managing NAT Port Forwarding Rules...");
            List<PortForwardRule> existingRules = client.listPortForwards();
            System.out.printf("  Active rules: %d%n", existingRules.size());
            for (PortForwardRule r : existingRules) {
                System.out.printf("  - WAN :%-5d -> LAN %s:%-5d [%s]%n",
                        r.getExternalPort(), r.getServerIp(), r.getInternalPort(), r.getProtocol());
            }

            // Demonstrate adding a rule
            String testRuleName = "Demo-Minecraft";
            int testPort = 25565;
            String targetIp = "192.168.1.150";

            System.out.printf("%n  Adding test rule: WAN :%d -> LAN %s:%d [TCP/UDP]...%n", testPort, targetIp, testPort);
            boolean added = client.addPortForward(testRuleName, testPort, testPort, targetIp, "TCP/UDP");
            System.out.println("  Rule added successfully: " + added);

            // Clean up test rule
            System.out.printf("  Cleaning up test rule '%s'...%n", testRuleName);
            boolean deleted = client.deletePortForward(testPort);
            System.out.println("  Rule deleted successfully: " + deleted);
            System.out.println();

            // 6. Gaming Optimization Macro
            System.out.println(">>> 5. Low-Latency Gaming Macro (DMZ + UPnP + DoS Bypass)...");
            GamingOptimizationResult gaming = client.optimizeGaming(targetIp);
            System.out.println("  Target IP:    " + gaming.getTargetIp());
            System.out.println("  DMZ:          " + (gaming.isDmzConfigured() ? "Configured" : "Off"));
            System.out.println("  DoS Bypass:   " + (gaming.isDosProtectionDisabled() ? "Active" : "Off"));
            System.out.println("  SIP ALG Off:  " + (gaming.isSipAlgDisabled() ? "Yes" : "No"));
            System.out.println("  UPnP:         " + (gaming.isUpnpEnabled() ? "Enabled" : "Disabled"));
            System.out.println("  Message:      " + gaming.getMessage());
            System.out.println();

            System.out.println("[+] GPON God-Mode Java SDK demo completed successfully!");

        } catch (GponException e) {
            System.err.println("[!] GponException caught: " + e.getMessage());
            if (e.getCause() != null) {
                System.err.println("[!] Cause: " + e.getCause().getMessage());
            }
        }
    }
}
