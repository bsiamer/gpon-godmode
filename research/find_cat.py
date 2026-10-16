import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/diag.cgi?ping")

if 'function cat(' in res.text:
    lines = res.text.splitlines()
    for i, line in enumerate(lines):
        if 'function cat(' in line:
            print("\n".join(lines[i:i+30]))
            break
