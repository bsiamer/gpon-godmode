package com.gpon.godmode;

import com.gpon.godmode.json.JsonObject;
import java.util.Objects;

/**
 * NAT Port Forwarding (Virtual Server) rule on the GPON Gateway.
 */
public class PortForwardRule {

    private final Integer oid;
    private final String name;
    private final boolean enabled;
    private final int externalPort;
    private final int internalPort;
    private final String serverIp;
    private final String protocol;

    public PortForwardRule(
        Integer oid,
        String name,
        boolean enabled,
        int externalPort,
        int internalPort,
        String serverIp,
        String protocol
    ) {
        this.oid = oid;
        this.name = name != null ? name : "";
        this.enabled = enabled;
        this.externalPort = externalPort;
        this.internalPort = internalPort;
        this.serverIp = serverIp != null ? serverIp : "";
        this.protocol = protocol != null ? protocol.toUpperCase() : "TCP";
    }

    public PortForwardRule(
        boolean enabled,
        int externalPort,
        int internalPort,
        String serverIp,
        String protocol
    ) {
        this(null, "", enabled, externalPort, internalPort, serverIp, protocol);
    }

    public static PortForwardRule fromJson(JsonObject json) {
        if (json == null) return null;
        Integer oid = json.getInteger("oid", "id");
        String name = json.getString("", "name", "rule_name", "ruleName", "description", "service_name");
        boolean enabled = json.getBoolean(true, "enabled", "status");
        int ext = json.getInt(0, "external_port", "externalPort", "wan_port", "ext_port");
        int inPort = json.getInt(ext, "internal_port", "internalPort", "lan_port", "int_port");
        String ip = json.getString("", "server_ip", "serverIp", "lan_ip", "ip");
        String proto = json.getString("TCP", "protocol", "proto");

        return new PortForwardRule(oid, name, enabled, ext, inPort, ip, proto);
    }

    public Integer getOid() {
        return oid;
    }

    public String getName() {
        return name;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public int getExternalPort() {
        return externalPort;
    }

    public int getInternalPort() {
        return internalPort;
    }

    public String getServerIp() {
        return serverIp;
    }

    public String getProtocol() {
        return protocol;
    }

    public JsonObject toJson() {
        JsonObject json = new JsonObject();
        if (oid != null) json.put("oid", oid);
        if (!name.isEmpty()) json.put("name", name);
        json.put("enabled", enabled);
        json.put("external_port", externalPort);
        json.put("internal_port", internalPort);
        json.put("server_ip", serverIp);
        json.put("protocol", protocol);
        return json;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof PortForwardRule)) return false;
        PortForwardRule that = (PortForwardRule) o;
        return externalPort == that.externalPort &&
                internalPort == that.internalPort &&
                Objects.equals(serverIp, that.serverIp) &&
                Objects.equals(protocol, that.protocol);
    }

    @Override
    public int hashCode() {
        return Objects.hash(externalPort, internalPort, serverIp, protocol);
    }

    @Override
    public String toString() {
        return "PortForwardRule{" +
                (name.isEmpty() ? "" : "'" + name + "': ") +
                "WAN :" + externalPort + " -> LAN " + serverIp + ":" + internalPort +
                " [" + protocol + "]" +
                (enabled ? " (enabled)" : " (disabled)") +
                '}';
    }
}
