#!/usr/bin/env python3
"""Debug Chrome connection issues."""
import requests
import socket
import time

print("Chrome Connection Diagnostics")
print("=" * 50)

# Test 1: Check if port is open
print("\n1. Testing if port 9222 is open...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
result = sock.connect_ex(('localhost', 9222))
sock.close()

if result == 0:
    print("✓ Port 9222 is open")
else:
    print("✗ Port 9222 is not reachable")
    print("  Make sure Chrome is running with: --remote-debugging-port=9222")

# Test 2: Try different endpoints
print("\n2. Testing Chrome DevTools endpoints...")
endpoints = [
    'http://localhost:9222/json',
    'http://127.0.0.1:9222/json',
    'http://localhost:9222/json/version',
    'http://127.0.0.1:9222/json/version',
]

for endpoint in endpoints:
    try:
        print(f"\nTrying {endpoint}...")
        response = requests.get(endpoint, timeout=2)
        print(f"✓ Success! Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"  Found {len(data)} pages")
                for page in data[:3]:  # Show first 3
                    print(f"  - {page.get('title', 'Untitled')}: {page.get('url', '')[:50]}...")
            else:
                print(f"  Response: {str(data)[:100]}...")
            break
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection refused")
    except requests.exceptions.Timeout:
        print(f"✗ Timeout")
    except Exception as e:
        print(f"✗ Error: {e}")

# Test 3: Check for common issues
print("\n3. Common issues check...")

# Check if Chrome needs a different user data dir
import subprocess
import os

# Look for existing Chrome debug instances
debug_dirs = [
    os.path.expanduser("~/.claude-sync-chrome-debug"),
    os.path.expanduser("~/.chrome-remote-debug"),
    "/tmp/chrome-debug"
]

print("\nChecking for debug profile directories...")
for dir_path in debug_dirs:
    if os.path.exists(dir_path):
        print(f"✓ Found: {dir_path}")

# Provide recommendations
print("\n" + "=" * 50)
print("RECOMMENDATIONS:")
print("=" * 50)

if result != 0:
    print("\n1. Chrome might not be running with debugging enabled.")
    print("   Kill all Chrome processes and restart with:")
    print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
    print("     --remote-debugging-port=9222 \\")
    print("     --user-data-dir=/tmp/chrome-debug")
    print("\n2. Or use the launch script:")
    print("   python scripts/launch_chrome_with_claude.py")
else:
    print("\nChrome appears to be running with debugging enabled.")
    print("Try running the test script again.")