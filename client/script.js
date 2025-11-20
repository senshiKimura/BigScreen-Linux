/*
 script.js

 Minimal JavaScript client logic:
 - Connect to the WebSocket server.
 - Display incoming frame messages (JPEG base64) inside an <img> tag.
 - Capture mouse move / click and keyboard events over the image and send them back.

 This file is intentionally verbose with comments for public readability.
*/

let socket = null;
const statusEl = document.getElementById('status');
const screenImg = document.getElementById('screen');
const connectBtn = document.getElementById('connectBtn');
const disconnectBtn = document.getElementById('disconnectBtn');
const serverUrlInput = document.getElementById('serverUrl');

function logStatus(msg) {
  statusEl.textContent = msg;
}

function connect() {
  const url = serverUrlInput.value.trim();
  if (!url) {
    logStatus('Please enter a WebSocket URL');
    return;
  }
  socket = new WebSocket(url);
  logStatus('Connecting...');
  connectBtn.disabled = true;

  socket.onopen = () => {
    logStatus('Connected');
    disconnectBtn.disabled = false;
  };

  socket.onclose = (evt) => {
    logStatus('Disconnected');
    connectBtn.disabled = false;
    disconnectBtn.disabled = true;
    socket = null;
  };

  socket.onerror = (err) => {
    console.error('WebSocket error:', err);
    logStatus('Error (see console)');
  };

  socket.onmessage = (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      if (payload.type === 'frame' && payload.encoding === 'jpeg-base64') {
        // Update the <img> source directly.
        screenImg.src = 'data:image/jpeg;base64,' + payload.data;
      }
    } catch (e) {
      console.warn('Non-JSON frame or parse failed:', e);
    }
  };
}

function disconnect() {
  if (socket) {
    socket.close();
  }
}

connectBtn.addEventListener('click', connect);
disconnectBtn.addEventListener('click', disconnect);

// --- Input Event Forwarding -------------------------------------------------
// We attach listeners to the image container. Coordinates must map to real screen.
// Because the server may have resized the stream, we scale mouse coordinates back
// to the original captured dimensions using the <img> displayed size vs intrinsic size.

function send(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

screenImg.addEventListener('mousemove', (e) => {
  if (!screenImg.naturalWidth || !screenImg.naturalHeight) return;
  // Compute scaling ratio between displayed size and natural (captured) size.
  const rect = screenImg.getBoundingClientRect();
  const scaleX = screenImg.naturalWidth / rect.width;
  const scaleY = screenImg.naturalHeight / rect.height;
  const x = Math.round((e.clientX - rect.left) * scaleX);
  const y = Math.round((e.clientY - rect.top) * scaleY);
  send({ type: 'mouse', action: 'move', x, y });
});

screenImg.addEventListener('click', (e) => {
  send({ type: 'mouse', action: 'click', button: 'left' });
});

// Capture key presses globally. In future we might focus only when pointer over image.
window.addEventListener('keydown', (e) => {
  // Avoid sending auto-repeated keydown events (optional improvement later).
  send({ type: 'keyboard', action: 'keydown', key: e.key });
});
window.addEventListener('keyup', (e) => {
  send({ type: 'keyboard', action: 'keyup', key: e.key });
});

// Prevent browser default actions (e.g., space scrolling) when controlling remote desktop.
window.addEventListener('keydown', (e) => {
  // Basic list of keys we typically want to suppress.
  const suppress = [' ', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Tab'];
  if (suppress.includes(e.key)) {
    e.preventDefault();
  }
});

// Optional: reconnect helper (future improvement).
