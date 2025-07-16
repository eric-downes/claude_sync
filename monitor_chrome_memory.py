#!/usr/bin/env python3
"""
Monitor Chrome memory usage to validate our assumptions.
Run this after starting headless Chrome to see actual memory usage.
"""
import time
import psutil
import subprocess
from datetime import datetime


def get_chrome_memory() -> float:
    """Get total memory usage of Chrome processes in MB."""
    total_mb = 0
    chrome_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if 'chrome' in proc.info['name'].lower():
                mb = proc.info['memory_info'].rss / 1024 / 1024
                chrome_processes.append((proc.info['pid'], proc.info['name'], mb))
                total_mb += mb
        except:
            pass
    
    return total_mb, chrome_processes


def monitor_memory(duration_minutes: int = 10):
    """Monitor Chrome memory usage over time."""
    print(f"Monitoring Chrome memory for {duration_minutes} minutes...")
    print("=" * 60)
    
    measurements = []
    
    for i in range(duration_minutes * 6):  # Check every 10 seconds
        total_mb, processes = get_chrome_memory()
        measurements.append(total_mb)
        
        # Print current status
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\r[{timestamp}] Total: {total_mb:.1f}MB | Processes: {len(processes)}", end="")
        
        # Every minute, show details
        if i > 0 and i % 6 == 0:
            print(f"\n  Min: {min(measurements):.1f}MB | "
                  f"Max: {max(measurements):.1f}MB | "
                  f"Avg: {sum(measurements)/len(measurements):.1f}MB")
            
            # Show top 3 processes
            if processes:
                print("  Top processes:")
                for pid, name, mb in sorted(processes, key=lambda x: x[2], reverse=True)[:3]:
                    print(f"    {pid}: {name} - {mb:.1f}MB")
        
        time.sleep(10)
    
    print("\n\n" + "=" * 60)
    print(f"Summary after {duration_minutes} minutes:")
    print(f"  Minimum: {min(measurements):.1f}MB")
    print(f"  Maximum: {max(measurements):.1f}MB")
    print(f"  Average: {sum(measurements)/len(measurements):.1f}MB")
    
    if max(measurements) > 100:
        print("\n⚠️  Memory usage exceeded 100MB target")
    else:
        print("\n✅ Memory usage stayed under 100MB")


def test_headless_chrome():
    """Start headless Chrome and monitor its memory."""
    print("Starting headless Chrome for testing...")
    
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--remote-debugging-port=9222",
        "--user-data-dir=/tmp/chrome-memory-test",
        # All memory optimization flags
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor",
        "--disable-accelerated-2d-canvas",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-features=TranslateUI",
        "--disable-ipc-flooding-protection",
        "--disable-renderer-backgrounding",
        "--aggressive-cache-discard",
        "--aggressive-tab-discard",
        "--js-flags=--max-old-space-size=128",
        "--max_old_space_size=128",
        "--memory-pressure-off"
    ]
    
    # Start Chrome
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Started Chrome with PID: {proc.pid}")
    
    # Wait for it to stabilize
    print("Waiting 10 seconds for Chrome to stabilize...")
    time.sleep(10)
    
    # Monitor
    try:
        monitor_memory(5)  # Monitor for 5 minutes
    finally:
        print("\nStopping Chrome...")
        proc.terminate()
        time.sleep(2)
        
        # Cleanup
        subprocess.run(["rm", "-rf", "/tmp/chrome-memory-test"], capture_output=True)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        test_headless_chrome()
    else:
        # Just monitor existing Chrome
        monitor_memory(5)