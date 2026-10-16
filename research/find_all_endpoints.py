import asyncio
from browserless_gpon import GPONClient
import re
client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/menu.cgi")
print("All endpoints in menu.cgi:")
for match in re.findall(r'target:"([^"]+)"', res.text):
    print(match)
