#!/bin/bash
# ─────────────────────────────────────────────
# Walpop v2.0 — Script de Instalação
# Para Pop!_OS 24.04 (COSMIC / Wayland)
# ─────────────────────────────────────────────

set -e

echo "╔══════════════════════════════════════╗"
echo "║      🎬 Walpop — Instalação         ║"
echo "╚══════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. Dependências do sistema ──────────────
echo "📦 Instalando dependências do sistema..."
sudo apt update -qq
sudo apt install -y mpv mpvpaper ffmpeg python3-pip python3-venv

# ── 2. Ambiente virtual Python ──────────────
echo ""
echo "🐍 Criando ambiente virtual Python..."
cd "$SCRIPT_DIR"

if [ -d "venv" ]; then
    echo "   → venv já existe, atualizando..."
else
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "   ✅ Dependências Python instaladas"

# ── 3. Criar pasta assets se não existir ────
mkdir -p "$SCRIPT_DIR/assets"

# ── 4. Criar atalho no menu de apps ─────────
echo ""
echo "🔗 Criando atalho no menu de aplicativos..."

DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

ICON_PATH="$SCRIPT_DIR/assets/icon.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_PATH="preferences-desktop-wallpaper"
fi

cat > "$DESKTOP_DIR/walpop.desktop" << EOF
[Desktop Entry]
Version=2.0
Type=Application
Name=Walpop
GenericName=Gerenciador de Wallpapers Animados
Comment=Gerencie e aplique wallpapers animados com mpvpaper
Exec=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/walpop.py
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Settings;DesktopSettings;
Keywords=wallpaper;fundo;video;animado;mpvpaper;
StartupNotify=true
Path=$SCRIPT_DIR
EOF

chmod +x "$DESKTOP_DIR/walpop.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "   ✅ Atalho criado em $DESKTOP_DIR/walpop.desktop"

# ── 5. Criar diretórios de config ───────────
mkdir -p "$HOME/.config/walpop/thumbs"
echo "   ✅ Diretórios de configuração criados"

# ── Concluído ───────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   ✅ Walpop instalado com sucesso!  ║"
echo "╠══════════════════════════════════════╣"
echo "║                                      ║"
echo "║  Para rodar:                         ║"
echo "║    source venv/bin/activate          ║"
echo "║    python3 walpop.py                 ║"
echo "║                                      ║"
echo "║  Ou busque 'Walpop' no menu de apps ║"
echo "╚══════════════════════════════════════╝"
