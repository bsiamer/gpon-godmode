import re
import sys
import os
from browserless_gpon import GPONClient

def debug_add(external_port: int, internal_port: int, server_ip: str, protocol: str = "TCP"):
    client = GPONClient()
    print("Logging in...")
    client.login()
    
    vhost_url = f"{client.ip}/nat_glb.cgi?v=vhost"
    print("Fetching vhost URL...")
    res = client.session.get(vhost_url)
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', res.text)
    if not csrf_match:
        csrf_match = re.search(r"csrf_token=([a-zA-Z0-9]+)", res.text)
    csrf_token = csrf_match.group(1)
    print("CSRF token:", csrf_token)
    
    payload = {
        "csrf_token": csrf_token,
        "passwd_token_value": "",
        "appname": "0",
        "nat_value": "0",
        "etPortStart": str(external_port),
        "etPortEnd": str(external_port),
        "inPortStart": str(internal_port),
        "inPortEnd": str(internal_port),
        "servername": "0",
        "serverIp": server_ip,
        "proto": protocol,
        "en_map": "on",
        "wanif": "ppp,1,1,1",
        "add": "Add"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": vhost_url,
        "Origin": client.ip
    }
    
    add_url = f"{client.ip}/nat_glb.cgi?v=add_vhost"
    print("Submitting POST to:", add_url)
    add_res = client.session.post(add_url, data=payload, headers=headers)
    print("POST Response status:", add_res.status_code)
    
    expected_pattern = f"ExternalPort:{external_port}"
    print(f"Pattern '{expected_pattern}' in POST response: {expected_pattern in add_res.text}")
    
    # Save the POST response HTML
    with open("add_res.html", "w", encoding="utf-8") as f:
        f.write(add_res.text)
    print("Saved POST response to add_res.html")
    
    print("Fetching vhost URL again...")
    res_verify = client.session.get(vhost_url)
    print(f"Pattern '{expected_pattern}' in verify response: {expected_pattern in res_verify.text}")
    
    with open("verify_res.html", "w", encoding="utf-8") as f:
        f.write(res_verify.text)
    print("Saved verify response to verify_res.html")

if __name__ == "__main__":
    debug_add(18888, 18888, "192.168.1.154")
