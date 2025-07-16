#!/usr/bin/env python3
"""
Quick Chrome launcher - kills existing Chrome and starts fresh with debug port
"""
import subprocess
import time
import os


def kill_chrome():
    """Kill all Chrome processes."""
    print("Killing any existing Chrome processes...")
    subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
    time.sleep(1)


def launch_chrome_for_claude():
    """Launch Chrome with debug port and Claude.ai."""
    # Create a dedicated debug profile directory
    debug_dir = os.path.expanduser("~/.claude-sync-chrome-debug")
    os.makedirs(debug_dir, exist_ok=True)
    
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        f"--user-data-dir={debug_dir}",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--disable-default-apps",
        "--disable-popup-blocking",
        "https://claude.ai/"
    ]
    
    print("Launching Chrome with debug port...")
    print(f"Using debug profile at: {debug_dir}")
    print("Command:", " ".join(cmd))
    
    # Suppress stderr to avoid TensorFlow and other warnings
    subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
    
    print("\nChrome is starting...")
    print("If prompted, log in with eric@triskew.com")
    print("\nOnce logged in, run: python manual_test_chrome_client.py")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--kill":
        kill_chrome()
    
    launch_chrome_for_claude()