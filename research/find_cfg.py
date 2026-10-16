import asyncio
from browserless_gpon import GPONClient

client = GPONClient()
client.login()

endpoints = [
    "/romfile.cfg",
    "/backup_glb.cgi",
    "/backup.cgi",
    "/hw_tree.xml",
    "/cfg_mac.cgi",
    "/config.bin",
    "/get_config.cgi"
]

for ep in endpoints:
    url = f"{client.ip}{ep}"
    try:
        r = client.session.get(url, allow_redirects=False)
        print(f"GET {ep} -> {r.status_code} ({len(r.content)} bytes)")
    except Exception as e:
        print(f"GET {ep} -> Error: {e}")
