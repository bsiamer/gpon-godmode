import asyncio
from browserless_gpon import GPONClient
import re
client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/restore.cgi")
print(res.text)
