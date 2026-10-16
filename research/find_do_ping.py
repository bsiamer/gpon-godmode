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
            # Print a few lines before and after to get the context
            start = max(0, i-20)
            end = min(len(lines), i+80)
            print("\n".join(lines[start:end]))
            break
