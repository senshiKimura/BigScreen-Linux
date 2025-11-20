#BIGSCREEN ON LINUX

Linux Remote Desktop Prototype (BigScreen-Linux)
================================================

Goal
----
Provide an open, highly readable prototype of a remote desktop streamer for Linux inspired by the "Bigscreen" remote desktop concept. Instead of shipping a closed executable, this repository shows clear, commented source code so anyone can learn, fork, and extend.

High-Level Features (Current Prototype)
--------------------------------------
- WebSocket server that captures the full screen periodically.
- JPEG frame encoding with adjustable quality & scale for bandwidth control.
- Browser-based client receives frames and displays them in real time.
- Mouse movement, clicks, and keyboard key presses forwarded back to the host.
- All code heavily commented in English for public readability.

Planned / Future Enhancements (Roadmap Ideas)
--------------------------------------------
- Authentication & authorization (current prototype is insecure for open networks).
- TLS termination (run behind a reverse proxy like Caddy / Nginx or use wss directly).
- Multi-monitor selection & dynamic resolution changes.
- Higher performance streaming (WebRTC media channel, H.264 / VP9 / AV1 encoding).
- Delta region updates instead of full-frame pushes.
- Clipboard sync, file transfer, drag operations, scrolling, double-click detection.
- Input permission gating (allow keyboard but not mouse, etc.).

Architecture Overview
---------------------
Server (Python):
- Uses `mss` to capture raw screen frames.
- Converts frames to PIL Image to optionally resize and JPEG encode.
- Base64 encodes the JPEG and sends JSON messages via `websockets`.
- Receives JSON input events and replays them locally using `pyautogui`.

Client (Browser / Vanilla JS):
- Establishes a WebSocket connection.
- Renders each received JPEG frame in an `<img>` element.
- Captures mouse position relative to the displayed image; scales coordinates back to original resolution.
- Sends keyboard and mouse events as JSON payloads.

Message Protocol (JSON)
-----------------------
Frame (Server -> Client):
```
{
	"type": "frame",
	"timestamp": 1730.123,
	"encoding": "jpeg-base64",
	"width": 1920,
	"height": 1080,
	"quality": 60,
	"data": "<BASE64_JPEG_DATA>"
}
```

Mouse Move (Client -> Server):
```
{ "type": "mouse", "action": "move", "x": 100, "y": 200 }
```

Mouse Click:
```
{ "type": "mouse", "action": "click", "button": "left" }
```

Keyboard Events:
```
{ "type": "keyboard", "action": "keydown", "key": "a" }
{ "type": "keyboard", "action": "keyup", "key": "a" }
```

Repository Layout
-----------------
```
server/
	main.py          # WebSocket server: capture + stream + input handling
	config.py        # Centralized settings with env var overrides
	requirements.txt # Python dependencies
client/
	index.html       # Simple UI (connect, disconnect, view stream)
	style.css        # Basic styling for readability
	script.js        # Logic for receiving frames & sending input
README.md          # This file: documentation & guidance
```

Prerequisites
-------------
- Linux OS (capture depends on system X11 / Wayland compatibility with `mss`).
- Python 3.10+ recommended.
- A modern browser for the client (tested with Chromium / Firefox).

Installation (Server)
---------------------
Create and activate a virtual environment (recommended) then install dependencies.

Windows PowerShell example (adapt for Linux shell):
```
python -m venv .venv
.venv\Scripts\activate
pip install -r server/requirements.txt
```

Linux/macOS example:
```
python -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
```

Run the Server
--------------
Adjust environment variables as desired (see `server/config.py`). Then start:
```
python server/main.py
```
Default listens on `0.0.0.0:8765`.

Environment Variable Overrides
------------------------------
| Variable | Default | Description |
|----------|---------|-------------|
| REMOTE_HOST | 0.0.0.0 | Bind address. Use 127.0.0.1 for local only. |
| REMOTE_PORT | 8765 | WebSocket port. |
| REMOTE_FPS | 12 | Target frames per second (soft). |
| REMOTE_JPEG_QUALITY | 60 | JPEG quality (1-95 typical). |
| REMOTE_MAX_CONNECTIONS | 5 | Connection cap. |
| REMOTE_RESIZE_SCALE | 1.0 | Resize factor (<1 reduces bandwidth). |
| REMOTE_SEND_CURSOR | 1 | Placeholder for future cursor overlay. |

Run the Client
--------------
Open `client/index.html` in your browser. Enter the WebSocket URL (e.g., `ws://localhost:8765`) and click Connect.

Security Warning
----------------
This prototype offers NO authentication, NO encryption, and NO authorization. If you expose it beyond localhost you risk granting full remote control of your machine. Suggested temporary mitigation:
- Use an SSH tunnel: `ssh -L 8765:localhost:8765 user@host`.
- Place behind a reverse proxy with HTTPS & Basic Auth (still weak, better: tokens).
- Limit accessible IPs via firewall.

Performance Tips
----------------
- Lower `REMOTE_JPEG_QUALITY` or set `REMOTE_RESIZE_SCALE=0.5` to reduce bandwidth.
- Reduce `REMOTE_FPS` if CPU usage is high.
- For substantial improvement, integrate a video codec (H.264, VP9) via ffmpeg or switch to WebRTC (future work).

Troubleshooting
---------------
| Symptom | Possible Cause | Resolution |
|---------|----------------|-----------|
| Black / empty image | Wayland compatibility issue | Try X11 session or update mss. |
| Extreme latency | High JPEG quality or large resolution | Lower quality / enable resize scale. |
| Input not registering | pyautogui limitations | Run with correct permissions; avoid Wayland restrictions. |

Contribution Guidelines
-----------------------
Please keep code heavily commented (English) and avoid introducing complex frameworks prematurely. Focus on clarity first, optimization later.

License
-------
No explicit license yet. Consider adding MIT / Apache-2.0 for broader adoption.

Acknowledgments
---------------
Inspired by remote desktop and VR streaming concepts (e.g., Bigscreen). Built for educational transparency.


This repo will show you how to use BigScreen Remote Desktop (exe) on differents Linux distributions
THIS IS NOT STABLE SO YOU CAN HAVE SOMES PROBLEMS
