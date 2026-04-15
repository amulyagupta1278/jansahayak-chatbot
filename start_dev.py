# -*- coding: utf-8 -*-
"""
JanSahayak dev launcher -- starts uvicorn + ngrok in one command.

Usage:
    python start_dev.py

Reads NGROK_AUTHTOKEN from .env or environment.
Get a free token at: https://dashboard.ngrok.com/get-started/your-authtoken
"""

import os
import sys

# ── resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "jansahayak-starter")

# Load .env from project dir first, then repo root
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_DIR, ".env"))
    load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
except ImportError:
    pass

NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN", "")
PORT = int(os.getenv("PORT", "8000"))


def start_ngrok(port):
    try:
        from pyngrok import ngrok, conf
        if NGROK_AUTHTOKEN:
            conf.get_default().auth_token = NGROK_AUTHTOKEN
        tunnel = ngrok.connect(port, "http")
        url = tunnel.public_url
        if url.startswith("http://"):
            url = "https://" + url[7:]
        return url
    except Exception as exc:
        print("[warn] ngrok not started: {}".format(exc))
        return None


if __name__ == "__main__":
    public_url = start_ngrok(PORT)

    if public_url:
        webhook_url = "{}/whatsapp/twilio".format(public_url)
        print()
        print("=" * 62)
        print("  ngrok tunnel active")
        print("  Public URL : {}".format(public_url))
        print()
        print("  Set this in Twilio Console > Messaging > Sandbox:")
        print("  WHEN A MESSAGE COMES IN:")
        print("  {}".format(webhook_url))
        print("=" * 62)
        print()
    else:
        print("  Running locally only: http://localhost:{}".format(PORT))
        print()

    os.chdir(PROJECT_DIR)
    sys.path.insert(0, PROJECT_DIR)

    try:
        import uvicorn
    except ImportError:
        print("uvicorn not found. Run:  pip install uvicorn[standard]")
        sys.exit(1)

    print("Starting API on http://localhost:{}  (Ctrl+C to stop)\n".format(PORT))
    uvicorn.run(
        "apps.api.app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        reload_dirs=[PROJECT_DIR],
    )
