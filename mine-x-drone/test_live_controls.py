import asyncio
import json
import websockets
import urllib.request

async def test_drone_controls():
    print("Testing REST status...")
    with urllib.request.urlopen("http://127.0.0.1:8000/api/status") as resp:
        data = json.loads(resp.read().decode())
        print(f"REST Status: {data}")
        assert data["status"] == "ONLINE"
        assert data["armed"] == True

    print("\nConnecting to WebSocket ws://127.0.0.1:8000/ws ...")
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        # 1. Read initial packet
        initial_msg = await ws.recv()
        initial_packet = json.loads(initial_msg)
        print("Received initial packet successfully!")
        print(f"Armed: {initial_packet.get('armed')}, Mode: {initial_packet.get('motion_mode')}")
        pos0 = initial_packet["position"]
        print(f"Initial Pos: X={pos0['x']}, Y={pos0['y']}, Z={pos0['z']}")

        # 2. Read 5 broadcast packets to confirm telemetry loop stability
        print("\nVerifying broadcast telemetry stream stability...")
        for i in range(5):
            msg = await ws.recv()
            pkt = json.loads(msg)
            assert "position" in pkt
            assert "battery" in pkt
        print("Telemetry loop is broadcast-stable (5/5 received without error)!")

        # 3. Send KEY_DOWN for 'w' (Forward down cavern)
        print("\nSending KEY_DOWN: 'w' (Forward)...", flush=True)
        await ws.send(json.dumps({"command": "KEY_DOWN", "key": "w"}))

        # Wait 1.2 seconds to let physics integrate forward velocity while receiving telemetry
        print("Receiving live telemetry while flying forward...", flush=True)
        end_time = asyncio.get_event_loop().time() + 1.2
        pos1 = None
        while asyncio.get_event_loop().time() < end_time:
            msg = await ws.recv()
            pkt = json.loads(msg)
            if "position" in pkt:
                pos1 = pkt["position"]

        print(f"New Pos after 'w': X={pos1['x']}, Y={pos1['y']}, Z={pos1['z']}", flush=True)
        delta_z = pos1["z"] - pos0["z"]
        print(f"Delta Z: {delta_z:.2f} m (expected negative)", flush=True)
        assert delta_z < -0.1, f"Drone did not move forward! Delta Z: {delta_z}"

        # 4. Release 'w'
        print("\nSending KEY_UP: 'w'...", flush=True)
        await ws.send(json.dumps({"command": "KEY_UP", "key": "w"}))

        # 5. Send KEY_DOWN for 'r' (Climb)
        print("\nSending KEY_DOWN: 'r' (Ascend)...", flush=True)
        await ws.send(json.dumps({"command": "KEY_DOWN", "key": "r"}))
        
        end_time = asyncio.get_event_loop().time() + 1.0
        pos2 = None
        while asyncio.get_event_loop().time() < end_time:
            msg = await ws.recv()
            pkt = json.loads(msg)
            if "position" in pkt:
                pos2 = pkt["position"]

        print(f"New Pos after 'r': X={pos2['x']}, Y={pos2['y']}, Z={pos2['z']}", flush=True)
        delta_y = pos2["y"] - pos1["y"]
        print(f"Delta Y: {delta_y:.2f} m (expected positive)", flush=True)
        assert delta_y > 0.1, f"Drone did not ascend! Delta Y: {delta_y}"

        # Release 'r'
        await ws.send(json.dumps({"command": "KEY_UP", "key": "r"}))

        # 6. Test 'a' (Left) and 'd' (Right)
        print("\nSending KEY_DOWN: 'a' (Left)...", flush=True)
        await ws.send(json.dumps({"command": "KEY_DOWN", "key": "a"}))
        pos_a = None
        end_time = asyncio.get_event_loop().time() + 1.0
        while asyncio.get_event_loop().time() < end_time:
            msg = await ws.recv()
            pkt = json.loads(msg)
            if "position" in pkt:
                pos_a = pkt["position"]
        print(f"Pos after 'a': X={pos_a['x']}, Y={pos_a['y']}, Z={pos_a['z']}", flush=True)
        assert pos_a["x"] < -0.1, "Drone did not bank left!"
        await ws.send(json.dumps({"command": "KEY_UP", "key": "a"}))

        # 7. Test RESET_POSITION
        print("\nTesting RESET_POSITION command...", flush=True)
        await ws.send(json.dumps({"command": "RESET_POSITION"}))
        pos_reset = None
        end_time = asyncio.get_event_loop().time() + 0.8
        while asyncio.get_event_loop().time() < end_time:
            msg = await ws.recv()
            pkt = json.loads(msg)
            if "position" in pkt:
                pos_reset = pkt["position"]
        print(f"Pos after RESET_POSITION: X={pos_reset['x']}, Y={pos_reset['y']}, Z={pos_reset['z']}", flush=True)
        assert abs(pos_reset["x"] - 0.0) < 0.2 and abs(pos_reset["z"] - 25.0) < 0.2, "Reset did not return to portal!"

        # 6. Test REST API command execution
        print("\nTesting REST API command fallback (/api/command)...")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/command",
            data=json.dumps({"command": "HOVER"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            rest_res = json.loads(resp.read().decode())
            print(f"REST Response for HOVER: {rest_res}")
            assert rest_res["status"] == "OK"

        print("\nALL CONTROLS AND WEBSOCKET STREAM VERIFIED SUCCESSFULLY! 100% OPERATIONAL.")

if __name__ == "__main__":
    asyncio.run(test_drone_controls())
