"""High-performance, pure HTTP client for Nokia/Alcatel GPON Gateway."""

import math
import os
import re
import time
import threading
import ipaddress
from typing import List, Optional, Dict, Any, Tuple
import httpx
from dotenv import load_dotenv

from .crypto import encrypt_login_payload
from .models import (
    Device,
    PortForwardRule,
    GatewayStatus,
    DMZConfig,
    GamingOptimizationResult,
    OpticalStatus,
    WifiConfig,
    EthernetPortStatus,
)

load_dotenv()


class GPONClient:
    """Thread-safe, browserless HTTP client for Nokia/Alcatel GPON Gateways."""

    _lock = threading.Lock()

    def __init__(
        self,
        ip: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.ip = (ip or os.environ.get("ROUTER_IP", "http://192.168.1.254")).rstrip("/")
        self.user = user or os.environ.get("ROUTER_USER", "userAdmin")
        self.password = password or os.environ.get("ROUTER_PASS", "")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._is_logged_in = False
        self._last_auth_time = 0.0

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                verify=False,
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
        return self._client

    def close(self):
        """Closes the underlying HTTP connection pool."""
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None
            self._is_logged_in = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def login(self, force: bool = False) -> bool:
        """Authenticates with the router using SJCL RSA/AES encryption.
        
        Caches the active session for up to 5 minutes to avoid redundant auth handshakes.
        """
        with self._lock:
            # Session reuse: keep session warm for 300 seconds
            if self._is_logged_in and not force and (time.time() - self._last_auth_time < 300):
                return True

            client = self._get_client()
            r = client.get(self.ip)
            if r.status_code != 200:
                raise ConnectionError(f"Failed to connect to gateway login page: HTTP {r.status_code}")

            html = r.text
            pubkey_match = re.search(
                r"var pubkey = '(-----BEGIN PUBLIC KEY-----\\.*?-----END PUBLIC KEY-----\\)';",
                html,
                re.DOTALL,
            )
            if not pubkey_match:
                pubkey_match = re.search(
                    r"var pubkey = '(-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----.*?)';",
                    html,
                    re.DOTALL,
                )

            if not pubkey_match:
                raise RuntimeError("Could not find RSA public key in login page HTML")

            pubkey_pem = pubkey_match.group(1).replace("\\\n", "\n").replace("\\", "")

            nonce_match = re.search(r'var nonce = "(.*?)";', html)
            if not nonce_match:
                raise RuntimeError("Could not find auth nonce in login page HTML")

            nonce = nonce_match.group(1)
            encrypted_payload = encrypt_login_payload(self.user, self.password, nonce, pubkey_pem)

            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": f"{self.ip}/",
            }

            login_res = client.post(
                f"{self.ip}/login.cgi",
                content=encrypted_payload,
                headers=headers,
                follow_redirects=False,
            )

            # Nokia firmware responds with HTTP 299 upon successful authentication
            if login_res.status_code != 299:
                raise PermissionError(
                    f"Authentication failed: HTTP {login_res.status_code}. Verify ROUTER_USER and ROUTER_PASS."
                )

            self._is_logged_in = True
            self._last_auth_time = time.time()
            return True

    def _extract_csrf(self, html: str) -> str:
        """Extracts CSRF token from page HTML or jQuery ajaxSend script."""
        csrf_match = re.search(r'csrf_token=([a-zA-Z0-9]+)', html)
        if not csrf_match:
            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        if not csrf_match:
            raise ValueError("Could not locate CSRF token on target configuration page")
        return csrf_match.group(1)

    def get_status(self) -> GatewayStatus:
        """Retrieves hardware information, software version, uptime, and WAN link state."""
        self.login()
        client = self._get_client()

        # 1. Device Info
        res_info = client.get(f"{self.ip}/device_status.cgi")
        html_info = res_info.text

        def find_field(key: str) -> str:
            m = re.search(rf'"{key}":"([^"]*)"', html_info)
            return m.group(1) if m else ""

        model = find_field("ModelName") or "Nokia GPON Gateway"
        hw_ver = find_field("HardwareVersion")
        sw_ver = find_field("SoftwareVersion")
        boot_ver = find_field("AdditionalSoftwareVersion")

        uptime_match = re.search(r'"UpTime":(\d+)', html_info) or re.search(r'var uptime = "(\d+)";', html_info)
        uptime_sec = int(uptime_match.group(1)) if uptime_match else 0

        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        mins = (uptime_sec % 3600) // 60
        uptime_fmt = f"{days}d {hours}h {mins}m ({uptime_sec}s)"

        # 2. CPU Temperature
        temp: Optional[float] = None
        temp_match = re.search(r'"CPUTemp":"([0-9.]+)', html_info)
        if temp_match:
            temp = float(temp_match.group(1))

        # 3. WAN IP & Status
        wan_ip: Optional[str] = None
        wan_status: Optional[str] = None
        try:
            res_wan = client.get(f"{self.ip}/show_wan_status.cgi?ipv4")
            ip_m = re.search(r"ExternalIPAddress:'([^']*)'", res_wan.text)
            status_m = re.search(r"ConnectionStatus:'([^']*)'", res_wan.text)
            if ip_m and ip_m.group(1):
                wan_ip = ip_m.group(1)
            if status_m:
                wan_status = status_m.group(1)
        except Exception:
            pass

        return GatewayStatus(
            model_name=model,
            hardware_version=hw_ver,
            software_version=sw_ver,
            boot_version=boot_ver,
            uptime_seconds=uptime_sec,
            uptime_formatted=uptime_fmt,
            cpu_temperature=temp,
            wan_ip=wan_ip,
            wan_status=wan_status,
        )

    def get_devices(self) -> List[Device]:
        """Lists all connected LAN and Wi-Fi clients (active and known)."""
        self.login()
        client = self._get_client()

        res = client.get(f"{self.ip}/macfilter.cgi")
        match = re.search(r"var device_cfg = (\[.*?\]);", res.text, re.DOTALL)
        if not match:
            return []

        devices: List[Device] = []
        entries = re.findall(r"\{([^\}]+)\}", match.group(1))
        for entry in entries:
            oid_m = re.search(r"_oid:(\d+)", entry)
            host_m = re.search(r"HostName:'([^']*)'", entry)
            ip_m = re.search(r"IPAddress:'([^']*)'", entry)
            mac_m = re.search(r"MACAddress:'([^']*)'", entry)
            act_m = re.search(r"Active:(\d+)", entry)
            if_m = re.search(r"InterfaceType:'([^']*)'", entry)

            if ip_m and mac_m:
                devices.append(
                    Device(
                        oid=int(oid_m.group(1)) if oid_m else 0,
                        hostname=host_m.group(1) if host_m else "",
                        ip_address=ip_m.group(1),
                        mac_address=mac_m.group(1),
                        active=bool(int(act_m.group(1))) if act_m else True,
                        interface_type=if_m.group(1) if if_m else "Ethernet",
                    )
                )

        return devices

    def list_port_forwards(self) -> List[PortForwardRule]:
        """Returns all configured port forwarding rules."""
        self.login()
        client = self._get_client()

        res = client.get(f"{self.ip}/nat_glb.cgi?v=vhost")
        portmaps_match = re.search(r"portmaps:\[(.*?)\]", res.text, re.DOTALL)
        if not portmaps_match:
            return []

        entries = re.split(r"\}\s*,\s*\{", portmaps_match.group(1))
        rules: List[PortForwardRule] = []

        for entry in entries:
            entry = entry.strip("{} ")
            if not entry:
                continue

            oid_m = re.search(r"_oid:(\d+)", entry)
            enabled_m = re.search(r"PortMappingEnabled:(\d+)", entry)
            ext_m = re.search(r"ExternalPort:(\d+)", entry)
            int_m = re.search(r"InternalPort:(\d+)", entry)
            ip_m = re.search(r"InternalClient:\s*'([^']+)'", entry)
            proto_m = re.search(r"PortMappingProtocol:\s*'([^']+)'", entry)

            if ext_m and int_m and ip_m:
                proto = proto_m.group(1) if proto_m else "TCP"
                if proto not in ["TCP", "UDP", "TCP/UDP"]:
                    proto = "TCP"

                rules.append(
                    PortForwardRule(
                        oid=int(oid_m.group(1)) if oid_m else None,
                        enabled=bool(int(enabled_m.group(1))) if enabled_m else True,
                        external_port=int(ext_m.group(1)),
                        internal_port=int(int_m.group(1)),
                        server_ip=ip_m.group(1),
                        protocol=proto,
                    )
                )

        return rules

    def add_port_forward(
        self,
        external_port: int,
        internal_port: int,
        server_ip: str,
        protocol: str = "TCP",
    ) -> bool:
        """Adds a port forwarding rule on the router."""
        rule = PortForwardRule(
            external_port=external_port,
            internal_port=internal_port,
            server_ip=server_ip,
            protocol=protocol.upper(),
        )

        self.login()
        client = self._get_client()

        vhost_url = f"{self.ip}/nat_glb.cgi?v=vhost"
        res = client.get(vhost_url)
        csrf_token = self._extract_csrf(res.text)

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "appname": "0",
            "nat_value": "0",
            "etPortStart": str(rule.external_port),
            "etPortEnd": str(rule.external_port),
            "inPortStart": str(rule.internal_port),
            "inPortEnd": str(rule.internal_port),
            "servername": "0",
            "serverIp": rule.server_ip,
            "proto": rule.protocol,
            "en_map": "on",
            "wanif": "ppp,1,1,1",
            "add": "Add",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": vhost_url,
            "Origin": self.ip,
        }

        add_res = client.post(f"{self.ip}/nat_glb.cgi?v=add_vhost", data=payload, headers=headers)
        if add_res.status_code != 200:
            raise RuntimeError(f"Router rejected port forward request: HTTP {add_res.status_code}")

        expected = f"ExternalPort:{rule.external_port}"
        if expected in add_res.text:
            return True

        verify_res = client.get(vhost_url)
        if expected in verify_res.text:
            return True

        raise RuntimeError("Rule was submitted but did not appear in active port forward table.")

    def delete_port_forward(self, external_port: int) -> bool:
        """Deletes a port forwarding rule by its external port number."""
        self.login()
        client = self._get_client()

        vhost_url = f"{self.ip}/nat_glb.cgi?v=vhost"
        res = client.get(vhost_url)
        html = res.text

        # Search for deletion link in the generated HTML table rows
        row_pattern = (
            rf'<tr>.*?<td>{external_port}~{external_port}</td>.*?'
            rf'href="[^"]*del_vhost(?:&amp;|&)t=([^&"]+)(?:&amp;|&)id=([^&"]+)".*?</tr>'
        )
        row_match = re.search(row_pattern, html, re.DOTALL)

        t_val = None
        found_id = None

        if row_match:
            t_val = row_match.group(1)
            found_id = row_match.group(2)
        else:
            # Fallback regex scanning the JS port_mappings structure
            js_match = re.search(r"var port_mappings=\[(.*?)\];\s*var", html, re.DOTALL)
            if js_match:
                js_text = js_match.group(1)
                pm_matches = re.finditer(rf'\{{[^}}]*ExternalPort:{external_port},[^}}]*\}}', js_text)
                for pm_m in pm_matches:
                    pm_oid = re.search(r"_oid:(\d+)", pm_m.group(0))
                    if pm_oid:
                        prefix = js_text[: pm_m.start()]
                        wan_m = list(re.finditer(r"did:(\d+),\s*_oid:(\d+)", prefix))
                        conn_m = list(
                            re.finditer(
                                r"(?:X_ASB_COM_IfName:\s*'([^']+)'|Name:\s*'[^']+').*?_oid:(\d+)",
                                prefix,
                                re.DOTALL,
                            )
                        )
                        if wan_m and conn_m:
                            last_wan = wan_m[-1]
                            last_conn = conn_m[-1]
                            is_ppp = True
                            if "ppp" not in last_conn.group(0).lower():
                                is_ppp = False
                            found_id = f"{last_wan.group(1)},{last_wan.group(2)},{last_conn.group(2)},{pm_oid.group(1)}"
                            t_val = "ppp" if is_ppp else "ip"
                            break

        if not found_id or not t_val:
            raise ValueError(f"No active port forward rule found for external port {external_port}")

        del_url = f"{self.ip}/nat_glb.cgi?v=del_vhost&t={t_val}&id={found_id}"
        del_res = client.get(del_url)
        return del_res.status_code == 200

    def get_dmz(self) -> DMZConfig:
        """Retrieves the current DMZ status and configured IP."""
        self.login()
        client = self._get_client()

        res = client.get(f"{self.ip}/nat_glb.cgi?v=alg")
        match = re.search(r"dmz:\{([^}]+)\}", res.text, re.DOTALL)
        if not match:
            return DMZConfig(enabled=False, ip_address="0.0.0.0")

        block = match.group(1)
        en_m = re.search(r"DmzEnabled:(\d+)", block)
        ip_m = re.search(r"InternalClient:'([^']*)'", block)

        return DMZConfig(
            enabled=bool(int(en_m.group(1))) if en_m else False,
            ip_address=ip_m.group(1) if ip_m else "0.0.0.0",
        )

    def set_dmz(self, target_ip: str, enabled: bool = True) -> bool:
        """Enables or disables DMZ for a given local IPv4 address."""
        if enabled:
            ipaddress.ip_address(target_ip)

        self.login()
        client = self._get_client()

        alg_url = f"{self.ip}/nat_glb.cgi?v=alg"
        res = client.get(alg_url)
        csrf_token = self._extract_csrf(res.text)

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "wanif": "ppp,1,1,1",
            "dmzEnable": "on" if enabled else "",
            "servername": target_ip if enabled else "other",
            "dmzAddr": target_ip if enabled else "0.0.0.0",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": alg_url,
            "Origin": self.ip,
        }

        post_res = client.post(f"{self.ip}/nat_glb.cgi?v=cfg_dmz", data=payload, headers=headers)
        if post_res.status_code != 200:
            raise RuntimeError(f"Failed to update DMZ configuration: HTTP {post_res.status_code}")

        # Verification
        verify_res = client.get(alg_url)
        target_check = f"InternalClient:'{target_ip}'" if enabled else "DmzEnabled:0"
        return target_check in verify_res.text

    def set_dns(self, primary: str, secondary: str) -> bool:
        """Sets primary and secondary IPv4 DNS servers on the LAN DHCP server."""
        ipaddress.ip_address(primary)
        ipaddress.ip_address(secondary)

        self.login()
        client = self._get_client()

        lan_url = f"{self.ip}/lan_ipv4.cgi"
        res = client.get(lan_url)
        csrf_token = self._extract_csrf(res.text)

        # Extract current network parameters to preserve them
        def extract_var(name: str) -> str:
            m = re.search(rf"{name}:'([^']*)'", res.text)
            return m.group(1) if m else ""

        eth_ip = extract_var("IPInterfaceIPAddress") or "192.168.1.254"
        mask = extract_var("SubnetMask") or "255.255.255.0"
        start_ip = extract_var("MinAddress") or "192.168.1.64"
        end_ip = extract_var("MaxAddress") or "192.168.1.253"

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "ethIpAddress": eth_ip,
            "ethSubnetMask": mask,
            "dhcpEnable": "on",
            "dhcpEthStart": start_ip,
            "dhcpEthEnd": end_ip,
            "dhcpLeasedTime": "86400",
            "firstDns": primary,
            "secondDns": secondary,
            "isReboot_1": "0",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": lan_url,
            "Origin": self.ip,
        }

        post_res = client.post(f"{self.ip}/lan_ipv4.cgi?config", data=payload, headers=headers)
        return post_res.status_code == 200

    def set_dos_protection(self, enabled: bool = False) -> bool:
        """Enables or disables the firewall's naive DoS / Attack Protection filter."""
        self.login()
        client = self._get_client()

        fire_url = f"{self.ip}/firewall.cgi?fire"
        res = client.get(fire_url)
        csrf_token = self._extract_csrf(res.text)

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "firewall_level": "Off",
            "dos_protection_enable": "1" if enabled else "0",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": fire_url,
            "Origin": self.ip,
        }

        post_res = client.post(fire_url, data=payload, headers=headers)
        return post_res.status_code == 200

    def set_algs(self, disable_problematic: bool = True) -> bool:
        """Disables SIP, H.323, RTSP, and FTP ALGs that corrupt gaming packets and voice chat."""
        self.login()
        client = self._get_client()

        alg_url = f"{self.ip}/nat_glb.cgi?v=alg"
        res = client.get(alg_url)
        csrf_token = self._extract_csrf(res.text)

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "AlgIpsecEnabled": "on",
            "AlgL2tpEnabled": "on",
            "AlgPPTPEnabled": "on",
        }

        if not disable_problematic:
            payload.update({
                "AlgFtpEnabled": "on",
                "AlgTftpEnabled": "on",
                "AlgSipEnabled": "on",
                "AlgH323Enabled": "on",
                "AlgRtspEnabled": "on",
            })

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": alg_url,
            "Origin": self.ip,
        }

        post_res = client.post(f"{self.ip}/nat_glb.cgi?v=cfg_alg", data=payload, headers=headers)
        return post_res.status_code == 200

    def set_upnp(self, enabled: bool = True) -> bool:
        """Enables or disables UPnP."""
        self.login()
        client = self._get_client()

        upnp_url = f"{self.ip}/upnp.cgi"
        res = client.get(upnp_url)
        csrf_token = self._extract_csrf(res.text)

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "upnp_enable": "on" if enabled else "",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": upnp_url,
            "Origin": self.ip,
        }

        post_res = client.post(f"{self.ip}/upnp.cgi?config_glb", data=payload, headers=headers)
        return post_res.status_code == 200

    def optimize_gaming(self, target_ip: str) -> GamingOptimizationResult:
        """One-click macro: puts target into DMZ, disables DoS filter, disables SIP ALG, enables UPnP."""
        ipaddress.ip_address(target_ip)

        dmz_ok = self.set_dmz(target_ip, enabled=True)
        dos_ok = self.set_dos_protection(enabled=False)
        alg_ok = self.set_algs(disable_problematic=True)
        upnp_ok = self.set_upnp(enabled=True)

        return GamingOptimizationResult(
            target_ip=target_ip,
            dmz_configured=dmz_ok,
            dos_protection_disabled=dos_ok,
            sip_alg_disabled=alg_ok,
            upnp_enabled=upnp_ok,
            message=f"Gaming optimizations successfully applied to target {target_ip}!",
        )

    def reboot(self) -> bool:
        """Sends a soft-reboot command to the GPON gateway."""
        self.login()
        client = self._get_client()

        reboot_url = f"{self.ip}/maintenance_reboot.cgi"
        res = client.get(reboot_url)
        csrf_token = self._extract_csrf(res.text)

        payload = {
            "data": "data",
            "csrf_token": csrf_token,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": reboot_url,
            "Origin": self.ip,
        }

        post_url = f"{self.ip}/maintenance_reboot.cgi?reboot"
        client.post(post_url, data=payload, headers=headers)
        self._is_logged_in = False
        return True

    def get_optical_status(self) -> OpticalStatus:
        """Retrieves fiber optic transceiver signal telemetry (TX/RX power, temp, bias)."""
        self.login()
        client = self._get_client()

        res = client.get(f"{self.ip}/wan_status.cgi?gpon")

        def parse_val(k: str) -> float:
            m = re.search(rf"{k}:([0-9.]+)", res.text)
            return float(m.group(1)) if m else 0.0

        tx_raw = parse_val("TXPower")
        rx_raw = parse_val("RXPower")
        temp_raw = parse_val("TransceiverTemperature")
        bias_raw = parse_val("BiasCurrent")

        def to_dbm(mw: float) -> float:
            if mw <= 0:
                return -99.0
            return round(10.0 * math.log10(mw * 0.0001), 2)

        tx_dbm = to_dbm(tx_raw)
        rx_dbm = to_dbm(rx_raw)
        temp_c = round(temp_raw / 256.0, 2)
        bias_ua = bias_raw * 2.0

        # Assess fiber quality based on standard ITU-T G.984 GPON Class B+ sensitivity
        if -25.0 <= rx_dbm <= -8.0:
            quality = "Excellent / Healthy"
        elif -28.0 <= rx_dbm < -25.0:
            quality = "Fair / Marginal Loss"
        elif rx_dbm < -28.0:
            quality = "Critical / High Attenuation"
        else:
            quality = "Warning / Overload (> -8 dBm)"

        return OpticalStatus(
            tx_power_dbm=tx_dbm,
            rx_power_dbm=rx_dbm,
            transceiver_temperature=temp_c,
            bias_current_ua=bias_ua,
            signal_quality=quality,
        )

    def get_wifi_config(self) -> WifiConfig:
        """Retrieves current 2.4GHz Wi-Fi configuration (SSID, channel, transmit power, WMM)."""
        self.login()
        client = self._get_client()

        res = client.get(f"{self.ip}/wlan_config.cgi")
        ssid_m = re.search(r"SSID:'([^']*)'", res.text) or re.search(r'wl_ssidname"[^>]*value="([^"]*)"', res.text)
        chan_m = re.search(r"ChannelsInUse:'([^']*)'", res.text) or re.search(r"Channel:(\d+)", res.text)
        pwr_m = re.search(r"TransmitPower:(\d+)", res.text)
        wmm_m = re.search(r"WMMEnable:(\d+)", res.text)
        en_m = re.search(r"Enable:(\d+)", res.text)

        return WifiConfig(
            enabled=bool(int(en_m.group(1))) if en_m else True,
            ssid=ssid_m.group(1) if ssid_m else "",
            channel=chan_m.group(1) if chan_m else "Auto",
            power_percent=int(pwr_m.group(1)) if pwr_m else 100,
            wmm_enabled=bool(int(wmm_m.group(1))) if wmm_m else True,
            broadcast_ssid=True,
        )

    def set_wifi_channel(self, channel: int | str) -> bool:
        """Switches Wi-Fi operating channel (e.g. 1, 6, 11, or 'Auto')."""
        self.login()
        client = self._get_client()

        wlan_url = f"{self.ip}/wlan_config.cgi"
        res = client.get(wlan_url)
        csrf_token = self._extract_csrf(res.text)

        # Get existing values
        cur_cfg = self.get_wifi_config()
        is_auto = str(channel).lower() == "auto" or channel == 0
        chan_val = "0" if is_auto else str(channel)

        payload = {
            "csrf_token": csrf_token,
            "passwd_token_value": "",
            "wl_power": str(cur_cfg.power_percent),
            "wl_NChannelwidth": "0",  # 20MHz
            "wl_channel": chan_val,
            "wl_wmm": "1" if cur_cfg.wmm_enabled else "0",
            "wl_id": "1",
            "wl_ssidname": cur_cfg.ssid,
            "wl_en": "1" if cur_cfg.enabled else "0",
            "wl_broad": "1",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": wlan_url,
            "Origin": self.ip,
        }

        post_res = client.post(f"{self.ip}/wlan_config.cgi?do_config_glb", data=payload, headers=headers)
        return post_res.status_code == 200

    def get_ethernet_ports(self) -> List[EthernetPortStatus]:
        """Retrieves physical Ethernet LAN port statuses and link speeds (1000M vs 100M)."""
        self.login()
        client = self._get_client()

        res = client.get(f"{self.ip}/lan_status.cgi?lan")
        ports: List[EthernetPortStatus] = []

        for port_id in range(1, 5):
            m = re.search(rf"{port_id}:\{{([^\}}]+)\s*stat:\{{([^\}}]+)\}}\s*\}}", res.text)
            if m:
                block = m.group(1)
                stat = m.group(2)

                st_m = re.search(r"Status:'([^']*)'", block)
                speed_m = re.search(r"X_ALU_COM_CurMaxBitRate:'([^']*)'", block)
                duplex_m = re.search(r"X_ALU_COM_CurDuplexMode:'([^']*)'", block)

                bytes_sent = re.search(r"BytesSent:(\d+)", stat)
                bytes_rx = re.search(r"BytesReceived:(\d+)", stat)
                pkts_sent = re.search(r"PacketsSent:(\d+)", stat)
                pkts_rx = re.search(r"PacketsReceived:(\d+)", stat)
                errs_rx = re.search(r"ErrorsReceived:(\d+)", stat)
                drops_rx = re.search(r"DiscardPacketsReceived:(\d+)", stat)

                speed_val = (
                    int(speed_m.group(1))
                    if speed_m and speed_m.group(1).isdigit()
                    else 0
                )

                ports.append(
                    EthernetPortStatus(
                        port_id=port_id,
                        status=st_m.group(1) if st_m else "NoLink",
                        speed_mbps=speed_val,
                        duplex=duplex_m.group(1) if duplex_m else "Auto",
                        bytes_sent=int(bytes_sent.group(1)) if bytes_sent else 0,
                        bytes_received=int(bytes_rx.group(1)) if bytes_rx else 0,
                        packets_sent=int(pkts_sent.group(1)) if pkts_sent else 0,
                        packets_received=int(pkts_rx.group(1)) if pkts_rx else 0,
                        errors_received=int(errs_rx.group(1)) if errs_rx else 0,
                        drops_received=int(drops_rx.group(1)) if drops_rx else 0,
                    )
                )

        return ports

