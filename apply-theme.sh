#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Script para Aplicar o Tema Customizado do gabesvr em um ACCELA já instalado
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.local/share/ACCELA"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
THEME_DIR="$SCRIPT_DIR/theme"

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}Aplicador de Tema ACCELA (Customizado por gabesvr)${NC}"
echo -e "${CYAN}====================================================${NC}"

if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}[ERRO] ACCELA não encontrado em $INSTALL_DIR.${NC}"
    echo "Execute primeiro o install.sh para realizar a instalação completa."
    exit 1
fi

# Se não tiver squashfs-root mas tiver AppImage, extrair
if [ ! -d "$INSTALL_DIR/squashfs-root" ] && [ -f "$INSTALL_DIR/ACCELA.AppImage" ]; then
    echo "Extraindo AppImage para possibilitar a aplicação do tema..."
    cp -f "$INSTALL_DIR/ACCELA.AppImage" "$INSTALL_DIR/ACCELA.AppImage.orig"
    (cd "$INSTALL_DIR" && "$INSTALL_DIR/ACCELA.AppImage.orig" --appimage-extract)
fi

echo "Copiando componentes da interface e músicas..."
mkdir -p "$INSTALL_DIR/music"
mkdir -p "$INSTALL_DIR/gifs"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/ui"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/managers"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/sonic"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/logo"

if [ -d "$THEME_DIR/app_files" ]; then
    [ -f "$THEME_DIR/app_files/main.py" ] && cp -f "$THEME_DIR/app_files/main.py" "$INSTALL_DIR/squashfs-root/bin/src/main.py"
    [ -d "$THEME_DIR/app_files/ui" ] && cp -rf "$THEME_DIR/app_files/ui/"* "$INSTALL_DIR/squashfs-root/bin/src/ui/"
    [ -d "$THEME_DIR/app_files/managers" ] && cp -rf "$THEME_DIR/app_files/managers/"* "$INSTALL_DIR/squashfs-root/bin/src/managers/"
    [ -d "$THEME_DIR/app_files/res/sonic" ] && cp -rf "$THEME_DIR/app_files/res/sonic/"* "$INSTALL_DIR/squashfs-root/bin/src/res/sonic/"
    [ -d "$THEME_DIR/app_files/res/logo" ] && cp -rf "$THEME_DIR/app_files/res/logo/"* "$INSTALL_DIR/squashfs-root/bin/src/res/logo/"
fi

cp -rf "$THEME_DIR/music/"* "$INSTALL_DIR/music/"
cp -rf "$THEME_DIR/gifs/"* "$INSTALL_DIR/gifs/"

# Instalar just_playback no venv interno
VENV_PIP="$INSTALL_DIR/squashfs-root/bin/.venv/bin/pip"
VENV_PYTHON="$INSTALL_DIR/squashfs-root/bin/.venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    if ! "$VENV_PYTHON" -c "import just_playback" &>/dev/null; then
        echo "Instalando dependência de áudio 'just_playback' no venv interno..."
        "$VENV_PIP" install just_playback || true
    fi
fi

# Configurar cores pastel e silenciar zumbido de fundo
echo "Aplicando configuração de cores e silenciando zumbido de fundo..."
CONF_DIR="$HOME/.config/Tachibana Labs"
mkdir -p "$CONF_DIR"

cat > "$CONF_DIR/ACCELA.conf" << 'EOF'
[General]
accent_color=#8E3B56
background_color=#F5F2EB
user_accent_color=#8E3B56
user_background_color=#F5F2EB
font_family=Comfortaa
play_50hz_hum=false
play_etw=false
play_lall=false
hum_volume=0
effects_volume=0
master_volume=80
auto_skip_single_choice=true
library_mode=true
max_downloads=16
use_steamless=true
EOF

# Garantir executável
cat > "$INSTALL_DIR/ACCELA.AppImage" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/squashfs-root/AppRun" "$@"
EOF
chmod +x "$INSTALL_DIR/ACCELA.AppImage"

echo -e "${GREEN}✓ Tema aplicado com sucesso no ACCELA!${NC}"
