#!/usr/bin/env python3
"""
Launch Chrome with debug port and automatically open Claude.ai
"""
import os
import subprocess
import time
import sys
import glob


def find_chrome_profiles():
    """Find available Chrome profiles on macOS."""
    chrome_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    profiles = []
    
    # Look for Profile directories
    for profile_dir in glob.glob(os.path.join(chrome_dir, "Profile*")):
        if os.path.isdir(profile_dir):
            profile_name = os.path.basename(profile_dir)
            
            # Try to get the profile's display name
            prefs_file = os.path.join(profile_dir, "Preferences")
            display_name = profile_name
            
            if os.path.exists(prefs_file):
                try:
                    import json
                    with open(prefs_file, 'r') as f:
                        prefs = json.load(f)
                        # Look for account info
                        account_info = prefs.get('account_info', [])
                        if account_info and len(account_info) > 0:
                            email = account_info[0].get('email', '')
                            if email:
                                display_name = f"{profile_name} ({email})"
                except:
                    pass
            
            profiles.append((profile_name, display_name, profile_dir))
    
    # Also check Default profile
    default_dir = os.path.join(chrome_dir, "Default")
    if os.path.exists(default_dir):
        profiles.insert(0, ("Default", "Default Profile", default_dir))
    
    return profiles


def launch_chrome_with_profile(profile_dir=None):
    """Launch Chrome with debug port and optional profile."""
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    # For debugging, we need a separate data directory
    debug_base = os.path.expanduser("~/.claude-sync-chrome-debug")
    
    # Base command
    cmd = [chrome_path]
    
    # Add profile if specified, otherwise use debug directory
    if profile_dir:
        # Copy profile name for debug use
        profile_name = os.path.basename(profile_dir)
        debug_dir = os.path.join(debug_base, f"debug-{profile_name}")
        os.makedirs(debug_dir, exist_ok=True)
        cmd.append(f"--user-data-dir={debug_dir}")
        print(f"Note: Using debug copy at {debug_dir}")
        print(f"(Chrome requires a separate data dir for debugging)")
    else:
        # Use default debug directory
        debug_dir = os.path.join(debug_base, "debug-default")
        os.makedirs(debug_dir, exist_ok=True)
        cmd.append(f"--user-data-dir={debug_dir}")
    
    # Add debug flags
    cmd.extend([
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--disable-default-apps",
        "--disable-popup-blocking",
        "https://claude.ai/"
    ])
    
    print(f"\nLaunching Chrome...")
    print(f"Debug profile: {debug_dir}")
    
    # Launch Chrome with suppressed stderr
    subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
    
    # Wait for Chrome to start
    print("\nWaiting for Chrome to start...")
    time.sleep(3)
    
    # Verify connection
    try:
        import requests
        response = requests.get('http://localhost:9222/json', timeout=5)
        pages = response.json()
        print(f"✓ Chrome started successfully with {len(pages)} pages")
        
        # Check for Claude page
        claude_pages = [p for p in pages if 'claude.ai' in p.get('url', '')]
        if claude_pages:
            print(f"✓ Claude.ai page opened: {claude_pages[0].get('url')}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to connect to Chrome: {e}")
        return False


def main():
    """Main function to interactively launch Chrome."""
    print("Chrome Profile Launcher for Claude.ai")
    print("=" * 50)
    
    # Find profiles
    profiles = find_chrome_profiles()
    
    if not profiles:
        print("No Chrome profiles found!")
        return
    
    print("\nAvailable Chrome profiles:")
    print("-" * 50)
    for i, (name, display_name, path) in enumerate(profiles):
        print(f"{i + 1}. {display_name}")
        if "eric@triskew.com" in display_name:
            print("   ^ This looks like your Claude.ai profile!")
    
    print(f"\n0. Launch without specific profile (fresh profile)")
    
    # Get user choice
    while True:
        try:
            choice = input("\nSelect profile number (or press Enter for fresh profile): ").strip()
            
            if choice == "" or choice == "0":
                print("\nLaunching Chrome with fresh profile...")
                launch_chrome_with_profile(None)
                break
            
            idx = int(choice) - 1
            if 0 <= idx < len(profiles):
                name, display_name, profile_dir = profiles[idx]
                print(f"\nLaunching Chrome with profile: {display_name}")
                launch_chrome_with_profile(profile_dir)
                break
            else:
                print("Invalid choice, please try again.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)
    
    print("\nChrome launched! You can now:")
    print("1. Log into Claude.ai if needed")
    print("2. Run: python manual_test_chrome_client.py")


if __name__ == "__main__":
    main()