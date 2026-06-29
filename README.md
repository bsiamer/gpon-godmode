# GPON God-Mode API 🚀

A full headless automation wrapper for Nokia/Alcatel GPON Home Gateways. This tool bypasses ISP-imposed UI restrictions (like hidden Bridge Modes, locked DNS settings, etc.) by directly injecting JavaScript DOM exploits via Playwright, and exposes the entire router configuration as a clean REST API.

## Features
- **God-Mode `forceset`**: Bypass `disabled`, `readonly`, and `hidden` HTML tags to force the router's backend to accept advanced configurations.
- **Automated Port Forwarding**: Open ports programmatically.
- **Automated Reboot**: Soft-reboot your gateway from a script.
- **Headless & Asynchronous**: Built entirely on FastAPI and Playwright.

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/gpon-godmode.git
cd gpon-godmode

# 2. Run the setup script
chmod +x setup.sh
./setup.sh
```

## Usage

Start the API server in the background:
```bash
./gpon.sh start
```

### Examples

**Force changing the IPv4 DNS servers (bypass ISP locks):**
```bash
./gpon.sh dns 1.1.1.1 8.8.8.8
```

**Force changing the IPv6 DNS servers:**
```bash
./gpon.sh ipv6-dns 2606:4700:4700::1111 2606:4700:4700::1001
```

**Bypass port-forwarding restrictions:**
```bash
./gpon.sh port 80 80 192.168.1.154
```

**Soft-reboot the gateway:**
```bash
./gpon.sh reboot
```

See `router_settings.md` for a full dictionary of every single internal variable if you want to write custom JSON payloads to hit the `http://127.0.0.1:5000/forceset` endpoint manually.

---
*Note: This tool uses Headless Chromium and supports dynamic IP configurations. If your router is not on `192.168.1.254` or uses a different password, set the `ROUTER_IP`, `ROUTER_USER`, and `ROUTER_PASS` environment variables.*
