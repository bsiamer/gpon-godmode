package com.gpon.godmode.plugin;

import com.gpon.godmode.*;
import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Command executor and tab completer for /gpon.
 */
public class GponCommand implements CommandExecutor, TabCompleter {

    private final GponPortForwardPlugin plugin;

    public GponCommand(GponPortForwardPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!sender.hasPermission("gpon.admin")) {
            sender.sendMessage(ChatColor.RED + "You do not have permission to execute GPON Gateway commands.");
            return true;
        }

        if (args.length == 0 || args[0].equalsIgnoreCase("help")) {
            sendHelp(sender, label);
            return true;
        }

        String sub = args[0].toLowerCase();

        // Run network/client calls asynchronously to avoid blocking the server tick
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try {
                GponClient client = plugin.getGponClient();
                if (client == null) {
                    sender.sendMessage(ChatColor.RED + "[GPON] Client is not initialized.");
                    return;
                }

                switch (sub) {
                    case "status":
                        handleStatus(sender, client);
                        break;
                    case "optical":
                        handleOptical(sender, client);
                        break;
                    case "ping":
                        handlePing(sender, client);
                        break;
                    case "forward":
                        handleForward(sender);
                        break;
                    case "unforward":
                        handleUnforward(sender);
                        break;
                    case "devices":
                        handleDevices(sender, client);
                        break;
                    case "gaming":
                        handleGaming(sender, client, args);
                        break;
                    case "reboot":
                        handleReboot(sender, client, args);
                        break;
                    default:
                        sender.sendMessage(ChatColor.RED + "Unknown subcommand '" + sub + "'. Type /" + label + " help for usage.");
                        break;
                }
            } catch (Exception e) {
                sender.sendMessage(ChatColor.RED + "[GPON Error] " + e.getMessage());
            }
        });

        return true;
    }

    private void handleStatus(CommandSender sender, GponClient client) {
        sender.sendMessage(ChatColor.GOLD + "=== GPON Gateway Status ===");
        try {
            GatewayStatus s = client.getStatus();
            sender.sendMessage(ChatColor.GRAY + "Model: " + ChatColor.AQUA + s.getModelName());
            sender.sendMessage(ChatColor.GRAY + "Hardware: " + ChatColor.AQUA + s.getHardwareVersion());
            sender.sendMessage(ChatColor.GRAY + "Software: " + ChatColor.AQUA + s.getSoftwareVersion());
            sender.sendMessage(ChatColor.GRAY + "Uptime: " + ChatColor.AQUA + s.getUptimeFormatted());
            if (s.getCpuTemperature() != null) {
                sender.sendMessage(ChatColor.GRAY + "CPU Temp: " + ChatColor.AQUA + s.getCpuTemperature() + " °C");
            }
            sender.sendMessage(ChatColor.GRAY + "WAN IP: " + ChatColor.GREEN + (s.getWanIp().isEmpty() ? "N/A" : s.getWanIp()));
            sender.sendMessage(ChatColor.GRAY + "WAN Status: " + (s.isWanConnected() ? ChatColor.GREEN : ChatColor.RED) + s.getWanStatus());
        } catch (Exception e) {
            sender.sendMessage(ChatColor.RED + "Failed to retrieve gateway status: " + e.getMessage());
        }
    }

    private void handleOptical(CommandSender sender, GponClient client) {
        sender.sendMessage(ChatColor.GOLD + "=== GPON Fiber Optic Telemetry ===");
        try {
            OpticalStatus opt = client.getOpticalStatus();
            ChatColor rxColor = opt.isSignalOptimal() ? ChatColor.GREEN : ChatColor.RED;

            sender.sendMessage(ChatColor.GRAY + "RX Power: " + rxColor + String.format("%.2f dBm", opt.getRxPowerDbm()) +
                    ChatColor.DARK_GRAY + " (Target: -8 to -25 dBm)");
            sender.sendMessage(ChatColor.GRAY + "TX Power: " + ChatColor.AQUA + String.format("%.2f dBm", opt.getTxPowerDbm()));
            sender.sendMessage(ChatColor.GRAY + "Transceiver Temp: " + ChatColor.AQUA + String.format("%.1f °C", opt.getTransceiverTemperature()));
            sender.sendMessage(ChatColor.GRAY + "Laser Bias: " + ChatColor.AQUA + String.format("%.1f µA", opt.getBiasCurrentUa()));
            sender.sendMessage(ChatColor.GRAY + "Quality: " + (opt.isSignalOptimal() ? ChatColor.GREEN : ChatColor.YELLOW) + opt.getSignalQuality());

            if (opt.isSignalDegraded()) {
                sender.sendMessage(ChatColor.RED + "WARNING: Fiber signal is outside optimal range! Cable attenuation or bend detected.");
            } else {
                sender.sendMessage(ChatColor.GREEN + "Fiber optic link is performing within optimal parameters.");
            }
        } catch (Exception e) {
            sender.sendMessage(ChatColor.RED + "Failed to retrieve optical status: " + e.getMessage());
        }
    }

    private void handlePing(CommandSender sender, GponClient client) {
        sender.sendMessage(ChatColor.GRAY + "Pinging GPON REST daemon...");
        long start = System.currentTimeMillis();
        boolean healthy = client.isHealthy();
        long elapsed = System.currentTimeMillis() - start;

        if (healthy) {
            sender.sendMessage(ChatColor.GREEN + String.format("[GPON] Daemon responded in %d ms (Status: Healthy)", elapsed));
        } else {
            sender.sendMessage(ChatColor.YELLOW + String.format("[GPON] Daemon ping returned non-healthy response in %d ms (CLI fallback active)", elapsed));
        }
    }

    private void handleForward(CommandSender sender) {
        sender.sendMessage(ChatColor.GRAY + "Applying GPON NAT port forwarding rule...");
        boolean success = plugin.applyPortForward();
        if (success) {
            sender.sendMessage(ChatColor.GREEN + String.format("Port forward active: WAN :%d -> LAN %s:%d [%s]",
                    plugin.getForwardPort(), plugin.getLocalIp(), plugin.getForwardPort(), plugin.getProtocol()));
        } else {
            sender.sendMessage(ChatColor.RED + "Failed to apply port forwarding rule. Check console logs.");
        }
    }

    private void handleUnforward(CommandSender sender) {
        sender.sendMessage(ChatColor.GRAY + "Removing GPON NAT port forwarding rule...");
        boolean success = plugin.removePortForward();
        if (success) {
            sender.sendMessage(ChatColor.GREEN + "Port forwarding rule successfully removed.");
        } else {
            sender.sendMessage(ChatColor.RED + "Failed to remove port forwarding rule.");
        }
    }

    private void handleDevices(CommandSender sender, GponClient client) {
        sender.sendMessage(ChatColor.GOLD + "=== Connected Devices ===");
        try {
            List<Device> devs = client.getDevices();
            sender.sendMessage(ChatColor.GRAY + "Total active clients: " + ChatColor.AQUA + devs.size());
            for (Device d : devs) {
                String host = d.getHostname().isEmpty() ? "<unknown>" : d.getHostname();
                String iface = d.isWifi() ? ChatColor.LIGHT_PURPLE + "[Wi-Fi]" : ChatColor.BLUE + "[LAN]";
                sender.sendMessage(String.format("%s %s%s %s(%s) %s%s",
                        iface,
                        ChatColor.GREEN, d.getIpAddress(),
                        ChatColor.GRAY, d.getMacAddress(),
                        ChatColor.WHITE, host));
            }
        } catch (Exception e) {
            sender.sendMessage(ChatColor.RED + "Failed to list devices: " + e.getMessage());
        }
    }

    private void handleGaming(CommandSender sender, GponClient client, String[] args) {
        String target = args.length > 1 ? args[1] : plugin.getLocalIp();
        sender.sendMessage(ChatColor.GRAY + "Applying gaming optimizations (DMZ + UPnP + DoS bypass) to " + target + "...");
        try {
            GamingOptimizationResult res = client.optimizeGaming(target);
            sender.sendMessage(ChatColor.GREEN + "Gaming Optimization Applied:");
            sender.sendMessage(ChatColor.GRAY + "  Target: " + ChatColor.AQUA + res.getTargetIp());
            sender.sendMessage(ChatColor.GRAY + "  DMZ: " + (res.isDmzConfigured() ? ChatColor.GREEN + "Enabled" : ChatColor.RED + "Disabled"));
            sender.sendMessage(ChatColor.GRAY + "  DoS Filter: " + (res.isDosProtectionDisabled() ? ChatColor.GREEN + "Bypassed" : ChatColor.GRAY + "Active"));
            sender.sendMessage(ChatColor.GRAY + "  SIP ALG: " + (res.isSipAlgDisabled() ? ChatColor.GREEN + "Disabled" : ChatColor.GRAY + "Active"));
            sender.sendMessage(ChatColor.GRAY + "  UPnP: " + (res.isUpnpEnabled() ? ChatColor.GREEN + "Enabled" : ChatColor.RED + "Disabled"));
        } catch (Exception e) {
            sender.sendMessage(ChatColor.RED + "Failed to apply gaming optimization: " + e.getMessage());
        }
    }

    private void handleReboot(CommandSender sender, GponClient client, String[] args) {
        if (args.length < 2 || !args[1].equalsIgnoreCase("confirm")) {
            sender.sendMessage(ChatColor.RED + "DANGER: This will reboot the fiber gateway! Confirm with: /gpon reboot confirm");
            return;
        }

        sender.sendMessage(ChatColor.YELLOW + "Transmitting soft-reboot command to GPON Gateway...");
        try {
            boolean ok = client.reboot();
            if (ok) {
                sender.sendMessage(ChatColor.GREEN + "Gateway accepted reboot command. The connection will cycle within 30-60 seconds.");
            } else {
                sender.sendMessage(ChatColor.RED + "Gateway returned false for reboot command.");
            }
        } catch (Exception e) {
            sender.sendMessage(ChatColor.RED + "Reboot command failed: " + e.getMessage());
        }
    }

    private void sendHelp(CommandSender sender, String label) {
        sender.sendMessage(ChatColor.GOLD + "=== GPON God-Mode Commands ===");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " status" + ChatColor.GRAY + " - Gateway hardware, uptime & WAN IP");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " optical" + ChatColor.GRAY + " - Fiber optic transceiver signal health");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " ping" + ChatColor.GRAY + " - Test latency to REST API daemon");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " forward" + ChatColor.GRAY + " - Force-apply NAT port forwarding");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " unforward" + ChatColor.GRAY + " - Remove NAT port forwarding rule");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " devices" + ChatColor.GRAY + " - List connected LAN / Wi-Fi clients");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " gaming [ip]" + ChatColor.GRAY + " - Low-latency DMZ/UPnP optimization");
        sender.sendMessage(ChatColor.YELLOW + "/" + label + " reboot confirm" + ChatColor.GRAY + " - Soft-reboot the gateway");
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (!sender.hasPermission("gpon.admin")) {
            return Collections.emptyList();
        }

        if (args.length == 1) {
            List<String> subs = Arrays.asList("status", "optical", "ping", "forward", "unforward", "devices", "gaming", "reboot", "help");
            List<String> matches = new ArrayList<>();
            for (String s : subs) {
                if (s.startsWith(args[0].toLowerCase())) {
                    matches.add(s);
                }
            }
            return matches;
        }

        if (args.length == 2 && args[0].equalsIgnoreCase("reboot")) {
            return Collections.singletonList("confirm");
        }

        if (args.length == 2 && args[0].equalsIgnoreCase("gaming")) {
            return Collections.singletonList(plugin.getLocalIp());
        }

        return Collections.emptyList();
    }
}
