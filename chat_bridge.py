"""Local, read-only YouTube live chat bridge for the OBS browser game."""

import json
import re
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).with_name("vendor")))
import pytchat

VIDEO_ID = sys.argv[1] if len(sys.argv) > 1 else ""
HOST, PORT = "127.0.0.1", 8765
messages = deque(maxlen=500)
lock = threading.Lock()
sequence = 0
state = "waiting for live link"


def read_chat():
    global sequence, state
    while True:
        with lock:
            selected = VIDEO_ID
        if not selected:
            time.sleep(0.5)
            continue
        chat = None
        try:
            with lock:
                if VIDEO_ID == selected:
                    state = "connecting"
            chat = pytchat.create(video_id=selected, interruptable=False)
            with lock:
                if VIDEO_ID == selected:
                    state = "connected"
            while chat.is_alive():
                with lock:
                    if VIDEO_ID != selected:
                        break
                for item in chat.get().sync_items():
                    if not getattr(item, "message", "").strip():
                        continue
                    author = item.author
                    with lock:
                        if VIDEO_ID != selected:
                            break
                        sequence += 1
                        messages.append({
                            "seq": sequence,
                            "id": item.id,
                            "name": author.name,
                            "channelId": author.channelId,
                            "photo": author.imageUrl,
                            "message": item.message,
                            "timestamp": int(item.timestamp),
                        })
                time.sleep(0.5)
            with lock:
                if VIDEO_ID == selected:
                    state = "reconnecting"
        except Exception as exc:
            with lock:
                if VIDEO_ID == selected:
                    state = "error: " + str(exc)[:160]
        finally:
            if chat:
                chat.terminate()
        time.sleep(1)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global VIDEO_ID, sequence, state
        url = urlparse(self.path)
        params = parse_qs(url.query)
        if url.path not in ("/connect", "/health", "/messages"):
            self.send_error(404)
            return
        requested = params.get("video", [""])[0]
        if url.path == "/connect" and not re.fullmatch(r"[A-Za-z0-9_-]{11}", requested):
            self.send_error(400, "Invalid video ID")
            return
        try:
            since = int(params.get("since", ["0"])[0])
        except ValueError:
            since = 0
        with lock:
            if url.path == "/connect" and requested != VIDEO_ID:
                VIDEO_ID = requested
                messages.clear()
                sequence = 0
                state = "connecting"
            payload = {
                "state": state,
                "video": VIDEO_ID,
                "latest": sequence,
                "messages": [m for m in messages if m["seq"] > since and m["timestamp"] >= (time.time() - 65) * 1000] if url.path == "/messages" else [],
            }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def log_message(self, *args):
        pass


threading.Thread(target=read_chat, daemon=True).start()
print(f"Chat bridge listening on http://{HOST}:{PORT} for {VIDEO_ID}", flush=True)
ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
