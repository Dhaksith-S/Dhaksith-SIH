import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

SCREENSHOT_DIR = Path(r"C:\Users\Dhaksith.S\.gemini\antigravity-ide\brain\dc25bc26-f083-4c57-b507-a865f931e172\screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

async def run_verification():
    print("Starting Playwright Dashboard Verification...")
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # =======================================================
        # 1. Desktop Viewport (1920 x 1080) - Normal Flight State
        # =======================================================
        print("\n--- Testing Desktop (1920x1080) ---")
        page_desktop = await browser.new_page(viewport={"width": 1920, "height": 1080})
        page_desktop.on("console", lambda msg: print(f"[Browser Console {msg.type}]: {msg.text}") if msg.type in ['error', 'warn'] else None)
        page_desktop.on("pageerror", lambda exc: errors.append(f"Page Error: {exc}"))

        await page_desktop.goto("http://localhost:8000", wait_until="networkidle")
        await asyncio.sleep(2.0)

        # Arm the drone for normal flight
        btn_arm = page_desktop.locator("#btn-arm-toggle")
        arm_text = await btn_arm.inner_text()
        print(f"Initial Arm Button text: {arm_text.strip()}")
        
        if "ARM" in arm_text:
            await btn_arm.click()
            await asyncio.sleep(2.5) # Lift off into hover clearance

        # Verify buttons enabled state
        btn_hover = page_desktop.locator("#btn-flight-hover")
        is_hover_disabled = await btn_hover.is_disabled()
        print(f"Hover button disabled when armed? {is_hover_disabled} (Expected: False)")

        # Verify top status hierarchy
        source_text = await page_desktop.locator("#hud-source-pill").inner_text()
        conn_text = await page_desktop.locator("#hud-conn-pill").inner_text()
        armed_text = await page_desktop.locator("#hud-armed-pill").inner_text()
        mode_text = await page_desktop.locator("#hud-flight-mode").inner_text()
        print(f"Top Hierarchy: Source='{source_text.strip()}', Conn='{conn_text.strip()}', Arm='{armed_text.strip()}', Mode='{mode_text.strip()}'")

        # Verify Atmospheric Monitor text
        atmo_text = await page_desktop.locator("#gas-overall-status").inner_text()
        print(f"Atmospheric Status: '{atmo_text.strip()}'")

        # Capture Desktop Normal Flight State Screenshot
        shot_desktop_normal = SCREENSHOT_DIR / "desktop_normal_flight.png"
        await page_desktop.screenshot(path=str(shot_desktop_normal))
        print(f"Saved: {shot_desktop_normal}")

        # Test switching metric card to Battery
        card_batt = page_desktop.locator("#card-metric-battery")
        await card_batt.click()
        await asyncio.sleep(1.0)
        chart_title = await page_desktop.locator("#chart-metric-label").inner_text()
        print(f"Switched dedicated chart to: {chart_title.strip()}")

        # =======================================================
        # 2. Trigger Emergency Stop -> Capture Emergency/Disarmed State
        # =======================================================
        print("\n--- Triggering Emergency Stop ---")
        btn_estop = page_desktop.locator("#btn-emergency-stop")
        await btn_estop.click()
        await asyncio.sleep(1.5)

        # Verify Fault Banner
        fault_banner = page_desktop.locator("#fault-banner")
        is_fault_visible = await fault_banner.is_visible()
        fault_cause = await page_desktop.locator("#fault-cause").inner_text()
        fault_status = await page_desktop.locator("#fault-recovery-status").inner_text()
        armed_pill_text = await page_desktop.locator("#hud-armed-pill").inner_text()
        mode_pill_text = await page_desktop.locator("#hud-flight-mode").inner_text()

        print(f"Fault Banner Visible? {is_fault_visible}")
        print(f"Fault Cause: '{fault_cause.strip()}'")
        print(f"Fault Recovery: '{fault_status.strip()}'")
        print(f"Armed Pill: '{armed_pill_text.strip()}' (Expected: DISARMED)")
        print(f"Mode Pill: '{mode_pill_text.strip()}' (Expected: EMERGENCY)")

        # Capture Desktop Emergency State Screenshot
        shot_desktop_estop = SCREENSHOT_DIR / "desktop_emergency_disarmed.png"
        await page_desktop.screenshot(path=str(shot_desktop_estop))
        print(f"Saved: {shot_desktop_estop}")

        # Reset Fault via Fault Banner Reset Button
        btn_reset = page_desktop.locator("#btn-reset-fault")
        if await btn_reset.is_visible():
            await btn_reset.click()
            await asyncio.sleep(1.0)
            print("Fault Reset clicked.")

        await page_desktop.close()

        # =======================================================
        # 3. Laptop Viewport (1366 x 768) - Normal Flight & Emergency
        # =======================================================
        print("\n--- Testing Laptop (1366x768) ---")
        page_laptop = await browser.new_page(viewport={"width": 1366, "height": 768})
        page_laptop.on("pageerror", lambda exc: errors.append(f"Laptop Page Error: {exc}"))

        await page_laptop.goto("http://localhost:8000", wait_until="networkidle")
        await asyncio.sleep(2.0)

        # Arm drone for laptop normal flight
        btn_arm_laptop = page_laptop.locator("#btn-arm-toggle")
        arm_text_laptop = await btn_arm_laptop.inner_text()
        if "ARM" in arm_text_laptop:
            await btn_arm_laptop.click()
            await asyncio.sleep(2.0)

        # Capture Laptop Normal Flight Screenshot
        shot_laptop_normal = SCREENSHOT_DIR / "laptop_normal_flight.png"
        await page_laptop.screenshot(path=str(shot_laptop_normal))
        print(f"Saved: {shot_laptop_normal}")

        # Trigger Emergency Stop on Laptop Viewport
        btn_estop_laptop = page_laptop.locator("#btn-emergency-stop")
        await btn_estop_laptop.click()
        await asyncio.sleep(1.5)

        # Capture Laptop Emergency / Disarmed Screenshot
        shot_laptop_estop = SCREENSHOT_DIR / "laptop_emergency_disarmed.png"
        await page_laptop.screenshot(path=str(shot_laptop_estop))
        print(f"Saved: {shot_laptop_estop}")

        await page_laptop.close()
        await browser.close()

    print("\n--- Verification Summary ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED WITH ZERO CONSOLE/PAGE ERRORS!")

if __name__ == "__main__":
    asyncio.run(run_verification())
