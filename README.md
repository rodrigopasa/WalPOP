# 🎬 Walpop

> Animated wallpaper manager for Pop!_OS 24.04 (COSMIC / Wayland)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Pop!_OS%2024.04-orange.svg)
![Desktop](https://img.shields.io/badge/session-Wayland-blueviolet.svg)

Walpop scans your **Steam Workshop** wallpapers and any **custom folder** you choose, then applies video wallpapers to your desktop through [mpvpaper](https://github.com/GhostNaN/mpvpaper). It features a modern dark UI built with [customtkinter](https://github.com/TomSchimansky/CustomTkinter), persistent configuration, FPS control, video optimization, and autostart support.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎮 **Steam Workshop** | Automatically scans Wallpaper Engine folders, reads `project.json`, and filters video-type wallpapers |
| 📁 **Custom Folder** | Point to any directory — all `.mp4`, `.webm`, `.mkv` files are picked up |
| 📋 **Unified List** | All wallpapers displayed in a single scrollable list with thumbnails and `[Steam]` / `[Custom]` tags |
| 🖼️ **Thumbnail Cache** | Auto-generates thumbnails via `ffmpeg` and caches them in `~/.config/walpop/thumbs/` |
| 🔍 **Search & Favorites** | Built-in search bar and favorites system (⭐) to quickly find and save wallpapers |
| 🖥️ **Multi-monitor Setup** | Specify exact monitors (e.g., `eDP-1`) or apply to all (`*`) seamlessly |
| ⏸️ **Smart Pause (Battery)** | Automatically freezes the wallpaper when your laptop unplugs to save battery |
| 🔀 **Auto-Shuffle** | Automatically rotates your favorite wallpapers at configurable intervals |
| 🎈 **System Tray Icon** | Lives in your taskbar for quick playback controls without opening the main window |
| 🎯 **FPS Control** | Slider with discrete values (10 / 15 / 24 / 30 / 60) — lower FPS = lower CPU usage |
| ⏩ **Speed Control** | Slider to control the playback speed (0.25x to 2.0x) |
| ⚡ **Video Optimization** | One-click optimization via `ffmpeg` — scales to 720p, removes audio, compresses with CRF 28 |
| 🚀 **Autostart** | Toggle to launch Walpop on boot and automatically apply the last used wallpaper (no UI) |
| 💾 **Persistent Config** | All settings saved to `~/.config/walpop/config.json` — survives restarts |
| 🌙 **Dark Theme** | Modern dark UI in Brazilian Portuguese |
| 📝 **Error Logging** | All errors logged to `~/.config/walpop/walpop.log` |

---

## 📋 Requirements

## 📋 Requirements

- **Pop!_OS 24.04** with Wayland / COSMIC
- **Python 3.10+**
- **ffmpeg** — generates thumbnails and optimizes videos
- **mpvpaper** — renders the animated wallpaper on the desktop

### ⚠️ Installing `mpvpaper` (Crucial Step)
`mpvpaper` is **not** available in the official Ubuntu/Pop!_OS repositories. You must install it manually before Walpop can draw wallpapers.
You can compile it directly from the [GhostNaN/mpvpaper repository](https://github.com/GhostNaN/mpvpaper):

```bash
# 1. Install build dependencies
sudo apt update
sudo apt install -y meson ninja-build libwlroots-dev wayland-protocols libegl-dev libwayland-dev libgles2-dev libmpv-dev git

# 2. Clone and build
git clone https://github.com/GhostNaN/mpvpaper.git
cd mpvpaper
meson setup build
ninja -C build
sudo ninja -C build install
```

---

## 🚀 Installation

### Option 1: Native DEB Package (Recommended)
You can build a native Debian package that will automatically install all dependencies (`mpvpaper`, `ffmpeg`, etc.) and the application globally:
```bash
git clone https://github.com/rodrigopasa/WalPOP.git
cd WalPOP
bash build_deb.sh
sudo apt install ./walpop_2.0_amd64.deb
```

### Option 2: Standalone Executable
If you just want a single executable without installing globally:
```bash
bash build_executable.sh 
# The executable will be available in dist/Walpop
./dist/Walpop
```

### Option 3: Local script installation
```bash
chmod +x install.sh
bash install.sh
```

The install script will:
1. Install system dependencies (`mpv`, `mpvpaper`, `ffmpeg`, `python3-pip`, `python3-venv`)
2. Create a Python virtual environment and install `customtkinter` + `Pillow`
3. Add a **Walpop** shortcut to your applications menu

---

## ▶️ Usage

### Launch the app
```bash
source venv/bin/activate
python3 walpop.py
```
Or search for **Walpop** in your applications menu after installation.

### Apply a wallpaper
1. Browse the wallpaper list (Steam Workshop items are detected automatically)
2. Optionally set a **custom folder** using the folder picker at the top
3. Adjust the **FPS slider** to your preference
4. Click **Aplicar** on any wallpaper

The wallpaper runs as an independent `mpvpaper` process — **closing the app does NOT stop the wallpaper**.

### Optimize a video
Click **Otimizar** on any wallpaper to create a lighter version:
- Scales down to **1280×720**
- Removes audio track
- Compresses with `libx264` CRF 28
- Progress bar shown during encoding

### Autostart
Enable **"Iniciar com o sistema"** to automatically apply the last wallpaper on boot without opening the UI.

```bash
# This is what happens under the hood:
python3 walpop.py --autostart
```

---

## 📂 Project Structure

```
WalPOP/
├── walpop.py              # Main application (UI + logic)
├── requirements.txt       # Python dependencies
├── build_deb.sh           # Script to build native .deb package
├── build_executable.sh    # Script to build standalone PyInstaller executable
├── install.sh             # One-command installer
├── walpop.desktop         # Desktop entry template
└── assets/
    └── icon.png           # Application icon
```

### Config files (created at runtime)

```
~/.config/walpop/
├── config.json            # Settings (FPS, custom folder, last wallpaper, autostart)
├── walpop.log             # Error and info logs
└── thumbs/                # Cached thumbnail images
```

---

## ⚙️ Configuration

The config file (`~/.config/walpop/config.json`) is managed automatically:

```json
{
  "fps": 30,
  "speed": 1.0,
  "custom_folder": "/home/user/Wallpapers",
  "last_wallpaper": "/path/to/video.mp4",
  "autostart": false
}
```

---

## 🎮 Steam Workshop Paths

Walpop scans the following directories for Wallpaper Engine content:

```
~/.local/share/Steam/steamapps/workshop/content/431960/
~/.steam/debian-installation/steamapps/workshop/content/431960/
```

For each subfolder, it reads `project.json` and:
- ✅ Includes wallpapers with video type (`.mp4`, `.webm`)
- ❌ Skips `scene` and `web` type wallpapers
- 🖼️ Uses `preview.jpg` / `preview.png` as thumbnail when available

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| **"mpvpaper não encontrado"** | `sudo apt install mpvpaper` |
| **"ffmpeg não encontrado"** | `sudo apt install ffmpeg` |
| **No wallpapers found** | Make sure Steam is installed with Wallpaper Engine subscriptions, or set a custom folder |
| **Wallpaper not applying** | Verify you're on a Wayland session: `echo $XDG_SESSION_TYPE` |
| **App won't start** | Check the log: `cat ~/.config/walpop/walpop.log` |

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — Modern dark UI framework
- [mpvpaper](https://github.com/GhostNaN/mpvpaper) — Wayland wallpaper renderer
- [ffmpeg](https://ffmpeg.org/) — Video processing
- Wallpaper Engine community for amazing content
