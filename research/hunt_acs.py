import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def find_acs_endpoint():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        
        print("[*] Navigating to router login page...")
        await page.goto(os.getenv("ROUTER_IP"))
        
        print("[*] Entering credentials...")
        inputs = await page.locator("input").all()
        for input_field in inputs:
            if not await input_field.is_visible(): continue
            input_type = await input_field.get_attribute("type")
            if input_type == 'text':
                await input_field.fill(os.getenv("ROUTER_USER"))
            elif input_type == 'password':
                await input_field.fill(os.getenv("ROUTER_PASS"))

        print("[*] Bypassing the login hurdle...")
        buttons = page.locator("button, input[type='button'], input[type='submit'], a")
        for i in range(await buttons.count()):
            btn = buttons.nth(i)
            if await btn.is_visible():
                text = (await btn.text_content() or await btn.get_attribute("value") or "").lower()
                if "log" in text or "sign" in text or "submit" in text:
                    await btn.click()
                    break
                    
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        await asyncio.sleep(3)
        print("[*] Logged in successfully! Scanning DOM and JS...")
        
        findings = await page.evaluate("""
            () => {
                let data = [];
                document.querySelectorAll('*').forEach(el => {
                    ['href', 'src', 'action', 'onclick', 'value', 'name', 'id'].forEach(attr => {
                        let val = el.getAttribute(attr);
                        if (val && val.match(/tr069|acs|cwmp|management|mgmt/i)) {
                            data.push({source: 'DOM', tag: el.tagName, attr: attr, val: val});
                        }
                    });
                });
                document.querySelectorAll('script').forEach(s => {
                    if (s.innerHTML.match(/tr069|acs|cwmp|management|mgmt/i)) {
                        data.push({source: 'InlineScript', snippet: s.innerHTML.substring(0, 300)});
                    }
                });
                return data;
            }
        """)
        
        print(f"\n[+] Found {len(findings)} potential matches in DOM/JS:")
        for f in findings:
            print(f" -> {f}")
            
        print("\n[*] Brute-forcing common hidden Nokia TR-069 endpoints...")
        endpoints = [
            "/menu.cgi", "/tree.xml", "/left.asp", "/top.asp", 
            "/cgi-bin/tr069.cgi", "/cgi-bin/acs.cgi", "/cgi-bin/cwmp.cgi",
            "/cgi-bin/management_server.cgi", "/tr069_conf.asp", "/act_tr069.cgi",
            "/cgi-bin/tr069_conf.cgi", "/mgmt_server.asp", "/cgi-bin/mgmt.cgi"
        ]
        
        for ep in endpoints:
            try:
                resp = await page.goto(os.getenv("ROUTER_IP") + ep)
                if resp and resp.status == 200:
                    content = await resp.text()
                    if any(kw in content.lower() for kw in ["tr069", "acs", "cwmp", "managementserver", "autoconfig", "mgmt"]):
                        print(f"[!] BINGO! Found TR-069 data at: {ep}")
                        fname = f"dump_{ep.replace('/', '_').strip('_')}.html"
                        with open(fname, "w") as f:
                            f.write(content)
                        print(f"    -> Saved to {fname}")
            except Exception:
                pass

        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_acs_endpoint())
