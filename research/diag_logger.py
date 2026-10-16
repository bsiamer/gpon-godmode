import asyncio
import os
import sys
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from api import router_login

# Load environment variables
load_dotenv()

async def run_diagnostics_logging(input_data: str):
    """
    Logs into the Nokia GPON gateway, navigates to the ping diagnostics page,
    sets up a network listener for command.cgi response bodies, and triggers a ping.
    """
    print(f"Starting network response logger for input: '{input_data}'")
    
    async with async_playwright() as p:
        # Launch headless browser (matching setup in api.py)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        
        try:
            # 1. Login using router_login helper from api.py
            async for msg in router_login(page):
                print(f"[Login] {msg.strip()}")
            
            # Wait to check if login succeeded or if we got locked out / failed
            print("Verifying login status...")
            try:
                # Wait until username input disappears OR an error/lockout message appears on the page
                await page.wait_for_function(
                    "() => !document.querySelector('#username') && !document.querySelector('input[name=\"name\"]') || "
                    "document.body.innerText.toLowerCase().includes('error happen') || "
                    "document.body.innerText.toLowerCase().includes('retry later') || "
                    "document.body.innerText.toLowerCase().includes('incorrect') || "
                    "document.body.innerText.toLowerCase().includes('fail')",
                    timeout=15000
                )
            except Exception as e:
                print(f"Warning: Login status check timed out: {e}")
            
            # Read page content to determine results
            body_text = (await page.locator("body").inner_text()).lower()
            if "error happen" in body_text or "retry later" in body_text:
                raise RuntimeError(
                    "Login Failed: The Nokia GPON gateway has locked login attempts due to too many failures.\n"
                    "Please wait a few minutes for the lockout to clear and verify your ROUTER_USER/ROUTER_PASS in .env."
                )
            elif "incorrect" in body_text or "fail" in body_text:
                raise RuntimeError(
                    "Login Failed: Incorrect username or password.\n"
                    "Please check your ROUTER_USER and ROUTER_PASS in the .env file."
                )
            
            # Check if username field is still visible
            username_visible = False
            for selector in ["#username", "input[name='name']"]:
                try:
                    if await page.locator(selector).is_visible():
                        username_visible = True
                        break
                except Exception:
                    pass
                    
            if username_visible:
                raise RuntimeError(
                    "Login Failed: The login form is still visible. Credentials might be incorrect or the page is unresponsive."
                )
                
            print("Logged in successfully! Session established.")
            
            # 2. Navigate to diagnostics page
            router_ip = os.environ.get("ROUTER_IP", "http://192.168.1.254").rstrip('/')
            diag_url = f"{router_ip}/diag.cgi?ping"
            print(f"Navigating to diagnostics page: {diag_url}")
            await page.goto(diag_url)
            await page.wait_for_load_state("networkidle")
            
            # 3. Setup Network Interceptor
            async def handle_response(response):
                if "command.cgi" in response.url:
                    print(f"Intercepted response from: {response.url}")
                    try:
                        text = await response.text()
                        # Append the raw text response to the log file
                        with open("network_debug_log.txt", "a", encoding="utf-8") as f:
                            f.write(f"--- Response from {response.url} ---\n")
                            f.write(text)
                            f.write("\n\n")
                        print("Saved response body to network_debug_log.txt")
                    except Exception as e:
                        print(f"Failed to read/save response body: {e}")

            page.on("response", handle_response)
            
            # 4. Form Interaction
            # Wait dynamically for the target selector to appear in either the main page or one of the frames
            target_selector = "input[name='ipaddr']"
            target_frame = None
            
            print("Locating form fields (scanning frames)...")
            for attempt in range(20):  # Check every 500ms for up to 10 seconds
                # Try the main page
                try:
                    if await page.locator(target_selector).count() > 0:
                        target_frame = page
                        break
                except Exception:
                    pass
                
                # Try all active frames
                for frame in page.frames:
                    try:
                        if await frame.locator(target_selector).count() > 0:
                            target_frame = frame
                            break
                    except Exception:
                        pass
                
                if target_frame:
                    break
                await asyncio.sleep(0.5)
                
            if not target_frame:
                raise RuntimeError(
                    "Timeout: Diagnostics input field ('input[name=\"ipaddr\"]') not found on the page or inside frames.\n"
                    "Make sure you have access rights and the diagnostics menu exists."
                )
            
            frame_name = getattr(target_frame, "name", "") or "unnamed frame"
            if target_frame == page:
                frame_name = "main page"
            print(f"Target input found in: {frame_name}")
            
            # Redefine the validation functions to return true, bypassing frontend formatting checks
            print("Bypassing frontend input validation rules...")
            try:
                await target_frame.evaluate("""
                    window.isValidIpAddress = function() { return true; };
                    window.checkDomain = function() { return true; };
                    if (typeof isValidIpAddress !== 'undefined') { isValidIpAddress = function() { return true; }; }
                    if (typeof checkDomain !== 'undefined') { checkDomain = function() { return true; }; }
                """)
                print("Frontend validation bypassed successfully.")
            except Exception as e:
                print(f"Warning: Could not redefine validation functions: {e}")

            # Fill the ipaddr input field
            ip_field = target_frame.locator(target_selector).first
            await ip_field.wait_for(state="attached", timeout=5000)
            await ip_field.fill(input_data)
            
            # Check the #ch_ping checkbox
            checkbox = target_frame.locator("#ch_ping").first
            await checkbox.wait_for(state="attached", timeout=5000)
            if not await checkbox.is_checked():
                await checkbox.check()
                
            # Click the #pingstart button
            start_btn = target_frame.locator("#pingstart").first
            await start_btn.wait_for(state="attached", timeout=5000)
            await start_btn.click()
            print("Diagnostics form submitted (ping started).")
            
            # 5. Wait to ensure background AJAX requests complete
            print("Waiting 10 seconds for response capture...")
            await asyncio.sleep(10)
            
        finally:
            await browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_input = sys.argv[1]
    else:
        test_input = "127.0.0.1"
        print(f"No input argument provided. Defaulting to: {test_input}")

    import ipaddress
    
    def is_safe_input(v: str) -> bool:
        # Check if valid IP address
        try:
            ipaddress.ip_address(v)
            return True
        except ValueError:
            pass
        # Check if valid domain name
        domain_regex = re.compile(
            r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])'
            r'(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$'
        )
        return bool(domain_regex.match(v))

    if not is_safe_input(test_input):
        print(f"\n❌ Error: Invalid input '{test_input}'. Must be a valid IP address or domain name to prevent injection attacks.", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(run_diagnostics_logging(test_input))
    except RuntimeError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
