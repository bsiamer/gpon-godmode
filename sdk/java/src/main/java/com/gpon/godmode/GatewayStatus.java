package com.gpon.godmode;

import com.gpon.godmode.json.JsonObject;
import java.util.Objects;

/**
 * Hardware information, firmware revision, uptime, and WAN connectivity status
 * of the GPON Gateway.
 */
public class GatewayStatus {

    private final String modelName;
    private final String hardwareVersion;
    private final String softwareVersion;
    private final String bootVersion;
    private final long uptimeSeconds;
    private final String uptimeFormatted;
    private final Double cpuTemperature;
    private final String wanIp;
    private final String wanStatus;

    public GatewayStatus(
        String modelName,
        String hardwareVersion,
        String softwareVersion,
        String bootVersion,
        long uptimeSeconds,
        String uptimeFormatted,
        Double cpuTemperature,
        String wanIp,
        String wanStatus
    ) {
        this.modelName = modelName != null ? modelName : "";
        this.hardwareVersion = hardwareVersion != null ? hardwareVersion : "";
        this.softwareVersion = softwareVersion != null ? softwareVersion : "";
        this.bootVersion = bootVersion != null ? bootVersion : "";
        this.uptimeSeconds = uptimeSeconds;
        this.uptimeFormatted = uptimeFormatted != null ? uptimeFormatted : "";
        this.cpuTemperature = cpuTemperature;
        this.wanIp = wanIp != null ? wanIp : "";
        this.wanStatus = wanStatus != null ? wanStatus : "";
    }

    public static GatewayStatus fromJson(JsonObject json) {
        if (json == null) return null;
        if (json.containsKey("data") && json.getObject("data") != null) {
            json = json.getObject("data");
        }

        String model = json.getString("model_name", "modelName", "model");
        String hw = json.getString("hardware_version", "hardwareVersion", "hardware");
        String sw = json.getString("software_version", "softwareVersion", "software");
        String boot = json.getString("boot_version", "bootVersion", "bootloader");
        long uptime = json.getLong(0, "uptime_seconds", "uptimeSeconds", "uptime");
        String uptimeFmt = json.getString("uptime_formatted", "uptimeFormatted");
        Double cpuTemp = json.getDoubleVal("cpu_temperature", "cpuTemperature", "cpuTemp");
        String wanIp = json.getString("wan_ip", "wanIp", "ip");
        String wanStat = json.getString("wan_status", "wanStatus", "status");

        return new GatewayStatus(
            model,
            hw,
            sw,
            boot,
            uptime,
            uptimeFmt,
            cpuTemp,
            wanIp,
            wanStat
        );
    }

    public String getModelName() {
        return modelName;
    }

    public String getHardwareVersion() {
        return hardwareVersion;
    }

    public String getSoftwareVersion() {
        return softwareVersion;
    }

    public String getBootVersion() {
        return bootVersion;
    }

    public long getUptimeSeconds() {
        return uptimeSeconds;
    }

    public String getUptimeFormatted() {
        return uptimeFormatted;
    }

    public Double getCpuTemperature() {
        return cpuTemperature;
    }

    public String getWanIp() {
        return wanIp;
    }

    public String getWanStatus() {
        return wanStatus;
    }

    public boolean isWanConnected() {
        return "Connected".equalsIgnoreCase(wanStatus) || (!wanIp.isEmpty() && !"0.0.0.0".equals(wanIp));
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof GatewayStatus)) return false;
        GatewayStatus that = (GatewayStatus) o;
        return uptimeSeconds == that.uptimeSeconds &&
                Objects.equals(modelName, that.modelName) &&
                Objects.equals(hardwareVersion, that.hardwareVersion) &&
                Objects.equals(softwareVersion, that.softwareVersion) &&
                Objects.equals(wanIp, that.wanIp);
    }

    @Override
    public int hashCode() {
        return Objects.hash(modelName, hardwareVersion, softwareVersion, uptimeSeconds, wanIp);
    }

    @Override
    public String toString() {
        return "GatewayStatus{" +
                "model='" + modelName + '\'' +
                ", sw='" + softwareVersion + '\'' +
                ", uptime='" + uptimeFormatted + '\'' +
                ", wanIp='" + wanIp + '\'' +
                ", wanStatus='" + wanStatus + '\'' +
                (cpuTemperature != null ? ", cpuTemp=" + cpuTemperature + "°C" : "") +
                '}';
    }
}
