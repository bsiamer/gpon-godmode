package com.gpon.godmode;

import com.gpon.godmode.json.JsonObject;
import java.util.Objects;

/**
 * Connected LAN or Wi-Fi client device discovered on the GPON Gateway.
 */
public class Device {

    private final int oid;
    private final String hostname;
    private final String ipAddress;
    private final String macAddress;
    private final boolean active;
    private final String interfaceType;

    public Device(
        int oid,
        String hostname,
        String ipAddress,
        String macAddress,
        boolean active,
        String interfaceType
    ) {
        this.oid = oid;
        this.hostname = hostname != null ? hostname : "";
        this.ipAddress = ipAddress != null ? ipAddress : "";
        this.macAddress = macAddress != null ? macAddress : "";
        this.active = active;
        this.interfaceType = interfaceType != null ? interfaceType : "Ethernet";
    }

    public static Device fromJson(JsonObject json) {
        if (json == null) return null;
        int oid = json.getInt(0, "oid", "id");
        String host = json.getString("", "hostname", "host_name", "name");
        String ip = json.getString("", "ip_address", "ipAddress", "ip");
        String mac = json.getString("", "mac_address", "macAddress", "mac");
        boolean active = json.getBoolean(true, "active", "is_active", "online");
        String iface = json.getString("Ethernet", "interface_type", "interfaceType", "type");

        return new Device(oid, host, ip, mac, active, iface);
    }

    public int getOid() {
        return oid;
    }

    public String getHostname() {
        return hostname;
    }

    public String getIpAddress() {
        return ipAddress;
    }

    public String getMacAddress() {
        return macAddress;
    }

    public boolean isActive() {
        return active;
    }

    public String getInterfaceType() {
        return interfaceType;
    }

    public boolean isWifi() {
        return interfaceType.contains("802.11") || interfaceType.equalsIgnoreCase("Wifi") || interfaceType.equalsIgnoreCase("Wireless");
    }

    public boolean isEthernet() {
        return !isWifi();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Device)) return false;
        Device device = (Device) o;
        return Objects.equals(ipAddress, device.ipAddress) &&
                Objects.equals(macAddress, device.macAddress);
    }

    @Override
    public int hashCode() {
        return Objects.hash(ipAddress, macAddress);
    }

    @Override
    public String toString() {
        return "Device{" +
                "ip='" + ipAddress + '\'' +
                ", mac='" + macAddress + '\'' +
                ", host='" + hostname + '\'' +
                ", active=" + active +
                ", type='" + interfaceType + '\'' +
                '}';
    }
}
