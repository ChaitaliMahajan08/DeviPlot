import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.main import app
from backend.app.config import settings

if __name__ == "__main__":
    print(f"============================================================")
    print(f"   DevPilot — Autonomous AI Engineering Guild (PS-001)     ")
    print(f"   Plan like a Shogun. Build like a Samurai.               ")
    print(f"   Test like a Sentinel. Adapt until the mission is done.  ")
    print(f"============================================================")
    print(f"Server starting on http://{settings.HOST}:{settings.PORT}")
    print(f"Default Workspace: {settings.DEFAULT_WORKSPACE}")
    print(f"Press Ctrl+C to terminate.")
    print(f"============================================================")
    app.run(host=settings.HOST, port=settings.PORT, debug=False, threaded=True)
