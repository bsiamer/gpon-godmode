import re
import os
from browserless_gpon import GPONClient

def list_port_forwardings():
    client = GPONClient()
    print("Logging into router at", client.ip)
    client.login()
    
    vhost_url = f"{client.ip}/nat_glb.cgi?v=vhost"
    print("Fetching port forwarding config page...")
    res = client.session.get(vhost_url)
    if res.status_code != 200:
        print("Failed to fetch port forwarding config page, status code:", res.status_code)
        return

    html = res.text
    # Let's extract the portmaps array
    # It looks like: portmaps:[{ ... }, { ... }]
    # We can extract all elements inside portmaps
    # Let's find "portmaps:[" and match everything up to the next closing bracket/script tag
    portmaps_match = re.search(r'portmaps:\[(.*?)\]', html, re.DOTALL)
    if not portmaps_match:
        print("Could not find portmaps array in HTML. Here's a sample of HTML:")
        print(html[:1000])
        return
        
    portmaps_str = portmaps_match.group(1)
    
    # Each entry is like: {PortMappingEnabled:1,PortMappingLeaseDuration:0,...,InternalClient:'192.168.1.154',ExternalPort:8080,...}
    # Let's split by } followed by , and {
    entries = re.split(r'\}\s*,\s*\{', portmaps_str)
    
    print("\n--- Current Port Forwarding Rules ---")
    print(f"{'Index':<5} | {'Enabled':<7} | {'Ext Port':<8} | {'Int Port':<8} | {'Internal Client':<16} | {'Protocol':<10}")
    print("-" * 65)
    
    for idx, entry in enumerate(entries):
        # clean up braces
        entry = entry.strip('{} ')
        if not entry:
            continue
            
        # extract properties using simple regex
        enabled = re.search(r'PortMappingEnabled:(\d+)', entry)
        ext_port = re.search(r'ExternalPort:(\d+)', entry)
        int_port = re.search(r'InternalPort:(\d+)', entry)
        client_ip = re.search(r"InternalClient:\s*'([^']+)'", entry)
        protocol = re.search(r"PortMappingProtocol:\s*'([^']+)'", entry)
        
        val_enabled = enabled.group(1) if enabled else "N/A"
        val_ext = ext_port.group(1) if ext_port else "N/A"
        val_int = int_port.group(1) if int_port else "N/A"
        val_ip = client_ip.group(1) if client_ip else "N/A"
        val_proto = protocol.group(1) if protocol else "N/A"
        
        print(f"{idx:<5} | {val_enabled:<7} | {val_ext:<8} | {val_int:<8} | {val_ip:<16} | {val_proto:<10}")

if __name__ == "__main__":
    list_port_forwardings()
