package com.gpon.godmode.plugin;

import com.gpon.godmode.GponClient;
import com.gpon.godmode.OpticalStatus;
import org.bukkit.ChatColor;
import org.bukkit.command.PluginCommand;
import org.bukkit.plugin.java.JavaPlugin;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Enumeration;
import java.util.logging.Level;

/**
 * Production-ready Spigot/Paper Minecraft plugin for automatic GPON Gateway
 * port forwarding and fiber optic transceiver health telemetry.
 */
public class GponPortForwardPlugin extends JavaPlugin {

    private GponClient gponClient;
    private String ruleName;
    private int forwardPort;
    private String localIp;
    private String protocol;
    private boolean autoForwardEnabled;
    private volatile boolean portForwarded = false;

    @Override
    public void onEnable() {
        // 1. Load configuration
        saveDefaultConfig();
        reloadConfig();

        String gponHost = getConfig().getString("gpon.host", "127.0.0.1");
        int gponPort = getConfig().getInt("gpon.port", 8254);
        boolean fallbackToCli = getConfig().getBoolean("gpon.fallback-to-cli", true);

        this.autoForwardEnabled = getConfig().getBoolean("port-forward.enabled", true);
        this.ruleName = getConfig().getString("port-forward.rule-name", "Minecraft-Auto");
        this.protocol = getConfig().getString("port-forward.protocol", "TCP/UDP");

        // 2. Resolve Minecraft server port
        int configuredPort = getConfig().getInt("port-forward.external-port", 0);
        if (configuredPort > 0) {
            this.forwardPort = configuredPort;
        } else {
            this.forwardPort = getServer().getPort();
            if (this.forwardPort <= 0) {
                this.forwardPort = 25565;
            }
        }

        // 3. Resolve local IP address
        String configuredIp = getConfig().getString("port-forward.server-ip", "auto");
        if (configuredIp != null && !configuredIp.equalsIgnoreCase("auto") && !configuredIp.trim().isEmpty()) {
            this.localIp = configuredIp.trim();
        } else {
            this.localIp = detectLocalIp();
        }

        getLogger().info(String.format("Initializing GPON God-Mode Client -> %s:%d (CLI fallback: %s)",
                gponHost, gponPort, fallbackToCli));

        // 4. Initialize GponClient
        this.gponClient = GponClient.builder()
                .host(gponHost)
                .port(gponPort)
                .fallbackToCli(fallbackToCli)
                .build();

        // 5. Register command executor and tab completer
        PluginCommand cmd = getCommand("gpon");
        if (cmd != null) {
            GponCommand executor = new GponCommand(this);
            cmd.setExecutor(executor);
            cmd.setTabCompleter(executor);
        }

        // 6. Asynchronous startup routine: Apply Port Forward & Check Optical Health
        getServer().getScheduler().runTaskAsynchronously(this, () -> {
            // Optical Health Check
            if (getConfig().getBoolean("optical.check-on-startup", true)) {
                checkOpticalHealth();
            }

            // Automatic Port Forwarding
            if (autoForwardEnabled) {
                applyPortForward();
            }
        });

        getLogger().info(ChatColor.GREEN + "GPON God-Mode Port Forward Plugin enabled successfully!");
    }

    @Override
    public void onDisable() {
        if (autoForwardEnabled && portForwarded && gponClient != null) {
            getLogger().info(String.format("Cleanly removing port forward rule '%s' (port %d)...", ruleName, forwardPort));
            try {
                boolean removed = gponClient.deletePortForward(forwardPort);
                if (removed) {
                    getLogger().info("Successfully removed GPON port forwarding rule.");
                } else {
                    getLogger().warning("Could not verify removal of port forwarding rule (already deleted or timed out).");
                }
            } catch (Exception e) {
                getLogger().log(Level.WARNING, "Failed to remove port forward rule on shutdown: " + e.getMessage(), e);
            }
        }
        getLogger().info("GPON God-Mode Plugin disabled.");
    }

