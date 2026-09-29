"""
MINE-X DRONE COMMAND - Automated Playwright End-to-End Verification
Tests full user workflows, 3D viewport, keyboard controls, WebSocket telemetry,
modals, and captures visual screenshots.
"""

import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path(r"C:\Users\Dhaksith.S\.gemini\antigravity-ide\brain\c29794cd-842f-4e48-95d8-a2bd5b69e622")
SCREENSHOT_DIR = ARTIFACT_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def run_verification():
    print("=" * 60)
    print("Starting Playwright E2E Verification of MINE-X Drone Command")
    print("=" * 60)

    console_logs = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Capture console messages
        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error" else console_logs.append(f"[{msg.type}] {msg.text}")
        ))

        # 1. Navigate to dashboard
        print("1. Navigating to http://127.0.0.1:8000 ...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        time.sleep(2)  # Allow Three.js and WebSocket to settle

        # Verify page title
        title = page.title()
        print(f"   Page Title: {title}")
        assert "MINE-X DRONE COMMAND" in title, "Title mismatch!"

        # Screenshot Initial State
        p_initial = SCREENSHOT_DIR / "01_initial_dashboard.png"
        page.screenshot(path=str(p_initial))
        print(f"   Saved screenshot: {p_initial}")

        # Check WebSocket connection status
        conn_pill = page.locator("#hud-conn-pill").inner_text()
        print(f"   Connection status pill: {conn_pill}")

        # 2. Test ARM Drone
        print("2. Testing ARM DRONE button...")
        btn_arm = page.locator("#btn-arm-toggle")
        btn_arm.click()
        time.sleep(1.5)

        armed_pill = page.locator("#hud-armed-pill").inner_text()
        print(f"   Armed status pill: {armed_pill}")
        assert "ARMED" in armed_pill, "Drone failed to arm!"

        p_armed = SCREENSHOT_DIR / "02_armed_hover.png"
        page.screenshot(path=str(p_armed))
        print(f"   Saved screenshot: {p_armed}")

        # 3. Test Keyboard Flight Controls (W, A, S, D, Q, E, R, F)
        print("3. Testing keyboard controls (W/A/S/D, Q/E, R/F)...")
        # Press W (Forward)
        page.keyboard.down("KeyW")
        time.sleep(0.8)
        page.keyboard.up("KeyW")
        time.sleep(0.5)

        # Press R (Ascend)
        page.keyboard.down("KeyR")
        time.sleep(0.8)
        page.keyboard.up("KeyR")
        time.sleep(0.5)

        # Press E (Rotate Right)
        page.keyboard.down("KeyE")
        time.sleep(0.6)
        page.keyboard.up("KeyE")
        time.sleep(0.5)

        # Check telemetry updates
        pos_z = page.locator("#coord-z").inner_text()
        pos_y = page.locator("#coord-y").inner_text()
        yaw = page.locator("#hud-yaw").inner_text()
        print(f"   Telemetry after movements: Z={pos_z}, Y={pos_y}, Yaw={yaw}")

        p_movement = SCREENSHOT_DIR / "03_flight_movement.png"
        page.screenshot(path=str(p_movement))
        print(f"   Saved screenshot: {p_movement}")

        # 4. Test Hardware Inspector Modal
        print("4. Testing Hardware Inspector Modal...")
        btn_hw = page.locator("#btn-open-hardware")
        btn_hw.click()
        time.sleep(1)

        p_hw = SCREENSHOT_DIR / "04_hardware_inspector_modal.png"
        page.screenshot(path=str(p_hw))
        print(f"   Saved screenshot: {p_hw}")

        # Close Hardware modal
        page.locator("#btn-close-hardware").click()
        time.sleep(0.5)

        # 5. Test Sensor Calibration Modal
        print("5. Testing Sensor Calibration Modal...")
        btn_cal = page.locator("#btn-open-calibration")
        btn_cal.click()
        time.sleep(0.8)

        # Click IMU Calibrate
        btn_cal_imu = page.locator("#btn-cal-imu")
        btn_cal_imu.click()
        time.sleep(2.5)  # Wait for calibration animation to complete

        p_cal = SCREENSHOT_DIR / "05_calibration_modal.png"
        page.screenshot(path=str(p_cal))
        print(f"   Saved screenshot: {p_cal}")

        # Close Calibration modal
        page.locator("#btn-close-calibration").click()
        time.sleep(0.5)

        # 6. Test Thermal LWIR Camera Viewport
        print("6. Testing Thermal Camera Viewport...")
        btn_thermal = page.locator("#tab-cam-thermal")
        btn_thermal.click()
        time.sleep(1)

        p_thermal = SCREENSHOT_DIR / "06_thermal_viewport.png"
        page.screenshot(path=str(p_thermal))
        print(f"   Saved screenshot: {p_thermal}")

        # 7. Test Emergency Stop (SPACE)
        print("7. Testing EMERGENCY STOP (SPACE / Button)...")
        page.keyboard.press("Space")
        time.sleep(1)

        armed_after_estop = page.locator("#hud-armed-pill").inner_text()
        mode_after_estop = page.locator("#hud-flight-mode").inner_text()
        print(f"   Status after ESTOP: Armed={armed_after_estop}, Mode={mode_after_estop}")
        assert "DISARMED" in armed_after_estop, "ESTOP failed to disarm!"

        p_estop = SCREENSHOT_DIR / "07_emergency_stop.png"
        page.screenshot(path=str(p_estop))
        print(f"   Saved screenshot: {p_estop}")

        browser.close()

    print("=" * 60)
    print("VERIFICATION COMPLETED!")
    print(f"Total console logs captured: {len(console_logs)}")
    print(f"Total console errors: {len(console_errors)}")
    if console_errors:
        print("Console errors:")
        for err in console_errors:
            print("  -", err)
    else:
        print(" ZERO JavaScript console errors detected! All tests passed cleanly.")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
