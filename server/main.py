"""
main.py

Primary entry point for the Linux Remote Desktop prototype.
This server performs three core responsibilities:

1. Screen Capture: Periodically captures the current screen (entire virtual display) using `mss`.
2. Encoding & Streaming: Converts frames to JPEG (quality adjustable) and sends them over a WebSocket
   connection to connected clients as Base64 strings wrapped in JSON messages.
3. Remote Input Handling: Receives keyboard and mouse events from clients and replays them locally
   using `pyautogui` (simple cross-platform automation library).

Protocol (JSON over WebSocket):
--------------------------------
Outgoing (Server -> Client) frame message format:
{
  "type": "frame",
  "timestamp": 1730.123,        # Python time.time() value
  "encoding": "jpeg-base64",
  "width": 1920,
  "height": 1080,
  "quality": 60,
  "data": "<BASE64_JPEG_DATA>"
}

Incoming (Client -> Server) input events examples:
Mouse move:
{
  "type": "mouse",
  "action": "move",
  "x": 100,
  "y": 200
}
Mouse click:
{
  "type": "mouse",
  "action": "click",
  "button": "left"   # or "right", "middle"
}
Keyboard key press:
{
  "type": "keyboard",
  "action": "keydown",  # or "keyup" (pyautogui treats keyUp separately)
  "key": "a"            # Raw key string (future: mapping for special keys)
}

Security / Safety Notice:
-------------------------
This prototype does NOT implement authentication, encryption (TLS), access control, or rate limiting.
Running it on an untrusted network is unsafe. Use an SSH tunnel or reverse proxy with TLS if exposing
beyond localhost. Future enhancements should integrate proper auth (e.g., token-based) and input
sanitization, plus sandbox restrictions.

Performance Notes:
------------------
This very first version sends full JPEG frames. For higher performance / lower bandwidth you can:
- Switch to WebRTC for real-time transport (complex but powerful).
- Use delta encoding (send only changed regions).
- Adopt a video codec via `ffmpeg` or `gstreamer` piping (H.264 / VP9 / AV1).
- Lower `jpeg_quality` or apply `resize_scale` < 1.0 to shrink frames.

Future Roadmap Ideas:
---------------------
- Multi-monitor support (select which monitor).
- Clipboard synchronization.
- File transfer channel.
- Secure authentication and optional per-user permissions.
- WebRTC data channel for input + media channel for video.

All code here is heavily commented for public readability.
"""

import asyncio
import base64
import json
import time
from typing import Set

import mss  # Screen capture
from PIL import Image  # Image processing / JPEG encoding
import pyautogui  # Input automation
import websockets  # WebSocket server

from config import settings

# Maintain active connections in a set for broadcasting (if needed later)
ACTIVE_CONNECTIONS: Set[websockets.WebSocketServerProtocol] = set()


