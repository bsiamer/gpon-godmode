package com.gpon.godmode;

import com.gpon.godmode.json.JsonObject;
import java.util.Objects;

/**
 * GPON fiber optic transceiver signal telemetry.
 * Monitors laser transmit/receive power, module temperature, and signal quality.
 */
public class OpticalStatus {

    private final double txPowerDbm;
    private final double rxPowerDbm;
    private final double transceiverTemperature;
    private final double biasCurrentUa;
    private final String signalQuality;

    public OpticalStatus(
        double txPowerDbm,
        double rxPowerDbm,
        double transceiverTemperature,
        double biasCurrentUa,
        String signalQuality
    ) {
        this.txPowerDbm = txPowerDbm;
        this.rxPowerDbm = rxPowerDbm;
        this.transceiverTemperature = transceiverTemperature;
        this.biasCurrentUa = biasCurrentUa;
        this.signalQuality = signalQuality != null ? signalQuality : "Good";
    }

    public static OpticalStatus fromJson(JsonObject json) {
        if (json == null) return null;
        if (json.containsKey("data") && json.getObject("data") != null) {
            json = json.getObject("data");
        }

        double tx = json.getDouble(0.0, "tx_power_dbm", "txPowerDbm", "tx_power", "tx");
        double rx = json.getDouble(0.0, "rx_power_dbm", "rxPowerDbm", "rx_power", "rx");
        double temp = json.getDouble(0.0, "transceiver_temperature", "transceiverTemperature", "temperature", "temp");
        double bias = json.getDouble(0.0, "bias_current_ua", "biasCurrentUa", "bias_current", "bias");
        String qual = json.getString("Good", "signal_quality", "signalQuality", "quality");

        return new OpticalStatus(tx, rx, temp, bias, qual);
    }

    /**
     * Transmit optical power in dBm.
     */
    public double getTxPowerDbm() {
        return txPowerDbm;
    }

    /**
     * Receive optical power in dBm. Normal operating target is between -8.0 dBm and -25.0 dBm.
     */
    public double getRxPowerDbm() {
        return rxPowerDbm;
    }

    /**
     * Optical transceiver module temperature in Celsius.
     */
    public double getTransceiverTemperature() {
        return transceiverTemperature;
    }

    /**
     * Laser bias current in microamperes (uA).
     */
    public double getBiasCurrentUa() {
        return biasCurrentUa;
    }

    /**
     * Overall signal quality assessment ("Good", "Warning", "Critical").
     */
    public String getSignalQuality() {
        return signalQuality;
    }

    /**
     * Checks if the optical receive power is within the healthy operating window (-8 to -25 dBm).
     */
    public boolean isSignalOptimal() {
        return rxPowerDbm >= -25.0 && rxPowerDbm <= -8.0;
    }

    /**
     * Checks if the optical receive signal is degraded (attenuation, dirty connector, or bend in fiber).
     */
    public boolean isSignalDegraded() {
        return rxPowerDbm < -25.0 || rxPowerDbm > -8.0;
    }

    /**
     * Generates a concise diagnostic summary string.
     */
    public String formatSummary() {
        return String.format(
            "RX: %.2f dBm, TX: %.2f dBm, Temp: %.1f °C, Laser: %.1f µA (Status: %s)",
            rxPowerDbm, txPowerDbm, transceiverTemperature, biasCurrentUa, signalQuality
        );
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof OpticalStatus)) return false;
        OpticalStatus that = (OpticalStatus) o;
        return Double.compare(that.txPowerDbm, txPowerDbm) == 0 &&
                Double.compare(that.rxPowerDbm, rxPowerDbm) == 0 &&
                Double.compare(that.transceiverTemperature, transceiverTemperature) == 0 &&
                Objects.equals(signalQuality, that.signalQuality);
    }

    @Override
    public int hashCode() {
        return Objects.hash(txPowerDbm, rxPowerDbm, transceiverTemperature, signalQuality);
    }

    @Override
    public String toString() {
        return "OpticalStatus{" + formatSummary() + "}";
    }
}
