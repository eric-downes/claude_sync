#!/usr/bin/env python3
"""
Clean up Chrome debug profiles created by claude-sync
"""
import os
import shutil


def clean_debug_profiles():
    """Remove Chrome debug profiles."""
    debug_dir = os.path.expanduser("~/.claude-sync-chrome-debug")
    
    if os.path.exists(debug_dir):
        print(f"Found debug directory: {debug_dir}")
        
        # Show size
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(debug_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        
        size_mb = total_size / (1024 * 1024)
        print(f"Total size: {size_mb:.1f} MB")
        
        response = input("\nDelete debug profiles? (y/N): ").strip().lower()
        if response == 'y':
            shutil.rmtree(debug_dir)
            print("✓ Debug profiles deleted")
        else:
            print("Cancelled")
    else:
        print("No debug profiles found")


if __name__ == "__main__":
    clean_debug_profiles()