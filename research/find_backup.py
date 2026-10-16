import asyncio
from browserless_gpon import GPONClient
import re
client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/menu.cgi")
print("MENU.CGI:")
for line in res.text.splitlines():
    if 'backup' in line.lower() or 'restore' in line.lower() or 'cfg' in line.lower() or 'export' in line.lower():
        print(line)

res2 = client.session.get(f"{client.ip}/maintenance.cgi")
print("\nMAINTENANCE.CGI:")
for line in res2.text.splitlines():
    if 'backup' in line.lower() or 'restore' in line.lower() or 'cfg' in line.lower() or 'export' in line.lower():
        print(line)
