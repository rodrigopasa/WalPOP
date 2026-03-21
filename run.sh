#!/bin/bash
# PopWallpaper Launcher Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Setting up virtual environment..."
    
    # Check if python3-venv is installed
    if ! dpkg -l | grep -q python3-venv; then
        echo "python3-venv is not installed."
        echo "Installing dependencies with pipx..."
        
        # Install pipx if not available
        if ! command -v pipx &> /dev/null; then
            echo "Installing pipx..."
            sudo apt install -y pipx
        fi
        
        # Use pipx to run in isolated environment
        pipx install customtkinter
        pipx inject customtkinter Pillow
        
        echo "Running with pipx environment..."
        cd "$SCRIPT_DIR"
        python3 popwallpaper.py
        exit 0
    else
        python3 -m venv "$SCRIPT_DIR/venv"
        "$SCRIPT_DIR/venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    fi
fi

# Activate virtual environment and run
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    python3 "$SCRIPT_DIR/popwallpaper.py"
else
    # Fallback: try running directly
    cd "$SCRIPT_DIR"
    python3 popwallpaper.py
fi
