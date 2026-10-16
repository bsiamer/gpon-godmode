import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/tr069.cgi")

if res.status_code == 200 and 'tr069' in res.text.lower():
    lines = res.text.splitlines()
    found = False
    for i, line in enumerate(lines):
        if 'enable' in line.lower() and 'tr069' in line.lower():
            start = max(0, i-5)
            end = min(len(lines), i+15)
            print("\n".join(lines[start:end]))
            found = True
            break
    if not found:
        print("Found tr069.cgi but couldn't locate enable status.")
        print(res.text[:1000])
else:
    print(f"tr069.cgi returned {res.status_code}")
