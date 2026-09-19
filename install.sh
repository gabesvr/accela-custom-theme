#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# ACCELA - Custom Theme & Aesthetic Music Player Installer
# Customizado por: Gabriel Vieira (gabesvr)
# 
# CRÉDITOS ESPECIAIS:
# - CiscoSweater (ciskao) pelo projeto Enter The Wired & instaladores ACCELA:
#   https://github.com/ciscosweater/enter-the-wired
# - Tachibana Labs / Morrenus pelo ACCELA original (Serial Experiments Lain style):
#   https://portal3d.github.io/accela-dist-archive/guide.html
# ==============================================================================

# Cores do terminal
if [ -t 1 ] && [ -t 0 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    MAGENTA='\033[0;35m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    GREEN=''
    RED=''
    YELLOW=''
    CYAN=''
    MAGENTA=''
    BOLD=''
    NC=''
fi

INSTALL_DIR="$HOME/.local/share/ACCELA"
REPO_URL="https://github.com/gabesvr/accela-custom-theme"

echo -e "${MAGENTA}${BOLD}"
cat << 'EOF'
     _    ____ ____ _____ _        _    
    / \  / ___/ ___| ____| |      / \   
   / _ \| |  | |   |  _| | |     / _ \  
  / ___ \ |__| |___| |___| |___ / ___ \ 
 /_/   \_\____\____|_____|_____/_/   \_\
   [ THEME & AESTHETIC MUSIC PLAYER ]
EOF
echo -e "${NC}"
echo -e "${CYAN}================================================================${NC}"
echo -e "${BOLD}CRÉDITOS ESPECIAIS AO CISKÃO (ciscosweater):${NC}"
echo -e "Executando instaladores base do projeto Enter The Wired..."
echo -e "Repositório original: https://github.com/ciscosweater/enter-the-wired"
echo -e "${CYAN}================================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Executar os Scripts Originais do Ciskão (Enter The Wired)
# ------------------------------------------------------------------------------
echo -e "${GREEN}[1/5] Executando dependências do sistema (fix-deps do Ciskão)...${NC}"
curl -fsSL https://raw.githubusercontent.com/ciscosweater/enter-the-wired/main/fix-deps | bash || true

echo ""
echo -e "${GREEN}[2/5] Instalando base oficial do ACCELA (accela do Ciskão)...${NC}"
curl -fsSL https://raw.githubusercontent.com/ciscosweater/enter-the-wired/main/accela | bash

# ------------------------------------------------------------------------------
# 2. Obter Arquivos do Tema Customizado
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}[3/5] Baixando e aplicando Tema Customizado & Music Player...${NC}"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
THEME_DIR="$SCRIPT_DIR/theme"

if [ ! -d "$THEME_DIR" ]; then
    echo "Clonando arquivos do tema do repositório GitHub..."
    TMP_CLONE=$(mktemp -d)
    trap 'rm -rf "$TMP_CLONE"' EXIT
    git clone --depth 1 "$REPO_URL.git" "$TMP_CLONE"
    THEME_DIR="$TMP_CLONE/theme"
fi

# Se não estiver descompactado no squashfs-root, descompactar o AppImage
if [ ! -d "$INSTALL_DIR/squashfs-root" ]; then
    echo "Extraindo AppImage para integração do tema e player..."
    if [ -f "$INSTALL_DIR/ACCELA.AppImage" ]; then
        cp -f "$INSTALL_DIR/ACCELA.AppImage" "$INSTALL_DIR/ACCELA.AppImage.orig"
        chmod +x "$INSTALL_DIR/ACCELA.AppImage.orig"
        (cd "$INSTALL_DIR" && "$INSTALL_DIR/ACCELA.AppImage.orig" --appimage-extract)
    fi
fi

if [ ! -d "$INSTALL_DIR/squashfs-root" ]; then
    echo -e "${RED}[ERRO] Não foi possível extrair o squashfs-root do ACCELA.${NC}"
    exit 1
fi

# Copiar arquivos do tema
echo "Copiando componentes da interface e músicas..."
mkdir -p "$INSTALL_DIR/music"
mkdir -p "$INSTALL_DIR/gifs"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/ui"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/managers"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/sonic"
mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/logo"

# Copiar código modificado
if [ -d "$THEME_DIR/app_files" ]; then
    [ -f "$THEME_DIR/app_files/main.py" ] && cp -f "$THEME_DIR/app_files/main.py" "$INSTALL_DIR/squashfs-root/bin/src/main.py"
    [ -d "$THEME_DIR/app_files/ui" ] && cp -rf "$THEME_DIR/app_files/ui/"* "$INSTALL_DIR/squashfs-root/bin/src/ui/"
    [ -d "$THEME_DIR/app_files/managers" ] && cp -rf "$THEME_DIR/app_files/managers/"* "$INSTALL_DIR/squashfs-root/bin/src/managers/"
    [ -d "$THEME_DIR/app_files/res/sonic" ] && cp -rf "$THEME_DIR/app_files/res/sonic/"* "$INSTALL_DIR/squashfs-root/bin/src/res/sonic/"
    [ -d "$THEME_DIR/app_files/res/logo" ] && cp -rf "$THEME_DIR/app_files/res/logo/"* "$INSTALL_DIR/squashfs-root/bin/src/res/logo/"
fi

# Copiar músicas e GIFs
if [ -d "$THEME_DIR/music" ]; then
    cp -rf "$THEME_DIR/music/"* "$INSTALL_DIR/music/"
fi
if [ -d "$THEME_DIR/gifs" ]; then
    cp -rf "$THEME_DIR/gifs/"* "$INSTALL_DIR/gifs/"
