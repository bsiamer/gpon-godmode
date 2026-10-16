import asyncio
from browserless_gpon import GPONClient
import re

client = GPONClient()
client.login()
res = client.session.get(f"{client.ip}/diag.cgi?ping")
# Extract scripts
scripts = re.findall(r'<script.*?src="([^"]+)".*?></script>', res.text)
print("Scripts:", scripts)

for script in scripts:
    if not script.startswith('/'):
        script = '/' + script
    try:
        js_res = client.session.get(f"{client.ip}{script}")
        if 'function do_ping' in js_res.text:
            print(f"\nFOUND do_ping in {script}:\n")
            # Find do_ping function body
            lines = js_res.text.splitlines()
            for i, line in enumerate(lines):
                if 'function do_ping' in line:
                    print("\n".join(lines[i:i+50]))
                    break
    except Exception as e:
        print(f"Skipping {script}: {e}")
