package com.gpon.godmode;

import com.gpon.godmode.json.JsonObject;
import java.util.Objects;

/**
 * Result of the low-latency gaming optimization macro on the GPON Gateway.
 */
public class GamingOptimizationResult {

    private final String targetIp;
    private final boolean dmzConfigured;
    private final boolean dosProtectionDisabled;
    private final boolean sipAlgDisabled;
    private final boolean upnpEnabled;
    private final String message;

    public GamingOptimizationResult(
        String targetIp,
        boolean dmzConfigured,
        boolean dosProtectionDisabled,
        boolean sipAlgDisabled,
        boolean upnpEnabled,
        String message
    ) {
        this.targetIp = targetIp != null ? targetIp : "";
        this.dmzConfigured = dmzConfigured;
        this.dosProtectionDisabled = dosProtectionDisabled;
        this.sipAlgDisabled = sipAlgDisabled;
        this.upnpEnabled = upnpEnabled;
        this.message = message != null ? message : "";
    }

    public static GamingOptimizationResult fromJson(JsonObject json) {
        if (json == null) return null;
        if (json.containsKey("data") && json.getObject("data") != null) {
            json = json.getObject("data");
        }

        String ip = json.getString("", "target_ip", "targetIp", "ip");
        boolean dmz = json.getBoolean(false, "dmz_configured", "dmzConfigured", "dmz");
        boolean dos = json.getBoolean(false, "dos_protection_disabled", "dosProtectionDisabled", "dos_disabled");
        boolean sip = json.getBoolean(false, "sip_alg_disabled", "sipAlgDisabled", "sip_disabled");
        boolean upnp = json.getBoolean(false, "upnp_enabled", "upnpEnabled", "upnp");
        String msg = json.getString("Gaming optimizations applied successfully.", "message", "msg", "result");

        return new GamingOptimizationResult(ip, dmz, dos, sip, upnp, msg);
    }

    public String getTargetIp() {
        return targetIp;
    }

    public boolean isDmzConfigured() {
        return dmzConfigured;
    }

    public boolean isDosProtectionDisabled() {
        return dosProtectionDisabled;
    }

    public boolean isSipAlgDisabled() {
        return sipAlgDisabled;
    }

    public boolean isUpnpEnabled() {
        return upnpEnabled;
    }

    public String getMessage() {
        return message;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof GamingOptimizationResult)) return false;
        GamingOptimizationResult that = (GamingOptimizationResult) o;
        return dmzConfigured == that.dmzConfigured &&
                dosProtectionDisabled == that.dosProtectionDisabled &&
                sipAlgDisabled == that.sipAlgDisabled &&
                upnpEnabled == that.upnpEnabled &&
                Objects.equals(targetIp, that.targetIp);
    }

    @Override
    public int hashCode() {
        return Objects.hash(targetIp, dmzConfigured, dosProtectionDisabled, sipAlgDisabled, upnpEnabled);
    }

    @Override
    public String toString() {
        return "GamingOptimizationResult{" +
                "targetIp='" + targetIp + '\'' +
                ", dmz=" + dmzConfigured +
                ", dosDisabled=" + dosProtectionDisabled +
                ", sipAlgDisabled=" + sipAlgDisabled +
                ", upnp=" + upnpEnabled +
                ", message='" + message + '\'' +
                '}';
    }
}
