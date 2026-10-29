import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.main import app
from backend.app.config import settings

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = settings.PORT
    print(f"============================================================")
    print(f"   DevPilot — Autonomous AI Engineering Guild (PS-001)     ")
    print(f"   Plan like a Shogun. Build like a Samurai.               ")
    print(f"   Test like a Sentinel. Adapt until the mission is done.  ")
    print(f"============================================================")
    print(f" > Local URL:       http://localhost:{port}")
    print(f" > Network URL:     http://{local_ip}:{port} (same Wi-Fi)")
    print(f" > Default Workspace: {settings.DEFAULT_WORKSPACE}")
    print(f"============================================================")
    app.run(host=settings.HOST, port=settings.PORT, debug=False, threaded=True)
