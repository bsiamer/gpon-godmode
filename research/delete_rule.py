import re
import os
import sys
from browserless_gpon import GPONClient

def delete_port_forward(ext_port: int):
    client = GPONClient()
    print("Logging into router at", client.ip)
    client.login()
    
    vhost_url = f"{client.ip}/nat_glb.cgi?v=vhost"
    print("Fetching port forwarding config page...")
    res = client.session.get(vhost_url)
    if res.status_code != 200:
        print("Failed to fetch port forwarding config page, status code:", res.status_code)
        return False

    html = res.text
    portmaps_match = re.search(r'portmaps:\[(.*?)\]', html, re.DOTALL)
    if not portmaps_match:
        print("Could not find portmaps array in HTML.")
        return False
        
    portmaps_str = portmaps_match.group(1)
    entries = re.split(r'\}\s*,\s*\{', portmaps_str)
    
    found_id = None
    t_val = None
    
    # Let's write a robust parser for the JS port_mappings structure in HTML.
    # The structure: var port_mappings=[{wan_num:1, did:1, _oid:1, ipConns:..., pppConns:[{X_ASB_COM_IfName:..., _oid:1, ..., portmaps:[ {_oid:14, ExternalPort:18888, ...} ] }] }];
    # Since it is JS object literal syntax, not strict JSON (keys aren't quoted), we can parse it dynamically or via regex on the raw HTML block.
    # Let's extract the id by matching the pattern in the HTML rows since they are constructed directly in the page body:
    # <td>18888~18888</td> ... <td><a href="?v=del_vhost&amp;t=ppp&amp;id=1,1,1,14" class="attr">Delete</a></td>
    # Or similarly: <a href="?v=del_vhost&t=ppp&id=1,1,1,14" ...
    
    # We will search the html for the specific row text containing our port
    # A port row looks like: <td>18888~18888</td>
    # Let's use a regex that matches the row containing that text and grabs the del_vhost href.
    row_pattern = rf'<tr>.*?<td>{ext_port}~{ext_port}</td>.*?href="[^"]*del_vhost(?:&amp;|&)t=([^&"]+)(?:&amp;|&)id=([^&"]+)".*?</tr>'
    row_match = re.search(row_pattern, html, re.DOTALL)
    if row_match:
        t_val = row_match.group(1)
        found_id = row_match.group(2)
    else:
        # Fallback to scanning the JS array literal manually:
        # Let's find our port mapping entry matching ExternalPort:18888
        # Since it is a nested structure under pppConns or ipConns:
        # var port_mappings=[{wan_num:1, did:1, _oid:1, ipConns:[...], pppConns:[{_oid:1, ... portmaps:[{_oid:14, ExternalPort:18888}]}]}]
        # Let's look for "did:X" and then the corresponding connection "_oid:Y" and then portmap "_oid:Z".
        # We can write a custom regex parser to match:
        # did:(\d+) ... _oid:(\d+) (of connection) ... _oid:(\d+) (of portmap) ... ExternalPort:18888
        # Let's extract the blocks.
        # Find the wan level blocks:
        wan_blocks = re.findall(r'\{wan_num:\d+,\s*did:(\d+),\s*_oid:(\d+),.*?(?:ipConns|pppConns):\[.*?\]\s*\}', html, re.DOTALL)
        # To make it simple, let's look at the JS array block and extract the full array text
        js_match = re.search(r'var port_mappings=\[(.*?)\];\s*var', html, re.DOTALL)
        if js_match:
            js_text = js_match.group(1)
            # Find the portmap block containing our ExternalPort
            # Example: {_oid:14, ... ExternalPort:18888, ... }
            portmap_pattern = rf'\{{[^}}]*ExternalPort:{ext_port},[^}}]*\}}'
            pm_matches = re.finditer(portmap_pattern, js_text)
            for pm_m in pm_matches:
                pm_str = pm_m.group(0)
                pm_oid = re.search(r'_oid:(\d+)', pm_str)
                if pm_oid:
                    # Now trace back to find the parent pppConn/ipConn _oid and wan did/oid.
                    # Since js_text contains the entire array, we can find the substring up to this portmap entry
                    offset = pm_m.start()
                    prefix = js_text[:offset]
                    
                    # Find last did:(\d+) and _oid:(\d+) of wan
                    wan_matches = list(re.finditer(r'did:(\d+),\s*_oid:(\d+)', prefix))
                    # Find last _oid of connection. A connection entry starts with X_ASB_COM_IfName or Name, and has an _oid field before the portmaps block.
                    # Example: {X_ASB_COM_IfName:'ppp111', Name:'1_INTERNET_R_VID_1000', _oid:1, ConnectionType:'IP_Routed', ...
                    conn_matches = list(re.finditer(r'(?:X_ASB_COM_IfName:\s*\'([^\'\s]+)\'|ConnectionType:\s*\'[^\']+\'|Name:\s*\'[^\']+\').*?_oid:(\d+)', prefix, re.DOTALL))
                    
                    if wan_matches and conn_matches:
                        last_wan = wan_matches[-1]
                        last_conn = conn_matches[-1]
                        
                        # Determine if it's PPP or IP based on the last connection interface name
                        # We look at the first capture group of the match or scan back.
                        # Let's search specifically for the connection block interface name.
                        conn_start = last_conn.start()
                        ifName_match = re.search(r"X_ASB_COM_IfName:\s*'([^']+)'", prefix[conn_start:conn_start+300])
                        if not ifName_match:
                            # search backwards from conn_start
                            ifName_match = re.search(r"X_ASB_COM_IfName:\s*'([^']+)'", prefix[max(0, conn_start-300):conn_start+100])
                            
                        is_ppp = True
                        if ifName_match and not ifName_match.group(1).lower().startswith('ppp'):
                            is_ppp = False
                            
                        found_id = f"{last_wan.group(1)},{last_wan.group(2)},{last_conn.group(2)},{pm_oid.group(1)}"
                        t_val = "ppp" if is_ppp else "ip"
                        break

    if not found_id:
        # Fallback: parse hrefs directly from HTML
        # e.g., <a href="?v=del_vhost&amp;t=ppp&amp;id=1,1,1,12" class="attr">Delete</a>
        # But we need to correlate it with the row. The row has ExternalPort.
        # Let's look at the HTML structure of the table.
        # <tr><td>Customer settings</td><td>...</td><td>18888~18888</td>...<td><a href="?v=del_vhost&amp;t=ppp&amp;id=1,1,1,12"...
        # We can extract all table rows, find the one with 18888~18888, and extract the href.
        rows = re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL)
        for row in rows:
            if f"{ext_port}~{ext_port}" in row:
                href_match = re.search(r'href="[^"]*del_vhost(?:&amp;|&)t=([^&"]+)(?:&amp;|&)id=([^&"]+)"', row)
                if href_match:
                    t_val = href_match.group(1)
                    found_id = href_match.group(2)
                    break

    if not found_id:
        print(f"Could not find deletion parameters for port {ext_port}")
        return False
        
    print(f"Deleting port forward rule with id={found_id}, type={t_val}...")
    del_url = f"{client.ip}/nat_glb.cgi?v=del_vhost&t={t_val}&id={found_id}"
    del_res = client.session.get(del_url)
    if del_res.status_code == 200:
        print(f"Successfully sent delete request for port {ext_port}!")
        return True
    else:
        print(f"Failed to delete rule, status code: {del_res.status_code}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_rule.py <external_port>")
        sys.exit(1)
    delete_port_forward(int(sys.argv[1]))
