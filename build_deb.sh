#!/bin/bash
# ─────────────────────────────────────────────
# Walpop v2.0 — Criar Pacote .deb no padrão Linux
# Este pacote exige mpvpaper e ffmpeg nas dependencias
# ─────────────────────────────────────────────

set -e

echo "📦 Preparando ambiente para empacotar o DEB..."

# 1. Compilar executável se não existir
if [ ! -f "dist/Walpop" ]; then
    echo "🔨 Executável central não encontrado. Compilando com Pyinstaller..."
    chmod +x build_executable.sh
    bash build_executable.sh
fi

echo "📁 Criando a estrutura de pastas do pacote DEB..."
DEB_NAME="walpop_2.0_amd64"
mkdir -p "$DEB_NAME/DEBIAN"
mkdir -p "$DEB_NAME/usr/bin"
mkdir -p "$DEB_NAME/usr/share/applications"
mkdir -p "$DEB_NAME/usr/share/icons/hicolor/128x128/apps"

# Copiar o binário final compendiado para dentro do pacote
cp dist/Walpop "$DEB_NAME/usr/bin/walpop"
chmod +x "$DEB_NAME/usr/bin/walpop"

# Se houver ícone:
if [ -f "assets/icon.png" ]; then
    cp assets/icon.png "$DEB_NAME/usr/share/icons/hicolor/128x128/apps/walpop.png"
fi

# Criar .desktop no padrão do instalador
echo "🔗 Gerando atalho do sistema..."
cat > "$DEB_NAME/usr/share/applications/walpop.desktop" << EOF
[Desktop Entry]
Version=2.0
Type=Application
Name=Walpop
GenericName=Gerenciador de Wallpapers Animados
Comment=Gerencie e aplique wallpapers animados com mpvpaper
Exec=/usr/bin/walpop
Icon=walpop
Terminal=false
Categories=Utility;Settings;DesktopSettings;
Keywords=wallpaper;fundo;video;animado;mpvpaper;
StartupNotify=true
EOF

chmod +x "$DEB_NAME/usr/share/applications/walpop.desktop"

# Criar o arquivo de controle DEBIAN
echo "📝 Criando metadados de dependências (DEBIAN/control)..."
cat > "$DEB_NAME/DEBIAN/control" << EOF
Package: walpop
Version: 2.0
Section: utils
Priority: optional
Architecture: amd64
Depends: mpvpaper, ffmpeg, gir1.2-appindicator3-0.1
Maintainer: Rodrigo Pasa <seu.email@example.com>
Description: Gerenciador de Wallpapers Animados para Pop!_OS
 Aplicativo feito em Python e customtkinter.
 Instala automaticamente as dependências do mpvpaper e ffmpeg.
 Permite controlar velocidade, fps e autostart.
EOF

# Construir pacote .deb
echo "📦 Construindo pacote .deb..."
dpkg-deb --build "$DEB_NAME"

echo ""
echo "🔥 SUCESSO! Pacote criado: $DEB_NAME.deb"
echo ""
echo "=========================================================="
echo "COMO INSTALAR AGORA (Você ou seus usuários):"
echo "  Você agora tem um pacote de instalação nativo de Linux."
echo "  Basta dar DOIS CLIQUES no arquivo $DEB_NAME.deb"
echo "  para abrir pela loja, ou instalar pelo terminal:"
echo ""
echo "  sudo apt install ./$DEB_NAME.deb"
echo "=========================================================="