    /**
     * Applies the Minecraft server NAT port forwarding rule asynchronously.
     */
    public boolean applyPortForward() {
        try {
            getLogger().info(String.format("Requesting port forward: WAN :%d -> LAN %s:%d [%s] (Rule: %s)...",
                    forwardPort, localIp, forwardPort, protocol, ruleName));

            boolean success = gponClient.addPortForward(ruleName, forwardPort, forwardPort, localIp, protocol);
            if (success) {
                this.portForwarded = true;
                getLogger().info(String.format(
                        "Port forward active: WAN :%d -> LAN %s:%d [%s] (Rule: %s)",
                        forwardPort, localIp, forwardPort, protocol, ruleName
                ));
                return true;
            } else {
                getLogger().warning("Gateway accepted request but returned success=false.");
                return false;
            }
        } catch (Exception e) {
            getLogger().log(Level.SEVERE, "Failed to create automatic port forward: " + e.getMessage(), e);
            return false;
        }
    }

    /**
     * Removes the active Minecraft server port forwarding rule.
     */
    public boolean removePortForward() {
        try {
            boolean success = gponClient.deletePortForward(forwardPort);
            if (success) {
                this.portForwarded = false;
            }
            return success;
        } catch (Exception e) {
            getLogger().log(Level.WARNING, "Failed to delete port forward: " + e.getMessage(), e);
            return false;
        }
    }

    /**
     * Checks and logs fiber optic transceiver signal telemetry.
     */
    public void checkOpticalHealth() {
        try {
            OpticalStatus optical = gponClient.getOpticalStatus();
            double rx = optical.getRxPowerDbm();
            double tx = optical.getTxPowerDbm();
            double temp = optical.getTransceiverTemperature();

            getLogger().info(String.format(
                    "Fiber Optic Signal Health: RX: %.2f dBm | TX: %.2f dBm | Temp: %.1f °C | Quality: %s",
                    rx, tx, temp, optical.getSignalQuality()
            ));

            double rxThreshold = getConfig().getDouble("optical.alert-threshold-rx-dbm", -25.0);
            if (rx < rxThreshold) {
                getLogger().warning(String.format(
                        "[FIBER WARNING] Optical receive power (%.2f dBm) is degraded below threshold (%.2f dBm)! " +
                        "Fiber patch cable may be bent, dirty, or damaged.",
                        rx, rxThreshold
                ));
            } else if (rx > -8.0) {
                getLogger().warning(String.format(
                        "[FIBER WARNING] Optical receive power (%.2f dBm) is unusually hot (normal: -8 to -25 dBm).",
                        rx
                ));
            } else {
                getLogger().info("Fiber optic link signal is optimal (-8 to -25 dBm).");
            }
        } catch (Exception e) {
            getLogger().warning("Could not query fiber optical status: " + e.getMessage());
        }
    }

    /**
     * Detects the first non-loopback, site-local IPv4 address on the machine.
     */
    private String detectLocalIp() {
        try {
            String srvIp = getServer().getIp();
            if (srvIp != null && !srvIp.isEmpty() && !"0.0.0.0".equals(srvIp)) {
                return srvIp;
            }

            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces.hasMoreElements()) {
                NetworkInterface iface = interfaces.nextElement();
                if (iface.isLoopback() || !iface.isUp() || iface.isVirtual()) continue;

                Enumeration<InetAddress> addresses = iface.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress addr = addresses.nextElement();
                    if (!addr.isLoopbackAddress() && addr instanceof Inet4Address && addr.isSiteLocalAddress()) {
                        return addr.getHostAddress();
                    }
                }
            }
        } catch (Exception e) {
            getLogger().warning("Exception while detecting local IP: " + e.getMessage());
        }
        return "127.0.0.1";
    }

    public GponClient getGponClient() {
        return gponClient;
    }

    public String getRuleName() {
        return ruleName;
    }

    public int getForwardPort() {
        return forwardPort;
    }

    public String getLocalIp() {
        return localIp;
    }

    public String getProtocol() {
        return protocol;
    }

    public boolean isPortForwarded() {
        return portForwarded;
    }
}
