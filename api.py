from fastapi import FastAPI, HTTPException
import os
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import re
from playwright.async_api import async_playwright

load_dotenv()

required_vars = ["ROUTER_IP", "ROUTER_USER", "ROUTER_PASS"]
if any(not os.getenv(var) for var in required_vars):
    raise RuntimeError("Missing essential .env configuration. Please ensure ROUTER_IP, ROUTER_USER, and ROUTER_PASS are set.")

app = FastAPI()
router_lock = asyncio.Lock()

class PortForwardRequest(BaseModel):
    external_port: int
    internal_port: int
    server_ip: str
    protocol: str = "TCP"

class ForceSetRequest(BaseModel):
    main_menu: str
    sub_menu: str
    settings: Dict[str, Any]
    submit_button: str

async def click_in_any_frame(page, text):
    await page.wait_for_load_state('networkidle')
    pattern = re.compile(text.strip(), re.IGNORECASE)
    for frame in page.frames:
        try:
            elem = frame.get_by_text(pattern)
            if await elem.count() > 0:
                await elem.first.click()
                return
        except Exception:
            pass

async def wait_for_selector_in_mainframe(page, selector):
    await page.wait_for_load_state('networkidle')
    for frame in page.frames:
        if frame.name == "mainFrame":
            try:
                await frame.locator(selector).first.wait_for(state="attached", timeout=5000)
            except Exception:
                pass
            return frame
    return page.frames[-1]

async def router_login(page):
    yield "Navigating to router login page...\n"
    await page.goto(os.environ.get("ROUTER_IP"))
    
    yield "Entering credentials...\n"
    inputs = await page.locator("input").all()
    for input_field in inputs:
        if not await input_field.is_visible(): continue
        input_type = await input_field.get_attribute("type")
        input_id = (await input_field.get_attribute("id") or "").lower()
        input_name = (await input_field.get_attribute("name") or "").lower()
        if input_type == 'text':
            await input_field.fill(os.environ.get("ROUTER_USER"))
        elif input_type == 'password':
            await input_field.fill(os.environ.get("ROUTER_PASS"))

    yield "Bypassing the login hurdle...\n"
    buttons = page.locator("button, input[type='button'], input[type='submit'], a")
    for i in range(await buttons.count()):
        btn = buttons.nth(i)
        if await btn.is_visible():
            text = (await btn.text_content() or await btn.get_attribute("value") or "").lower()
            if "log" in text or "sign" in text or "submit" in text:
                await btn.click()
                break
    yield "Logged in successfully! We're in.\n"

async def navigate_to_menu(page, main_menu, sub_menu):
    yield f"Opening the '{main_menu}' menu...\n"
    await click_in_any_frame(page, main_menu)
    
    yield f"Navigating into the '{sub_menu}' thingie...\n"
    await click_in_any_frame(page, sub_menu)

async def reboot_generator():
    yield "Waiting for global router lock...\n"
    async with router_lock:
        yield "Working on it... Launching headless browser...\n"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(ignore_https_errors=True)
                    page = await context.new_page()
                    
                    async for msg in router_login(page): yield msg
                    async for msg in navigate_to_menu(page, "Maintenance", "Reboot"): yield msg
                    
                    yield "Clicking the final Reboot button...\n"
                    main_frame = await wait_for_selector_in_mainframe(page, "#do_reboot")
                    
                    page.on("dialog", lambda dialog: dialog.accept())
                    await main_frame.locator("#do_reboot").click()
                    
                    yield "Done! Router is rebooting.\n"
                finally:
                    await browser.close()
        except Exception as e:
            yield f"Error occurred: {str(e)}\n"

