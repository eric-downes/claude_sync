#!/usr/bin/env python3
"""Launch Chrome with debug port non-interactively."""
import os
import subprocess
import time
import requests

# Kill any existing Chrome processes
print("Killing existing Chrome processes...")
subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
time.sleep(2)

# Launch Chrome with debug port
chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
debug_dir = os.path.expanduser("~/.claude-sync-chrome-debug/debug-default")
os.makedirs(debug_dir, exist_ok=True)

cmd = [
    chrome_path,
    f"--user-data-dir={debug_dir}",
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--no-first-run",
    "--disable-default-apps",
    "--disable-popup-blocking",
    "https://claude.ai/"
]

print(f"Launching Chrome with debug port 9222...")
print(f"Debug profile: {debug_dir}")

# Launch Chrome
proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

# Wait for Chrome to start
print("Waiting for Chrome to start...")
for i in range(10):
    time.sleep(1)
    try:
        response = requests.get('http://localhost:9222/json', timeout=1)
        pages = response.json()
        print(f"✓ Chrome started successfully with {len(pages)} pages")
        
        # Check for Claude page
        claude_pages = [p for p in pages if 'claude.ai' in p.get('url', '')]
        if claude_pages:
            print(f"✓ Claude.ai page opened: {claude_pages[0].get('url')}")
        
        print("\nChrome is ready! You can now run:")
        print("python test_dni_knowledge_titles.py")
        break
    except:
        if i == 9:
            print("✗ Failed to connect to Chrome after 10 seconds")
        else:
            print(f"  Waiting... ({i+1}/10)")