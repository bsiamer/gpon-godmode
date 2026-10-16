import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/wan_config_glb.cgi")

lines = res.text.splitlines()
for i, line in enumerate(lines):
    if '2_TR069_R_VID_3000' in line:
        start = max(0, i-2)
        end = min(len(lines), i+15)
        print("\n".join(lines[start:end]))
        break