async def portforward_generator(req: PortForwardRequest):
    yield "Waiting for global router lock...\n"
    async with router_lock:
        yield "Working on it... Launching headless browser...\n"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(ignore_https_errors=True)
                    page = await context.new_page()
                    
                    async for msg in router_login(page): yield msg
                    async for msg in navigate_to_menu(page, "Application", "Port Forwarding"): yield msg
                    
                    yield f"Filling out the form to open port {req.external_port}...\n"
                    main_frame = await wait_for_selector_in_mainframe(page, "input[name='etPortStart']")
                    
                    await main_frame.locator("input[name='etPortStart']").fill(str(req.external_port))
                    await main_frame.locator("input[name='etPortEnd']").fill(str(req.external_port))
                    await main_frame.locator("input[name='inPortStart']").fill(str(req.internal_port))
                    await main_frame.locator("input[name='inPortEnd']").fill(str(req.internal_port))
                    await main_frame.locator("input[name='serverIp']").fill(req.server_ip)
                    await main_frame.locator("select[name='proto']").select_option(req.protocol)
                    
                    checkbox = main_frame.locator("input[name='en_map']")
                    if not await checkbox.is_checked():
                        await checkbox.check()
                        
                    yield "Submitting the form...\n"
                    await main_frame.locator("input[id='do_add']").click()
                    
                    yield f"Done! Port {req.external_port} is now open and forwarded to {req.server_ip}.\n"
                finally:
                    await browser.close()
        except Exception as e:
            yield f"Error occurred: {str(e)}\n"

@app.post("/reboot")
async def reboot_router():
    return StreamingResponse(reboot_generator(), media_type="text/plain")

@app.post("/portforward")
async def add_port_forward(req: PortForwardRequest):
    return StreamingResponse(portforward_generator(req), media_type="text/plain")

async def forceset_generator(req: ForceSetRequest):
    yield "Waiting for global router lock...\n"
    async with router_lock:
        yield f"Working on it... Launching headless browser to force set {req.main_menu} -> {req.sub_menu}...\n"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(ignore_https_errors=True)
                    page = await context.new_page()
                    
                    async for msg in router_login(page): yield msg
                    async for msg in navigate_to_menu(page, req.main_menu, req.sub_menu): yield msg
                    
                    yield "Unlocking all UI elements (bypassing disabled and hidden flags)...\n"
                    main_frame = await wait_for_selector_in_mainframe(page, "body")
                    await page.wait_for_load_state('networkidle')
                    
                    await main_frame.evaluate("document.querySelectorAll(':disabled').forEach(el => el.removeAttribute('disabled'));")
                    await main_frame.evaluate("document.querySelectorAll('.hidden, [style*=\"display: none\"]').forEach(el => el.style.display = 'block');")
                    
                    yield "Applying new settings...\n"
                    for element_id, val in req.settings.items():
                        element = main_frame.locator(f"[name='{element_id}'], [id='{element_id}']").first
                        
                        # Strip restrictions right before interaction!
                        await element.evaluate("el => el.removeAttribute('disabled')")
                        await element.evaluate("el => el.removeAttribute('readonly')")
                        
                        tag = await element.evaluate("el => el.tagName.toLowerCase()")
                        inp_type = (await element.get_attribute("type") or "").lower()
                        
                        if tag == "select":
                            await element.select_option(str(val), force=True)
                        elif tag == "input" and inp_type in ["checkbox", "radio"]:
                            if str(val).lower() in ["true", "1", "on"]:
                                await element.check(force=True)
                            else:
                                await element.uncheck(force=True)
                        else:
                            await element.fill(str(val), force=True)
                        yield f" -> Set {element_id} to {val}\n"
                        
                    yield f"Clicking submit button '{req.submit_button}'...\n"
                    page.on("dialog", lambda dialog: dialog.accept())
                    submit_btn = main_frame.locator(f"[name='{req.submit_button}'], [id='{req.submit_button}']").first
                    await submit_btn.click(force=True)
                    
                    await page.wait_for_load_state('networkidle')
                    yield "Done! God-mode bypass complete.\n"
                finally:
                    await browser.close()
        except Exception as e:
            yield f"Error occurred: {str(e)}\n"

@app.post("/forceset")
async def force_set(req: ForceSetRequest):
    return StreamingResponse(forceset_generator(req), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
