#!/bin/bash
# ─────────────────────────────────────────────
# Walpop v2.0 — Script de Compilação (PyInstaller)
# Cria um executável único sem a janela do terminal
# ─────────────────────────────────────────────

set -e

echo "📦 Preparando para compilar o Walpop..."

# Se existir o venv, ativá-lo para usar as mesmas libs
if [ -d "venv" ]; then
    echo "🐍 Ativando ambiente virtual..."
    source venv/bin/activate
fi

# Instalar o PyInstaller se não estiver instalado
echo "📥 Verificando PyInstaller..."
pip install pyinstaller -q

echo "🔨 Compilando com PyInstaller (Isso pode levar um minuto)..."
# --noconsole / --windowed : Oculta o terminal no executável
# --onefile                : Cria apenas 1 arquivo
# --collect-all            : Garante que os temas e fontes do CustomTkinter sejam empacotados
pyinstaller --noconsole --windowed --onefile \
    --name "Walpop" \
    --collect-all customtkinter \
    walpop.py

echo ""
echo "✅ Compilação concluída!"
echo "📂 Seu executável pronto foi gerado na pasta: 'dist/Walpop'"
echo "Você pode rodar apenas clicando ou com: ./dist/Walpop"
