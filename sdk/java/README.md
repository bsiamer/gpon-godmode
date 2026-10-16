# GPON God-Mode: Java SDK & Minecraft Paper/Spigot Plugin

A complete, idiomatic, **zero-external-dependency** Java SDK and automated Minecraft Paper/Spigot plugin for Nokia/Alcatel-Lucent GPON Gateways.

---

## ⚡ Highlights

* **Zero External Dependencies**: Built entirely on Java 11+ standard library (`java.net.http.HttpClient`, `java.time`, and built-in RFC 8259 JSON engine). No Jackson or Gson shading conflicts.
* **Default REST Daemon Target**: Connects to the local GPON God-Mode REST API on **port `8254`** (`http://127.0.0.1:8254`).
* **Resilient Dual-Mode Operation**: If the background daemon is not running, the SDK automatically executes local `gpon <command> --json` commands via `ProcessBuilder` and parses stdout seamlessly.
* **Paper/Spigot 1.20+ Plugin**: Drops directly into any Minecraft server to auto-forward port `25565`, monitor optical fiber power (RX/TX dBm), and diagnose network health in real-time.

---

## 📦 Project Structure

```text
sdk/java/
├── pom.xml                                      # Core Java SDK Maven POM (Java 11+)
├── src/main/java/com/gpon/godmode/
│   ├── GponClient.java                          # Core high-level client
│   ├── GponException.java                       # Standard runtime exception
│   ├── GatewayStatus.java                       # Router model, uptime & WAN telemetry
│   ├── Device.java                              # Connected LAN & Wi-Fi device model
│   ├── OpticalStatus.java                       # Fiber transceiver telemetry (RX/TX dBm)
│   ├── PortForwardRule.java                     # NAT virtual server forwarding rule model
│   ├── GamingOptimizationResult.java            # Low-latency gaming macro result model
│   ├── StandaloneExample.java                   # Runnable CLI demo application
│   └── json/
│       ├── SimpleJson.java                      # Pure standard library JSON parser/serializer
│       ├── JsonObject.java                      # Typed JSON object wrapper with snake_case support
│       └── JsonArray.java                       # Typed JSON array wrapper
├── minecraft-plugin/
│   ├── pom.xml                                  # Paper/Spigot plugin POM (Java 17+, shaded jar)
│   └── src/main/
│       ├── java/com/gpon/godmode/plugin/
│       │   ├── GponPortForwardPlugin.java       # Plugin lifecycle (auto-forward on start/stop)
│       │   └── GponCommand.java                 # In-game /gpon commands & tab completer
│       └── resources/
│           ├── plugin.yml                       # Bukkit plugin manifest
│           └── config.yml                       # Configurable host, port, thresholds
└── README.md
```

---

## 🚀 Java Client Usage

### 1. Initializing the Client

The client connects to `http://127.0.0.1:8254` by default. You can configure host and port via constructor, builder, system properties, or environment variables.

```java
import com.gpon.godmode.GponClient;

// Default client (127.0.0.1:8254 with CLI fallback enabled)
GponClient client = new GponClient();

// Or customized with Fluent Builder
GponClient customClient = GponClient.builder()
        .host("127.0.0.1")
        .port(8254)
        .timeout(Duration.ofSeconds(5))
        .fallbackToCli(true) // execute 'gpon <command> --json' if daemon unreachable
        .build();
```

#### Configuration Precedence:
1. Explicit constructor/builder values
2. System properties: `-Dgpon.api.url`, `-Dgpon.api.host`, `-Dgpon.api.port`
3. Environment variables: `GPON_API_URL`, `GPON_API_HOST`, `GPON_API_PORT`
4. Built-in defaults: `http://127.0.0.1:8254`

---

### 2. Querying Gateway Status

```java
GatewayStatus status = client.getStatus();
System.out.println("Model:       " + status.getModelName());
System.out.println("Firmware:    " + status.getSoftwareVersion());
System.out.println("Uptime:      " + status.getUptimeFormatted());
System.out.println("Public IP:   " + status.getWanIp());
System.out.println("WAN Status:  " + status.getWanStatus());
```

---

### 3. Monitoring Fiber Optical Signal

Monitors optical laser transmit/receive power, transceiver module temperature, and laser bias current.

```java
OpticalStatus optical = client.getOpticalStatus();
System.out.printf("RX Power: %.2f dBm%n", optical.getRxPowerDbm());
System.out.printf("TX Power: %.2f dBm%n", optical.getTxPowerDbm());
System.out.printf("Laser Temperature: %.1f °C%n", optical.getTransceiverTemperature());

if (optical.isSignalDegraded()) {
    System.err.println("WARNING: Fiber signal degraded (below -25 dBm)! Check physical patch cable.");
} else {
    System.out.println("Fiber signal is within optimal range (-8 to -25 dBm).");
}
```

