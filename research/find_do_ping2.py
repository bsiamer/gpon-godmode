import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/diag.cgi?ping")

if 'do_ping' in res.text:
    lines = res.text.splitlines()
    for i, line in enumerate(lines):
        if 'do_ping' in line:
            start = i + 80
            end = i + 150
            print("\n".join(lines[start:end]))
            break