async def capture_and_send_frames(ws: websockets.WebSocketServerProtocol) -> None:
    """Continuously capture the screen and send frames until the connection closes.

    Frame regulation uses a simple sleep based on target FPS. A more precise
    scheduling (e.g., using asyncio loop timing deltas) could be implemented later.
    """
    target_interval = 1.0 / max(settings.target_fps, 1)
    with mss.mss() as sct:
        monitor = sct.monitors[0]  # Full virtual screen (includes all monitors merged).
        while True:
            start_time = time.time()
            try:
                raw = sct.grab(monitor)
            except Exception as e:
                # If capture fails, log and break to avoid busy loop.
                print(f"[WARN] Screen capture failed: {e}")
                break

            # Convert to PIL Image for resizing / encoding.
            img = Image.frombytes("RGB", raw.size, raw.rgb)

            if settings.resize_scale != 1.0:
                new_size = (
                    int(img.width * settings.resize_scale),
                    int(img.height * settings.resize_scale),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Encode to JPEG in-memory.
            from io import BytesIO
            buff = BytesIO()
            img.save(buff, format="JPEG", quality=settings.jpeg_quality)
            jpeg_bytes = buff.getvalue()
            encoded = base64.b64encode(jpeg_bytes).decode("ascii")

            frame_message = {
                "type": "frame",
                "timestamp": time.time(),
                "encoding": "jpeg-base64",
                "width": img.width,
                "height": img.height,
                "quality": settings.jpeg_quality,
                "data": encoded,
            }

            try:
                await ws.send(json.dumps(frame_message))
            except Exception as e:
                print(f"[INFO] Connection closed while sending frame: {e}")
                break

            # Compute how long to sleep to approximate target FPS.
            elapsed = time.time() - start_time
            sleep_for = target_interval - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                # If encoding took too long, we skip sleeping (frame rate drops automatically).
                await asyncio.sleep(0)


def _handle_mouse_event(payload: dict) -> None:
    """Interpret and execute a mouse event payload using pyautogui.

    Actions supported: move, click.
    Future expansions: drag, scroll, double-click.
    """
    action = payload.get("action")
    if action == "move":
        x = int(payload.get("x", 0))
        y = int(payload.get("y", 0))
        pyautogui.moveTo(x, y)
    elif action == "click":
        button = payload.get("button", "left")
        pyautogui.click(button=button)
    else:
        print(f"[WARN] Unknown mouse action: {action}")


def _handle_keyboard_event(payload: dict) -> None:
    """Interpret and execute a keyboard event payload.

    Actions: keydown, keyup.
    NOTE: pyautogui does not provide a distinct 'keydown' without 'keyup' for all keys;
    it issues a full press by default. For simplicity we map:
    - keydown => pyautogui.keyDown
    - keyup   => pyautogui.keyUp

    Some special keys need name mapping (e.g., 'Enter', 'Ctrl'). For now we assume
    raw key strings follow pyautogui's accepted naming.
    """
    action = payload.get("action")
    key = str(payload.get("key", ""))
    if not key:
        return
    if action == "keydown":
        try:
            pyautogui.keyDown(key)
        except Exception as e:
            print(f"[WARN] keyDown failed for '{key}': {e}")
    elif action == "keyup":
        try:
            pyautogui.keyUp(key)
        except Exception as e:
            print(f"[WARN] keyUp failed for '{key}': {e}")
    else:
        print(f"[WARN] Unknown keyboard action: {action}")


async def handle_incoming(ws: websockets.WebSocketServerProtocol) -> None:
    """Receive and process incoming messages from a client until disconnect."""
    async for raw in ws:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print("[WARN] Received non-JSON message")
            continue

        msg_type = payload.get("type")
        if msg_type == "mouse":
            _handle_mouse_event(payload)
        elif msg_type == "keyboard":
            _handle_keyboard_event(payload)
        else:
            print(f"[INFO] Ignoring unknown message type: {msg_type}")


async def connection_handler(ws: websockets.WebSocketServerProtocol) -> None:
    """Manage lifecycle for a single WebSocket connection.

    Spawns concurrent tasks: one for sending frames, one for receiving input.
    """
    if len(ACTIVE_CONNECTIONS) >= settings.max_connections:
        await ws.close(code=1013, reason="Server busy: max connections reached")
        print("[INFO] Rejected connection: capacity reached")
        return

    print("[INFO] New client connected")
    ACTIVE_CONNECTIONS.add(ws)
    try:
        # Run capture and incoming handlers concurrently.
        sender = asyncio.create_task(capture_and_send_frames(ws))
        receiver = asyncio.create_task(handle_incoming(ws))
        done, pending = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
    finally:
        ACTIVE_CONNECTIONS.discard(ws)
        print("[INFO] Client disconnected")


async def main() -> None:
    """Start the WebSocket server and serve forever until interrupted."""
    print(f"[INFO] Starting server on {settings.host}:{settings.port}")
    async with websockets.serve(connection_handler, settings.host, settings.port):
        print("[INFO] Server ready. Press Ctrl+C to stop.")
        await asyncio.Future()  # Run until cancelled.


if __name__ == "__main__":
    # PyAutoGUI fails if failsafe triggered (mouse moved to corner). Disable failsafe for remote control.
    pyautogui.FAILSAFE = False
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[INFO] Server shutdown requested by user")
