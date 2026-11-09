"""
AgriNiramaya - Single-Click Application Launcher
Runs the Flask server and opens the browser to AgriNiramaya Home.
"""

import os
import sys
import webbrowser
import threading
import time

# Ensure flask_project is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLASK_DIR = os.path.join(BASE_DIR, "flask_project")
sys.path.insert(0, FLASK_DIR)

from app import app, init_db

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:5000"
    print(f"\n✨ Opening AgriNiramaya in your web browser: {url}\n")
    webbrowser.open(url)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=open_browser, daemon=True).start()
    print("=" * 68)
    print("🌿 AgriNiramaya: Healthy Plants. Smarter Farming.")
    print("   AI-Enabled Integrated Plant Health and Soil Monitoring System")
    print("   EDI First-Year Engineering Project")
    print("   Running locally on: http://127.0.0.1:5000")
    print("   Press Ctrl+C to stop the application server")
    print("=" * 68)
    app.run(host="0.0.0.0", port=5000, debug=False)