fi

# Instalar dependência de áudio just_playback no venv interno
VENV_PYTHON="$INSTALL_DIR/squashfs-root/bin/.venv/bin/python3"
VENV_PIP="$INSTALL_DIR/squashfs-root/bin/.venv/bin/pip"
if [ -f "$VENV_PYTHON" ]; then
    if ! "$VENV_PYTHON" -c "import just_playback" &>/dev/null; then
        echo "Instalando dependência de áudio 'just_playback' no venv interno..."
        "$VENV_PIP" install just_playback || true
    fi
fi

# ------------------------------------------------------------------------------
# 3. Gravar Configuração do Tema (Pastel Macintosh & Silenciar Sons Nativos)
# ------------------------------------------------------------------------------
echo "Aplicando paleta Pastel Macintosh (#F5F2EB / #8E3B56) e silenciando ruídos..."
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

# ------------------------------------------------------------------------------
# 4. Configurar Janela Flutuante (Window Rules para Hyprland)
# ------------------------------------------------------------------------------
echo -e "${GREEN}[4/5] Configurando regras de janela flutuante (Float)...${NC}"

# Hyprland Lua
if [ -f "$HOME/.config/hypr/hyprland.lua" ]; then
    if ! grep -q "accela-float" "$HOME/.config/hypr/hyprland.lua"; then
        echo "Adicionando regra flutuante no ~/.config/hypr/hyprland.lua..."
        cat >> "$HOME/.config/hypr/hyprland.lua" << 'EOF'

-- ACCELA: sempre flutuante e centralizado (Custom Theme by gabesvr)
hl.window_rule({
    name   = "accela-float",
    match  = { class = "^([aA][cC][cC][eE][lL][aA]|god\\.is\\.in\\.the\\.wired\\.accela)$" },
    float  = true,
    center = true,
    size   = "820 540",
})
hl.window_rule({
    name   = "accela-float-title",
    match  = { title = "^(ACCELA)$" },
    float  = true,
    center = true,
    size   = "820 540",
})
EOF
    fi
# Hyprland Conf
elif [ -f "$HOME/.config/hypr/hyprland.conf" ]; then
    if ! grep -q "class:^(ACCELA" "$HOME/.config/hypr/hyprland.conf"; then
        echo "Adicionando regra flutuante no ~/.config/hypr/hyprland.conf..."
        cat >> "$HOME/.config/hypr/hyprland.conf" << 'EOF'

# ACCELA: sempre flutuante e centralizado (Custom Theme by gabesvr)
windowrulev2 = float, class:^(ACCELA|accela|god\.is\.in\.the\.wired\.accela)$
windowrulev2 = center, class:^(ACCELA|accela|god\.is\.in\.the\.wired\.accela)$
windowrulev2 = size 820 540, class:^(ACCELA|accela|god\.is\.in\.the\.wired\.accela)$
windowrulev2 = float, title:^(ACCELA)$
windowrulev2 = center, title:^(ACCELA)$
EOF
    fi
fi

# ------------------------------------------------------------------------------
# 5. Configurar Lançador e Atalhos
# ------------------------------------------------------------------------------
echo -e "${GREEN}[5/5] Configurando lançador e atalhos do sistema...${NC}"

# Script executável portátil
cat > "$INSTALL_DIR/ACCELA.AppImage" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/squashfs-root/AppRun" "$@"
EOF
chmod +x "$INSTALL_DIR/ACCELA.AppImage"

# Atalho .desktop
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/ACCELA.desktop" << EOF
[Desktop Entry]
Name=ACCELA
Comment=Gerenciador de jogos estilizado (Tema Customizado por gabesvr)
Exec=$HOME/.local/share/ACCELA/ACCELA.AppImage %u
Icon=$HOME/.local/share/ACCELA/squashfs-root/accela.png
Terminal=false
Type=Application
Categories=Utility;Game;
MimeType=x-scheme-handler/accela;
EOF
chmod +x "$HOME/.local/share/applications/ACCELA.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# Ícone do sistema
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
if [ -f "$INSTALL_DIR/squashfs-root/accela.png" ]; then
    cp "$INSTALL_DIR/squashfs-root/accela.png" "$HOME/.local/share/icons/hicolor/256x256/apps/accela.png" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# Wrapper CLI
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/accela" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/ACCELA.AppImage" "$@"
EOF
chmod +x "$HOME/.local/bin/accela"

echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}${BOLD}✨ INSTALAÇÃO DO ACCELA COM TEMA CONCLUÍDA COM SUCESSO! ✨${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "🎮 ${BOLD}Como iniciar:${NC}"
echo -e "  • Menu de aplicativos: ${BOLD}ACCELA${NC}"
echo -e "  • Pelo terminal: ${BOLD}accela${NC}"
echo ""
echo -e "🎵 ${BOLD}Recursos do Tema Customizado:${NC}"
echo -e "  • 100% Flutuante e centralizado por padrão"
echo -e "  • Visual Pastel Macintosh (#F5F2EB) com destaque (#8E3B56)"
echo -e "  • Zumbidos elétricos e ruídos de fundo desativados"
echo -e "  • Music player integrado no rodapé com mascote Yume Nikki"
echo -e "  • Visualizador CAVA em tempo real"
echo ""
echo -e "🙏 ${BOLD}Créditos:${NC}"
echo -e "  • CiscoSweater (ciskao) pelo projeto Enter The Wired & instaladores"
echo -e "  • Tachibana Labs / Morrenus pelo ACCELA original"
echo -e "  • gabesvr pelo tema, player e customizações"
echo ""
