#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Script para Aplicar o Tema Customizado do gabesvr em um ACCELA já instalado
# ==============================================================================

# Cores
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
    mv "$INSTALL_DIR/ACCELA.AppImage" "$INSTALL_DIR/ACCELA.AppImage.orig"
    (cd "$INSTALL_DIR" && "$INSTALL_DIR/ACCELA.AppImage.orig" --appimage-extract)
fi

echo "Copiando arquivos do tema..."
mkdir -p "$INSTALL_DIR/music"
mkdir -p "$INSTALL_DIR/gifs"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/ui"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/sonic"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/logo"

cp -rf "$THEME_DIR/app_files/ui/"* "$INSTALL_DIR/squashfs-root/bin/src/ui/"
cp -rf "$THEME_DIR/app_files/res/sonic/"* "$INSTALL_DIR/squashfs-root/bin/src/res/sonic/"
cp -rf "$THEME_DIR/app_files/res/logo/"* "$INSTALL_DIR/squashfs-root/bin/src/res/logo/"
cp -rf "$THEME_DIR/music/"* "$INSTALL_DIR/music/"
cp -rf "$THEME_DIR/gifs/"* "$INSTALL_DIR/gifs/"

# Instalar just_playback no venv
VENV_PIP="$INSTALL_DIR/squashfs-root/bin/.venv/bin/pip"
VENV_PYTHON="$INSTALL_DIR/squashfs-root/bin/.venv/bin/python3"
if [ -f "$VENV_PYTHON" ]; then
    if ! "$VENV_PYTHON" -c "import just_playback" &>/dev/null; then
        echo "Instalando dependência de áudio 'just_playback' no venv..."
        "$VENV_PIP" install just_playback || true
    fi
fi

# Garantir executável
cat > "$INSTALL_DIR/ACCELA.AppImage" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/squashfs-root/AppRun" "$@"
EOF
chmod +x "$INSTALL_DIR/ACCELA.AppImage"

echo -e "${GREEN}✓ Tema aplicado com sucesso no ACCELA!${NC}"
