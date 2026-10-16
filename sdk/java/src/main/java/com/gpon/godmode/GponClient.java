package com.gpon.godmode;

import com.gpon.godmode.json.JsonArray;
import com.gpon.godmode.json.JsonObject;
import com.gpon.godmode.json.SimpleJson;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpConnectTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Idiomatic, zero-external-dependency Java Client for GPON God-Mode.
 * <p>
 * Connects by default to the local REST API daemon at {@code http://127.0.0.1:8254}.
 * If the REST daemon is unreachable, it automatically provides seamless CLI fallback
 * to {@code gpon <command> --json} via {@link ProcessBuilder}.
 */
public class GponClient {

    private static final Logger LOGGER = Logger.getLogger(GponClient.class.getName());

    public static final String DEFAULT_HOST = "127.0.0.1";
    public static final int DEFAULT_PORT = 8254;

    private final String baseUrl;
    private final String host;
    private final int port;
    private final Duration timeout;
    private final boolean fallbackToCli;
    private final String cliExecutable;
    private final HttpClient httpClient;

    /**
     * Creates a GponClient using default configurations, checking System properties
     * ({@code gpon.api.host}, {@code gpon.api.port}, {@code gpon.api.url}) and environment variables
     * ({@code GPON_API_HOST}, {@code GPON_API_PORT}, {@code GPON_API_URL}).
     */
    public GponClient() {
        this(resolveConfig());
    }

    /**
     * Creates a GponClient pointing to the specified base URL (e.g. {@code http://127.0.0.1:8254}).
     *
     * @param baseUrl the root URL of the GPON REST API daemon
     */
    public GponClient(String baseUrl) {
        this(builder().baseUrl(baseUrl));
    }

    /**
     * Creates a GponClient pointing to the specified host and port.
     *
     * @param host hostname or IP of the REST daemon
     * @param port TCP port of the REST daemon (default: 8254)
     */
    public GponClient(String host, int port) {
        this(builder().host(host).port(port));
    }

    /**
     * Creates a GponClient with configurable CLI fallback.
     *
     * @param host          hostname or IP
     * @param port          TCP port
     * @param fallbackToCli whether to fallback to 'gpon --json' if HTTP fails
     */
    public GponClient(String host, int port, boolean fallbackToCli) {
        this(builder().host(host).port(port).fallbackToCli(fallbackToCli));
    }

    private GponClient(Builder builder) {
        this.host = builder.host;
        this.port = builder.port;
        this.baseUrl = builder.baseUrl != null
                ? builder.baseUrl.replaceAll("/+$", "")
                : String.format("http://%s:%d", this.host, this.port);
        this.timeout = builder.timeout != null ? builder.timeout : Duration.ofSeconds(5);
        this.fallbackToCli = builder.fallbackToCli;
        this.cliExecutable = builder.cliExecutable != null ? builder.cliExecutable : resolveCliPath();

        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(this.timeout)
                .build();
    }

    public static Builder builder() {
        return new Builder();
    }

    private static Builder resolveConfig() {
        Builder b = new Builder();

        // 1. URL overrides
        String urlProp = System.getProperty("gpon.api.url");
        String urlEnv = System.getenv("GPON_API_URL");
        if (urlProp != null && !urlProp.trim().isEmpty()) {
            b.baseUrl(urlProp.trim());
            return b;
        }
        if (urlEnv != null && !urlEnv.trim().isEmpty()) {
            b.baseUrl(urlEnv.trim());
            return b;
        }

        // 2. Host overrides
        String hostProp = System.getProperty("gpon.api.host");
        String hostEnv = System.getenv("GPON_API_HOST");
        if (hostProp != null && !hostProp.trim().isEmpty()) {
            b.host(hostProp.trim());
        } else if (hostEnv != null && !hostEnv.trim().isEmpty()) {
            b.host(hostEnv.trim());
        } else {
            b.host(DEFAULT_HOST);
        }

        // 3. Port overrides
        String portProp = System.getProperty("gpon.api.port");
        String portEnv = System.getenv("GPON_API_PORT");
        int resolvedPort = DEFAULT_PORT;
        if (portProp != null && !portProp.trim().isEmpty()) {
            try {
                resolvedPort = Integer.parseInt(portProp.trim());
            } catch (NumberFormatException ignored) {}
        } else if (portEnv != null && !portEnv.trim().isEmpty()) {
            try {
                resolvedPort = Integer.parseInt(portEnv.trim());
            } catch (NumberFormatException ignored) {}
        }
        b.port(resolvedPort);

        return b;
    }

    private static String resolveCliPath() {
        String prop = System.getProperty("gpon.cli.path");
        if (prop != null && !prop.trim().isEmpty()) return prop.trim();

        String env = System.getenv("GPON_CLI_PATH");
        if (env != null && !env.trim().isEmpty()) return env.trim();

        // Check common locations
        String[] probe = new String[]{
            "gpon",
            "./gpon.sh",
            "../gpon.sh",
            "../../gpon.sh",
            "/home/noe/Projects/gpon-godmode/gpon.sh"
        };
        for (String p : probe) {
            if ("gpon".equals(p)) continue;
            File f = new File(p);
            if (f.exists() && f.canExecute()) {
                return f.getAbsolutePath();
            }
        }
        return "gpon";
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public String getHost() {
        return host;
    }

    public int getPort() {
        return port;
    }

    public boolean isFallbackToCliEnabled() {
        return fallbackToCli;
    }

    // =========================================================================
    // Core API Operations
    // =========================================================================

    /**
     * Retrieves hardware specs, firmware revision, uptime, and WAN IP from the gateway.
     *
     * @return {@link GatewayStatus}
     * @throws GponException on communication or parse error
     */
    public GatewayStatus getStatus() throws GponException {
        try {
            String body = httpGet("/api/status");
            return GatewayStatus.fromJson(SimpleJson.parseObject(body));
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP /api/status failed, attempting CLI fallback...", e);
                JsonObject json = executeCliJson("status");
                return GatewayStatus.fromJson(json);
            }
            throw wrapException("Failed to fetch gateway status", e);
        }
    }

    /**
     * Lists all active and registered LAN and Wi-Fi client devices.
     *
     * @return List of {@link Device}
     * @throws GponException on communication or parse error
     */
    public List<Device> getDevices() throws GponException {
        try {
            String body = httpGet("/api/devices");
            Object parsed = SimpleJson.parse(body);
            return parseDeviceList(parsed);
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP /api/devices failed, attempting CLI fallback...", e);
                Object parsed = executeCliParsed("devices");
                return parseDeviceList(parsed);
            }
            throw wrapException("Failed to fetch devices", e);
        }
    }

    /**
     * Retrieves GPON optical laser telemetry (TX/RX power in dBm, temperature, laser bias).
     *
     * @return {@link OpticalStatus}
     * @throws GponException on communication or parse error
     */
    public OpticalStatus getOpticalStatus() throws GponException {
        try {
            String body = httpGet("/api/optical");
            return OpticalStatus.fromJson(SimpleJson.parseObject(body));
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP /api/optical failed, attempting CLI fallback...", e);
                JsonObject json = executeCliJson("optical");
                return OpticalStatus.fromJson(json);
            }
            throw wrapException("Failed to fetch optical status", e);
        }
    }

    /**
     * Lists active NAT port forwarding rules configured on the GPON Gateway.
     *
     * @return List of {@link PortForwardRule}
     * @throws GponException on communication or parse error
     */
    public List<PortForwardRule> listPortForwards() throws GponException {
        try {
            String body = httpGet("/api/port-forwards");
            Object parsed = SimpleJson.parse(body);
            return parsePortForwardList(parsed);
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP /api/port-forwards failed, attempting CLI fallback...", e);
                Object parsed = executeCliParsed("ports", "list");
                return parsePortForwardList(parsed);
            }
            throw wrapException("Failed to list port forwards", e);
        }
    }

    /**
     * Adds a new NAT port forwarding rule.
     *
     * @param name         Identifier or label for this rule (e.g. "Minecraft-Auto")
     * @param externalPort WAN port (1-65535)
     * @param internalPort LAN port (1-65535)
     * @param ip           Target internal IP address (e.g. "192.168.1.100")
     * @param protocol     Protocol: "TCP", "UDP", or "TCP/UDP"
     * @return {@code true} if successfully applied
     * @throws GponException on communication or validation error
     */
    public boolean addPortForward(String name, int externalPort, int internalPort, String ip, String protocol) throws GponException {
        JsonObject req = new JsonObject();
        req.put("external_port", externalPort);
        req.put("internal_port", internalPort);
        req.put("server_ip", ip);
        req.put("protocol", protocol != null ? protocol.toUpperCase() : "TCP");
        if (name != null && !name.isEmpty()) {
            req.put("name", name);
        }

        try {
            String resp = httpPost("/api/port-forwards", req.toJson());
            JsonObject json = SimpleJson.parseObject(resp);
            return json.getBoolean(true, "success");
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP addPortForward failed, attempting CLI fallback...", e);
                JsonObject cliRes = executeCliJson(
                    "ports", "add",
                    String.valueOf(externalPort),
                    String.valueOf(internalPort),
                    ip,
                    "--proto",
                    protocol != null ? protocol.toUpperCase() : "TCP"
                );
                return cliRes.getBoolean(true, "success");
            }
            throw wrapException("Failed to add port forward", e);
        }
    }

    /**
     * Overload for {@link #addPortForward(String, int, int, String, String)} without explicit rule name.
     */
    public boolean addPortForward(int externalPort, int internalPort, String ip, String protocol) throws GponException {
        return addPortForward("", externalPort, internalPort, ip, protocol);
    }

    /**
     * Deletes a port forwarding rule by name or external port.
     * If {@code name} matches a rule name or represents an integer port, it will be removed.
     *
     * @param name rule name (e.g. "Minecraft-Auto") or external port as string
     * @return {@code true} if deleted successfully
     * @throws GponException on failure
     */
    public boolean deletePortForward(String name) throws GponException {
        if (name == null || name.trim().isEmpty()) {
            throw new IllegalArgumentException("Rule name or port must not be empty");
        }

        // Try parsing directly as an integer port
        try {
            int port = Integer.parseInt(name.trim());
            return deletePortForward(port);
        } catch (NumberFormatException ignored) {}

        // Otherwise look up existing rules to find the port matching rule name
        List<PortForwardRule> rules = listPortForwards();
        for (PortForwardRule r : rules) {
            if (name.equalsIgnoreCase(r.getName())) {
                return deletePortForward(r.getExternalPort());
            }
        }

        // Fallback: if not found by name, try CLI directly if CLI supports name delete
        LOGGER.warning("No rule named '" + name + "' found in active port forward list.");
        return false;
    }

    /**
     * Deletes a port forwarding rule by external port number.
     *
     * @param externalPort WAN port of the rule to delete
     * @return {@code true} if successfully removed
     * @throws GponException on failure
     */
    public boolean deletePortForward(int externalPort) throws GponException {
        try {
            String resp = httpDelete("/api/port-forwards/" + externalPort);
            JsonObject json = SimpleJson.parseObject(resp);
            return json.getBoolean(true, "success");
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP deletePortForward failed, attempting CLI fallback...", e);
                JsonObject cliRes = executeCliJson("ports", "del", String.valueOf(externalPort));
                return cliRes.getBoolean(true, "success");
            }
            throw wrapException("Failed to delete port forward on port " + externalPort, e);
        }
    }

    /**
     * Enables or disables DMZ host forwarding for a specified LAN IP.
     *
     * @param ip     Target LAN IP address
     * @param enable {@code true} to enable DMZ, {@code false} to disable
     * @return {@code true} if updated successfully
     * @throws GponException on failure
     */
    public boolean setDmz(String ip, boolean enable) throws GponException {
        JsonObject req = new JsonObject();
        req.put("ip_address", ip != null ? ip : "0.0.0.0");
        req.put("enabled", enable);

        try {
            String resp = httpPost("/api/dmz", req.toJson());
            JsonObject json = SimpleJson.parseObject(resp);
            return json.getBoolean(true, "success");
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP setDmz failed, attempting CLI fallback...", e);
                JsonObject cliRes;
                if (enable) {
                    cliRes = executeCliJson("dmz", "set", ip);
                } else {
                    cliRes = executeCliJson("dmz", "disable");
                }
                return cliRes.getBoolean(true, "success");
            }
            throw wrapException("Failed to configure DMZ", e);
        }
    }

    /**
     * Applies full low-latency gaming optimization macro:
     * enables DMZ for IP, enables UPnP, and disables DoS filtering and SIP ALG.
     *
     * @param ip Target console/server LAN IP
     * @return {@link GamingOptimizationResult}
     * @throws GponException on failure
     */
    public GamingOptimizationResult optimizeGaming(String ip) throws GponException {
        JsonObject req = new JsonObject();
        req.put("target_ip", ip);
        req.put("enable_dmz", true);

        try {
            String resp = httpPost("/api/optimize-gaming", req.toJson());
            return GamingOptimizationResult.fromJson(SimpleJson.parseObject(resp));
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP optimizeGaming failed, attempting CLI fallback...", e);
                JsonObject cliRes = executeCliJson("gaming", ip);
                return GamingOptimizationResult.fromJson(cliRes);
            }
            throw wrapException("Failed to apply gaming optimization", e);
        }
    }

    /**
     * Reboots the GPON Gateway.
     *
     * @return {@code true} if reboot command was accepted
     * @throws GponException on failure
     */
    public boolean reboot() throws GponException {
        JsonObject req = new JsonObject();
        req.put("confirm", true);

        try {
            String resp = httpPost("/api/reboot", req.toJson());
            JsonObject json = SimpleJson.parseObject(resp);
            return json.getBoolean(true, "success");
        } catch (Exception e) {
            if (fallbackToCli) {
                LOGGER.log(Level.FINE, "HTTP reboot failed, attempting CLI fallback...", e);
                JsonObject cliRes = executeCliJson("reboot");
                return cliRes.getBoolean(true, "success");
            }
            throw wrapException("Failed to reboot gateway", e);
        }
    }

    /**
     * Performs a lightweight health/liveness probe against the REST daemon.
     *
     * @return {@code true} if daemon is reachable and healthy
     */
    public boolean isHealthy() {
        try {
            String resp = httpGet("/health");
            JsonObject json = SimpleJson.parseObject(resp);
            return "healthy".equalsIgnoreCase(json.getString("status"));
        } catch (Exception e) {
            return false;
        }
    }

    // =========================================================================
    // HTTP Helpers
    // =========================================================================

    private String httpGet(String path) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(timeout)
                .header("Accept", "application/json")
                .GET()
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        checkStatusCode(response);
        return response.body();
    }

    private String httpPost(String path, String jsonBody) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(timeout)
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        checkStatusCode(response);
        return response.body();
    }

    private String httpDelete(String path) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(timeout)
                .header("Accept", "application/json")
                .DELETE()
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        checkStatusCode(response);
        return response.body();
    }

    private void checkStatusCode(HttpResponse<String> response) {
        int code = response.statusCode();
        if (code < 200 || code >= 300) {
            throw new GponException("Gateway daemon returned HTTP " + code + ": " + response.body(), code);
        }
    }

    // =========================================================================
    // CLI Fallback Helpers
    // =========================================================================

    private JsonObject executeCliJson(String... args) {
        Object parsed = executeCliParsed(args);
        if (parsed instanceof JsonObject) {
            return (JsonObject) parsed;
        }
        if (parsed instanceof JsonArray) {
            JsonObject wrapper = new JsonObject();
            wrapper.put("data", parsed);
            return wrapper;
        }
        throw new GponException("Expected JSON object from CLI but got: " + parsed);
    }

    private Object executeCliParsed(String... args) {
        List<String> command = new ArrayList<>();
        if (cliExecutable.endsWith(".sh")) {
            command.add("bash");
            command.add(cliExecutable);
        } else {
            command.add(cliExecutable);
        }

        for (String a : args) {
            command.add(a);
        }
        command.add("--json");

        try {
            ProcessBuilder pb = new ProcessBuilder(command);
            pb.redirectErrorStream(false);
            Process process = pb.start();

            StringBuilder stdout = new StringBuilder();
            StringBuilder stderr = new StringBuilder();

            try (BufferedReader r = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) {
                    stdout.append(line).append('\n');
                }
            }

            try (BufferedReader r = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) {
                    stderr.append(line).append('\n');
                }
            }

            boolean finished = process.waitFor(15, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                throw new GponException("CLI command timed out after 15 seconds: " + String.join(" ", command));
            }

            int exitCode = process.exitValue();
            String output = stdout.toString().trim();

            if (exitCode != 0) {
                String err = stderr.toString().trim();
                throw new GponException("CLI execution failed (exit code " + exitCode + "): " + (err.isEmpty() ? output : err));
            }

            if (output.isEmpty()) {
                throw new GponException("CLI produced empty output for command: " + String.join(" ", command));
            }

            return SimpleJson.parse(output);
        } catch (IOException | InterruptedException e) {
            throw new GponException("Failed to execute fallback CLI: " + String.join(" ", command), e);
        }
    }

    // =========================================================================
    // List Parsers
    // =========================================================================

    private List<Device> parseDeviceList(Object parsed) {
        List<Device> list = new ArrayList<>();
        JsonArray array = null;

        if (parsed instanceof JsonArray) {
            array = (JsonArray) parsed;
        } else if (parsed instanceof JsonObject) {
            JsonObject obj = (JsonObject) parsed;
            if (obj.containsKey("data")) {
                array = obj.getArray("data");
            }
        }

        if (array != null) {
            for (Object item : array) {
                if (item instanceof JsonObject) {
                    list.add(Device.fromJson((JsonObject) item));
                }
            }
        }
        return list;
    }

    private List<PortForwardRule> parsePortForwardList(Object parsed) {
        List<PortForwardRule> list = new ArrayList<>();
        JsonArray array = null;

        if (parsed instanceof JsonArray) {
            array = (JsonArray) parsed;
        } else if (parsed instanceof JsonObject) {
            JsonObject obj = (JsonObject) parsed;
            if (obj.containsKey("data")) {
                array = obj.getArray("data");
            }
        }

        if (array != null) {
            for (Object item : array) {
                if (item instanceof JsonObject) {
                    list.add(PortForwardRule.fromJson((JsonObject) item));
                }
            }
        }
        return list;
    }

    private GponException wrapException(String message, Exception e) {
        if (e instanceof GponException) {
            return (GponException) e;
        }
        return new GponException(message + ": " + e.getMessage(), e);
    }

    // =========================================================================
    // Builder
    // =========================================================================

    public static class Builder {
        private String baseUrl;
        private String host = DEFAULT_HOST;
        private int port = DEFAULT_PORT;
        private Duration timeout = Duration.ofSeconds(5);
        private boolean fallbackToCli = true;
        private String cliExecutable;

        public Builder baseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
            return this;
        }

        public Builder host(String host) {
            this.host = host;
            return this;
        }

        public Builder port(int port) {
            this.port = port;
            return this;
        }

        public Builder timeout(Duration timeout) {
            this.timeout = timeout;
            return this;
        }

        public Builder fallbackToCli(boolean fallbackToCli) {
            this.fallbackToCli = fallbackToCli;
            return this;
        }

        public Builder cliExecutable(String cliExecutable) {
            this.cliExecutable = cliExecutable;
            return this;
        }

        public GponClient build() {
            return new GponClient(this);
        }
    }
}
