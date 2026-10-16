import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/wan_config_glb.cgi")

if "TR069" in res.text or "tr069" in res.text.lower():
    lines = res.text.splitlines()
    for i, line in enumerate(lines):
        if 'tr069' in line.lower():
            start = max(0, i-5)
            end = min(len(lines), i+15)
            print("\n".join(lines[start:end]))
            break
else:
    print("TR069 not found on wan_config_glb.cgi")
