import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import re

load_dotenv()

async def debug_routing():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        
        try:
            print("Navigating to", os.environ.get("ROUTER_IP"))
            await page.goto(os.environ.get("ROUTER_IP"))
            
            # Login
            print("Logging in...")
            inputs = await page.locator("input").all()
            for input_field in inputs:
                if not await input_field.is_visible(): continue
                input_type = await input_field.get_attribute("type")
                if input_type == 'text':
                    await input_field.fill(os.environ.get("ROUTER_USER"))
                elif input_type == 'password':
                    await input_field.fill(os.environ.get("ROUTER_PASS"))
            
            buttons = page.locator("button, input[type='button'], input[type='submit'], a")
            for i in range(await buttons.count()):
                btn = buttons.nth(i)
                if await btn.is_visible():
                    text = (await btn.text_content() or await btn.get_attribute("value") or "").lower()
                    if "log" in text or "sign" in text or "submit" in text:
                        await btn.click()
                        break
            
            await asyncio.sleep(5)
            print("Logged in. Current URL:", page.url)
            
            # Inspect frames
            print("\nInitial frames list:")
            for idx, frame in enumerate(page.frames):
                print(f"Frame {idx}: name={frame.name}, url={frame.url}")
                
            # Click "Application"
            print("\nClicking 'Application' menu...")
            pattern = re.compile("Application", re.IGNORECASE)
            clicked = False
            for frame in page.frames:
                elem = frame.get_by_text(pattern)
                if await elem.count() > 0 and await elem.first.is_visible():
                    print(f"Found 'Application' in frame: {frame.name or 'main'}")
                    await elem.first.click()
                    clicked = True
                    break
            
            if not clicked:
                print("Failed to click Application menu")
                return
                
            await asyncio.sleep(3)
            
            # Click "Port Forwarding"
            print("\nClicking 'Port Forwarding'...")
            pattern = re.compile("Port Forwarding", re.IGNORECASE)
            clicked = False
            for frame in page.frames:
                elem = frame.get_by_text(pattern)
                if await elem.count() > 0 and await elem.first.is_visible():
                    print(f"Found 'Port Forwarding' in frame: {frame.name or 'main'}")
                    await elem.first.click()
                    clicked = True
                    break
                    
            if not clicked:
                print("Failed to click Port Forwarding sub-menu")
                return
                
            await asyncio.sleep(5)
            
            print("\nFrames list after navigation:")
            for idx, frame in enumerate(page.frames):
                print(f"Frame {idx}: name={frame.name}, url={frame.url}")
                
            # Check for input field in each frame
            print("\nSearching for input[name='etPortStart']:")
            for idx, frame in enumerate(page.frames):
                count = await frame.locator("input[name='etPortStart']").count()
                print(f"Frame {idx} ({frame.name or 'main'}): found {count} occurrences")
                if count > 0:
                    html = await frame.locator("input[name='etPortStart']").first.evaluate("el => el.outerHTML")
                    print(f"  Outer HTML: {html}")
                    
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_routing())
