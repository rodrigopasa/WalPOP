#!/usr/bin/env python3
"""
Test script for PopWallpaper - verifies Steam Workshop scanning
"""

import os
import json
from pathlib import Path

WORKSHOP_PATH = os.path.expanduser("~/.local/share/Steam/steamapps/workshop/content/431960")

def test_workshop_directory():
    """Test if workshop directory exists"""
    print(f"Testing workshop directory: {WORKSHOP_PATH}")
    
    if not os.path.exists(WORKSHOP_PATH):
        print("❌ Workshop directory not found")
        print("   Make sure Steam is installed and you have Wallpaper Engine workshop items")
        return False
    
    print("✅ Workshop directory exists")
    return True

def test_scan_wallpapers():
    """Test wallpaper scanning"""
    if not os.path.exists(WORKSHOP_PATH):
        return
    
    wallpapers = []
    folders = os.listdir(WORKSHOP_PATH)
    print(f"\nFound {len(folders)} workshop folders")
    
    for folder_name in folders[:5]:  # Test first 5
        folder_path = os.path.join(WORKSHOP_PATH, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
        
        project_json = os.path.join(folder_path, "project.json")
        
        if not os.path.exists(project_json):
            print(f"  ⚠️  {folder_name}: No project.json")
            continue
        
        try:
            with open(project_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            title = data.get('title', 'Untitled')
            wallpaper_type = data.get('type', 'unknown')
            file_name = data.get('file', '')
            
            print(f"  📁 {folder_name}:")
            print(f"     Title: {title}")
            print(f"     Type: {wallpaper_type}")
            print(f"     File: {file_name}")
            
            if wallpaper_type not in ['scene', 'web'] and file_name:
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext in ['.mp4', '.webm']:
                    wallpapers.append(title)
                    print(f"     ✅ Valid video wallpaper")
                else:
                    print(f"     ⚠️  Not a video file")
            else:
                print(f"     ⚠️  Skipped (type: {wallpaper_type})")
        
        except Exception as e:
            print(f"  ❌ {folder_name}: Error - {e}")
    
    print(f"\n✅ Found {len(wallpapers)} valid video wallpapers")
    return len(wallpapers) > 0

def test_mpvpaper():
    """Test if mpvpaper is installed"""
    print("\nTesting mpvpaper installation:")
    
    try:
        result = os.system("which mpvpaper > /dev/null 2>&1")
        if result == 0:
            print("✅ mpvpaper is installed")
            return True
        else:
            print("❌ mpvpaper not found")
            print("   Install with: sudo apt install mpvpaper")
            return False
    except Exception as e:
        print(f"❌ Error checking mpvpaper: {e}")
        return False

if __name__ == "__main__":
    print("PopWallpaper Test Suite")
    print("=" * 50)
    
    test_workshop_directory()
    test_scan_wallpapers()
    test_mpvpaper()
    
    print("\n" + "=" * 50)
    print("Test complete!")
