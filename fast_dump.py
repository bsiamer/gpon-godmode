import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

required_vars = ["ROUTER_IP", "ROUTER_USER", "ROUTER_PASS"]
if any(not os.getenv(var) for var in required_vars):
    raise RuntimeError("Missing essential .env configuration. Please ensure ROUTER_IP, ROUTER_USER, and ROUTER_PASS are set.")

async def dump_docs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        page.set_default_timeout(5000)
        
        try:
            router_ip = os.environ.get("ROUTER_IP")
            await page.goto(router_ip)
        except Exception:
            pass
            
        # Login
        try:
            await page.locator("input[type='text'], input[id*='user'], input[name*='user']").first.fill(os.environ.get("ROUTER_USER"))
            await page.locator("input[type='password'], input[id*='pass'], input[name*='pass']").first.fill(os.environ.get("ROUTER_PASS"))
            buttons = page.locator("button, input[type='button'], input[type='submit'], a")
            for i in range(await buttons.count()):
                btn = buttons.nth(i)
                if await btn.is_visible():
                    text = (await btn.text_content() or await btn.get_attribute("value") or "").lower()
                    if "log" in text or "sign" in text or "submit" in text:
                        await btn.click()
                        break
        except Exception as e:
            print("Login error", e)
            
        await asyncio.sleep(5)
        
        async def click_menu(name):
            for frame in page.frames:
                try:
                    elem = frame.get_by_text(name, exact=True)
                    if await elem.count() > 0 and await elem.first.is_visible():
                        await elem.first.click()
                        return True
                except Exception:
                    pass
            return False

        menus_map = {
            "Status": ["Device Information", "LAN Status", "WAN Status", "WAN Status IPv6", "Home Networking", "Optics Module Status", "Statistics", "Voice Information"],
            "Network": ["LAN", "LAN_IPv6", "WAN", "Wireless (2.4GHz)", "Wireless Schedule"],
            "Security": ["Firewall", "MAC Filter", "IP Filter", "URL Filter", "Parental Control", "DMZ and ALG"],
            "Application": ["Port Forwarding", "Port Triggering", "DDNS", "NTP", "USB", "UPNP and DLNA"],
            "Maintenance": ["Password", "Speed Test", "Device Management", "Reboot Device", "Factory Default", "Diagnostics", "Log"]
        }
        
        artifact_path = "router_settings.md"
        
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write("# GPON Home Gateway - Full Settings Documentation\n\n")
            f.flush()
            
            for main_menu, submenus in menus_map.items():
                f.write(f"## {main_menu}\n\n")
                f.flush()
                await click_menu(main_menu)
                await asyncio.sleep(2)
                
                for sub in submenus:
                    f.write(f"### {sub}\n")
                    f.flush()
                    
                    await click_menu(sub)
                    await asyncio.sleep(2) # Wait for page load
                    
                    # Scrape mainFrame content
                    content_found = False
                    for frame in page.frames:
                        if frame.name == "mainFrame":
                            try:
                                body_text = await frame.locator("body").inner_text()
                                lines = body_text.split('\n')
                                clean_lines = []
                                for line in lines:
                                    line = line.strip()
                                    if line and len(line) < 150 and "{" not in line and "function(" not in line:
                                        clean_lines.append(f"- {line}")
                                
                                inputs = await frame.locator("input, select").all()
                                for inp in inputs:
                                    name = await inp.get_attribute("name") or await inp.get_attribute("id")
                                    type_ = await inp.get_attribute("type") or await inp.evaluate("el => el.tagName.toLowerCase()")
                                    if name and type_ != "hidden":
                                        clean_lines.append(f"- *[{type_} field]:* `{name}`")
                                
                                if clean_lines:
                                    seen_lines = set()
                                    dedup_lines = []
                                    for l in clean_lines:
                                        if l not in seen_lines:
                                            dedup_lines.append(l)
                                            seen_lines.add(l)
                                    
                                    f.write("\n".join(dedup_lines) + "\n\n")
                                    f.flush()
                                    content_found = True
                            except Exception as e:
                                f.write(f"- Error extracting page data: {e}\n\n")
                                f.flush()
                                content_found = True
                    if not content_found:
                        f.write("- *(No extractable text or settings found on this page)*\n\n")
                        f.flush()

        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(dump_docs())
