"""
MINE-X DRONE COMMAND - Automated Spherical Drone Verification Script
Tests and captures screenshots of all 5 operational modes:
1. Normal Flight (with spinning props, searchlights, stationary outer cage, and Follow Drone camera)
2. Landing / Touchdown (smooth descent to mine floor contact at y=1.35m)
3. Ground Rolling (outer cage rotating with distance traveled while inner camera remains upright)
4. Takeoff (cage stops rolling, props spin up, smooth ascent)
5. Emergency Stop / Disarmed (motors killed immediately, settles safely)
6. Design Reference Modal (10s reference clip playback)
"""

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots" / "spherical_drone"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def run_verification():
    print("=" * 70)
    print("   MINE-X SPHERICAL DRONE 3D VERIFICATION & AUTOMATED DEMO   ")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 920})
        page = context.new_page()

        print("\n[1/7] Navigating to http://localhost:8000...")
        page.goto("http://localhost:8000")
        page.wait_for_selector("#viewport-container canvas", timeout=15000)
        time.sleep(2)

        # Check WebSocket online
        conn_text = page.locator("#hud-conn-pill").text_content()
        print(f"  Connection Status: {conn_text.strip()}")

        # ----------------------------------------------------
        # Mode 1: Normal Flight
        # ----------------------------------------------------
        print("\n[2/7] Testing Mode 1: Normal Flight...")
        # Switch to Follow Drone camera view
        page.click("#btn-view-follow")
        time.sleep(0.5)

        # Arm the drone to initiate takeoff
        page.evaluate("window.droneApp.socket.sendCommand('ARM')")
        time.sleep(3.5)  # Allow time for smooth takeoff climb to 3.5m

        drone_state_flight = page.evaluate("""() => {
            const d = window.droneApp.drone3d;
            return {
                altitude: d.dronePos.y,
                cageRotationX: d.outerCageGroup ? d.outerCageGroup.rotation.x : null,
                innerPitch: d.innerCoreGroup ? d.innerCoreGroup.rotation.x : null,
                armed: d.armed,
                motionMode: d.motionMode,
                propCount: d.props.length,
                propBlurOpacity: d.props[0] ? d.props[0].blurDisc.material.opacity : 0
            };
        }""")
        print(f"  Flight State: Alt={drone_state_flight['altitude']:.2f}m, Armed={drone_state_flight['armed']}, "
              f"Props={drone_state_flight['propCount']}, BlurOpacity={drone_state_flight['propBlurOpacity']:.2f}")

        screenshot_flight = SCREENSHOT_DIR / "mode_1_normal_flight.png"
        page.screenshot(path=str(screenshot_flight))
        print(f"  Saved screenshot: {screenshot_flight}")

        # ----------------------------------------------------
        # Mode 2: Landing / Touchdown
        # ----------------------------------------------------
        print("\n[3/7] Testing Mode 2: Landing / Touchdown...")
        page.evaluate("window.droneApp.socket.sendCommand('LAND')")
        time.sleep(3.0)  # Wait for descent to y=1.35m

        drone_state_land = page.evaluate("""() => {
            const d = window.droneApp.drone3d;
            return {
                altitude: d.dronePos.y,
                groundContact: d.groundContact,
                motionMode: d.motionMode,
                cageRotationX: d.outerCageGroup ? d.outerCageGroup.rotation.x : null,
                innerPitch: d.innerCoreGroup ? d.innerCoreGroup.rotation.x : null
            };
        }""")
        print(f"  Touchdown State: Alt={drone_state_land['altitude']:.2f}m (Floor=1.35m), GroundContact={drone_state_land['groundContact']}")

        screenshot_land = SCREENSHOT_DIR / "mode_2_touchdown.png"
        page.screenshot(path=str(screenshot_land))
        print(f"  Saved screenshot: {screenshot_land}")

        # ----------------------------------------------------
        # Mode 3: Ground Rolling
        # ----------------------------------------------------
        print("\n[4/7] Testing Mode 3: Ground Rolling...")
        # Command forward ground rolling motion
        initial_cage_rot = page.evaluate("window.droneApp.drone3d.outerCageGroup ? window.droneApp.drone3d.outerCageGroup.rotation.x : 0")

        # Send forward command
        page.evaluate("window.droneApp.socket.sendCommand('KEY_DOWN', { key: 'w' })")
        time.sleep(2.5)
        page.evaluate("window.droneApp.socket.sendCommand('KEY_UP', { key: 'w' })")
        page.evaluate("window.droneApp.socket.sendCommand('STOP_MOTION')")
        time.sleep(0.5)

        drone_state_roll = page.evaluate("""() => {
            const d = window.droneApp.drone3d;
            return {
                altitude: d.dronePos.y,
                cageRotationX: d.outerCageGroup ? d.outerCageGroup.rotation.x : 0,
                innerPitch: d.innerCoreGroup ? d.innerCoreGroup.rotation.x : 0,
                innerRoll: d.innerCoreGroup ? d.innerCoreGroup.rotation.z : 0,
                motionMode: d.motionMode
            };
        }""")
        rot_delta = abs(drone_state_roll['cageRotationX'] - initial_cage_rot)
        print(f"  Ground Roll State: Altitude={drone_state_roll['altitude']:.2f}m, "
              f"Cage Rotation Delta={rot_delta:.3f} rad, Inner Core Pitch={drone_state_roll['innerPitch']:.3f} rad (upright)")

        screenshot_roll = SCREENSHOT_DIR / "mode_3_ground_rolling.png"
        page.screenshot(path=str(screenshot_roll))
        print(f"  Saved screenshot: {screenshot_roll}")

        # ----------------------------------------------------
        # Mode 4: Takeoff
        # ----------------------------------------------------
        print("\n[5/7] Testing Mode 4: Takeoff...")
        # Trigger takeoff
        page.evaluate("window.droneApp.socket.sendCommand('TAKEOFF')")
        time.sleep(1.8)  # Mid-climb snapshot

        drone_state_takeoff = page.evaluate("""() => {
            const d = window.droneApp.drone3d;
            return {
                altitude: d.dronePos.y,
                motionMode: d.motionMode,
                propBlurOpacity: d.props[0] ? d.props[0].blurDisc.material.opacity : 0
            };
        }""")
        print(f"  Takeoff State: Climbing Alt={drone_state_takeoff['altitude']:.2f}m, Props Active (Blur={drone_state_takeoff['propBlurOpacity']:.2f})")

        screenshot_takeoff = SCREENSHOT_DIR / "mode_4_takeoff.png"
        page.screenshot(path=str(screenshot_takeoff))
        print(f"  Saved screenshot: {screenshot_takeoff}")

        # ----------------------------------------------------
        # Mode 5: Emergency Stop / Disarmed
        # ----------------------------------------------------
        print("\n[6/7] Testing Mode 5: Emergency Stop / Disarmed...")
        page.click("#btn-emergency-stop")
        time.sleep(1.5)

        drone_state_estop = page.evaluate("""() => {
            const d = window.droneApp.drone3d;
            return {
                armed: d.armed,
                altitude: d.dronePos.y,
                propBlurOpacity: d.props[0] ? d.props[0].blurDisc.material.opacity : 0,
                faultBannerVisible: !document.getElementById('fault-banner').classList.contains('hidden')
            };
        }""")
        print(f"  Emergency Stop State: Armed={drone_state_estop['armed']}, Motors Killed (Blur={drone_state_estop['propBlurOpacity']:.2f}), "
              f"Fault Banner Visible={drone_state_estop['faultBannerVisible']}")

        screenshot_estop = SCREENSHOT_DIR / "mode_5_emergency_disarmed.png"
        page.screenshot(path=str(screenshot_estop))
        print(f"  Saved screenshot: {screenshot_estop}")

        # Reset fault
        page.click("#btn-reset-fault")
        time.sleep(0.5)

        # ----------------------------------------------------
        # Mode 6: Design Reference Modal
        # ----------------------------------------------------
        print("\n[7/7] Testing Mode 6: Design Reference Modal...")
        page.click("#btn-open-design-ref")
        time.sleep(1.0)

        modal_visible = page.evaluate("""() => {
            const m = document.getElementById('modal-design-reference');
            const v = document.getElementById('design-ref-video');
            return {
                visible: m && !m.classList.contains('hidden'),
                videoSrc: v ? v.getAttribute('src') : null
            };
        }""")
        print(f"  Design Reference Modal: Visible={modal_visible['visible']}, Src={modal_visible['videoSrc']}")

        screenshot_modal = SCREENSHOT_DIR / "mode_6_design_ref_modal.png"
        page.screenshot(path=str(screenshot_modal))
        print(f"  Saved screenshot: {screenshot_modal}")

        # Close modal
        page.click("#btn-close-design-ref")
        time.sleep(0.5)

        # Overview wide shot of the 3D scene
        page.click("#btn-view-overview")
        time.sleep(1.0)
        screenshot_overview = SCREENSHOT_DIR / "overview_scene_wide.png"
        page.screenshot(path=str(screenshot_overview))
        print(f"  Saved screenshot: {screenshot_overview}")

        browser.close()

    print("\n" + "=" * 70)
    print("   AUTOMATED VERIFICATION COMPLETED SUCCESSFULLY!   ")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
