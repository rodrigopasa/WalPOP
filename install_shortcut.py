#!/usr/bin/env python3
"""
PopWallpaper Desktop Shortcut Installer
Creates a .desktop file for easy access from the applications menu
"""

import os
import sys
import urllib.request
from pathlib import Path


def get_project_dir():
    """Get the absolute path to the PopWallpaper project directory"""
    # Get the directory where this script is located
    return os.path.dirname(os.path.abspath(__file__))


def download_icon():
    """Download a wallpaper-themed icon or use system icon"""
    icon_dir = os.path.join(get_project_dir(), "icons")
    icon_path = os.path.join(icon_dir, "popwallpaper.png")
    
    # Create icons directory if it doesn't exist
    os.makedirs(icon_dir, exist_ok=True)
    
    # Try to download a nice wallpaper icon from an open source icon library
    icon_urls = [
        "https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/wallpaper.svg",
        "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/solid/image.svg"
    ]
    
    for url in icon_urls:
        try:
            print(f"Downloading icon from {url}...")
            urllib.request.urlretrieve(url, icon_path.replace('.png', '.svg'))
            print(f"✅ Icon downloaded to {icon_path}")
            return icon_path.replace('.png', '.svg')
        except Exception as e:
            print(f"⚠️ Failed to download from {url}: {e}")
            continue
    
    # If download fails, use system icon name
    print("⚠️ Using system wallpaper icon instead")
    return "preferences-desktop-wallpaper"


def create_desktop_file():
    """Create the .desktop file in ~/.local/share/applications/"""
    project_dir = get_project_dir()
    
    # Paths
    desktop_dir = os.path.expanduser("~/.local/share/applications")
    desktop_file = os.path.join(desktop_dir, "popwallpaper.desktop")
    
    # Ensure directory exists
    os.makedirs(desktop_dir, exist_ok=True)
    
    # Try to get icon
    icon = download_icon()
    
    # Determine how to run the application
    venv_python = os.path.join(project_dir, "venv", "bin", "python3")
    main_script = os.path.join(project_dir, "popwallpaper.py")
    run_script = os.path.join(project_dir, "run.sh")
    
    # Prefer run.sh if it exists, otherwise use venv python, otherwise system python
    if os.path.exists(run_script):
        exec_cmd = run_script
    elif os.path.exists(venv_python):
        exec_cmd = f"{venv_python} {main_script}"
    else:
        exec_cmd = f"python3 {main_script}"
    
    # Desktop file content
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=PopWallpaper
GenericName=Animated Wallpaper Manager
Comment=Manage and apply animated wallpapers from Wallpaper Engine
Exec={exec_cmd}
Icon={icon}
Terminal=false
Categories=Utility;Settings;DesktopSettings;GTK;
Keywords=wallpaper;background;video;animated;mpvpaper;
StartupNotify=true
Path={project_dir}
"""
    
    # Write desktop file
    try:
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        
        # Make it executable
        os.chmod(desktop_file, 0o755)
        
        print(f"\n✅ Desktop shortcut created successfully!")
        print(f"   Location: {desktop_file}")
        print(f"   Icon: {icon}")
        print(f"   Exec: {exec_cmd}")
        print(f"\n🎉 You can now launch PopWallpaper from your applications menu!")
        
        # Update desktop database for immediate recognition
        try:
            import subprocess
            subprocess.run(['update-desktop-database', desktop_dir], 
                         check=False, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            print("   Desktop database updated!")
        except Exception:
            pass
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating desktop file: {e}")
        return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("PopWallpaper - Desktop Shortcut Installer")
    print("=" * 60)
    print()
    
    if create_desktop_file():
        print("\n" + "=" * 60)
        print("Installation Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Open your applications menu")
        print("2. Search for 'PopWallpaper'")
        print("3. Click to launch!")
        print()
    else:
        print("\nInstallation failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
