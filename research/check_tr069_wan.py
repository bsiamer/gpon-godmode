import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/wan_config_glb.cgi")

lines = res.text.splitlines()
for line in lines:
    if '2_TR069_R_VID_3000' in line:
        print("FOUND TR069 Profile:")
        print(line)
        break
else:
    print("TR069 Profile '2_TR069_R_VID_3000' is NOT present in WAN configurations.")