---

### 4. Managing NAT Port Forwarding Rules

```java
// List active rules
List<PortForwardRule> rules = client.listPortForwards();
for (PortForwardRule rule : rules) {
    System.out.println("Active: " + rule);
}

// Add a port forward (e.g., Minecraft server)
boolean ok = client.addPortForward("Minecraft-Server", 25565, 25565, "192.168.1.150", "TCP/UDP");

// Delete port forward by name or port number
client.deletePortForward("Minecraft-Server");
// or
client.deletePortForward(25565);
```

---

### 5. Low-Latency Gaming Macro

Applies one-shot optimizations: sets DMZ for the target IP, disables router DoS packet flood filtering, disables SIP ALG, and enables UPnP.

```java
GamingOptimizationResult result = client.optimizeGaming("192.168.1.150");
System.out.println("Gaming Macro Applied: " + result.getMessage());
```

---

### 6. Running the Standalone Demo

Compile and run the built-in demo directly:

```bash
cd sdk/java
# Compile using javac:
javac -d target/classes $(find src/main/java -name "*.java")

# Run demo:
java -cp target/classes com.gpon.godmode.StandaloneExample
```

Or using Maven:
```bash
mvn compile exec:java -Dexec.mainClass="com.gpon.godmode.StandaloneExample"
```

---

## 🎮 Minecraft Paper/Spigot Plugin

`GponPortForwardPlugin` is a drop-in Spigot/Paper 1.20+ plugin designed for server administrators hosting Minecraft servers behind GPON fiber connections.

### Features
1. **Automated Port Forwarding**: On server startup (`onEnable`), detects the server's local LAN IP and automatically forwards WAN port `25565` to the server machine via GPON Gateway.
2. **Clean Shutdown**: On server shutdown (`onDisable`), cleanly removes the NAT rule to keep router forwarding tables tidy.
3. **Fiber Health Telemetry**: Automatically checks RX/TX optical signal power on startup. Warns in server console if the fiber line has degraded attenuation (e.g. sharp bend in yellow fiber patch cable or dirty SC/APC connector).
4. **Asynchronous Execution**: All gateway communication occurs asynchronously off the main thread; your server tick rate (20 TPS) will never hitch or stall.

### In-Game Commands (`/gpon`)

| Command | Permission | Description |
| :--- | :--- | :--- |
| `/gpon status` | `gpon.admin` | Displays gateway model, uptime, firmware, and WAN IP |
| `/gpon optical` | `gpon.admin` | Displays optical RX/TX dBm, laser temperature, and fiber health |
| `/gpon ping` | `gpon.admin` | Measures round-trip latency to the GPON REST daemon |
| `/gpon forward` | `gpon.admin` | Manually triggers/verifies server NAT port forward |
| `/gpon unforward` | `gpon.admin` | Manually deletes the server NAT port forward |
| `/gpon devices` | `gpon.admin` | Lists connected LAN and Wi-Fi clients |
| `/gpon gaming [ip]` | `gpon.admin` | Applies low-latency DMZ/UPnP optimization macro |
| `/gpon reboot confirm` | `gpon.admin` | Reboots the fiber gateway remotely |

### Configuration (`config.yml`)

```yaml
gpon:
  host: "127.0.0.1"
  port: 8254
  fallback-to-cli: true

port-forward:
  enabled: true
  rule-name: "Minecraft-Auto"
  protocol: "TCP/UDP"
  server-ip: "auto"        # Auto-detects local LAN IPv4 (e.g. 192.168.1.150)
  external-port: 0         # 0 = Automatically mirrors server-port from server.properties
  internal-port: 0

optical:
  check-on-startup: true
  alert-threshold-rx-dbm: -25.0
```

### Compiling the Plugin

```bash
cd sdk/java/minecraft-plugin
mvn clean package
```
The output file `target/gpon-minecraft-plugin-2.0.0.jar` contains the shaded SDK classes and is ready to copy directly into your Paper/Spigot server's `plugins/` directory:

```bash
cp target/gpon-minecraft-plugin-2.0.0.jar /path/to/minecraft/plugins/
```

---

## 🛠️ Testing the REST Daemon

Start the Python REST daemon on port `8254`:

```bash
# In project root:
export GPON_API_PORT=8254
./gpon.sh --help

# Launch daemon:
python3 -m gpon_godmode.api --port 8254
```
Access the interactive OpenAPI Swagger docs at `http://127.0.0.1:8254/docs`.
