#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Aplica o tema customizado do gabesvr em um ACCELA já instalado.
# Também é chamado pelo install.sh depois de instalar o ACCELA e o SLSsteam.
# Pode ser executado quantas vezes quiser: as configurações do usuário são mantidas.
# ==============================================================================

if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    GREEN='' RED='' YELLOW='' CYAN='' NC=''
fi

INSTALL_DIR="$HOME/.local/share/ACCELA"
SRC_DIR="$INSTALL_DIR/squashfs-root/bin/src"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
THEME_DIR="$SCRIPT_DIR/theme"
CONF_DIR="$HOME/.config/Tachibana Labs"
CONF_FILE="$CONF_DIR/ACCELA.conf"

warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}Aplicador de Tema ACCELA (Customizado por gabesvr)${NC}"
echo -e "${CYAN}====================================================${NC}"

if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}[ERRO] ACCELA não encontrado em $INSTALL_DIR.${NC}"
    echo "Execute primeiro o install.sh para realizar a instalação completa."
    exit 1
fi

# ------------------------------------------------------------------------------
# Extrair o AppImage (o tema precisa dos arquivos soltos em squashfs-root)
# ------------------------------------------------------------------------------
if [ ! -d "$INSTALL_DIR/squashfs-root" ] && [ -f "$INSTALL_DIR/ACCELA.AppImage" ]; then
    echo "Extraindo AppImage para possibilitar a aplicação do tema..."
    cp -f "$INSTALL_DIR/ACCELA.AppImage" "$INSTALL_DIR/ACCELA.AppImage.orig"
    chmod +x "$INSTALL_DIR/ACCELA.AppImage.orig"
    (cd "$INSTALL_DIR" && "$INSTALL_DIR/ACCELA.AppImage.orig" --appimage-extract >/dev/null)
fi

if [ ! -d "$SRC_DIR" ]; then
    echo -e "${RED}[ERRO] Não foi possível encontrar $SRC_DIR.${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# Copiar código, músicas e GIFs do tema
# ------------------------------------------------------------------------------
echo "Copiando componentes da interface, músicas e GIFs..."
mkdir -p "$INSTALL_DIR/music" "$INSTALL_DIR/gifs"
cp -rf "$THEME_DIR/app_files/." "$SRC_DIR/"
cp -rf "$THEME_DIR/music/." "$INSTALL_DIR/music/"
cp -rf "$THEME_DIR/gifs/." "$INSTALL_DIR/gifs/"

# ------------------------------------------------------------------------------
# Dependências do player: just_playback (venv interno) e cava (sistema)
# ------------------------------------------------------------------------------
VENV_PYTHON="$INSTALL_DIR/squashfs-root/bin/.venv/bin/python3"
if [ -f "$VENV_PYTHON" ] && ! "$VENV_PYTHON" -c "import just_playback" &>/dev/null; then
    echo "Instalando dependência de áudio 'just_playback' no venv interno..."
    "$VENV_PYTHON" -m pip install --quiet just_playback \
        || warn "Não foi possível instalar just_playback; o player de música não vai funcionar."
fi

if ! command -v cava &>/dev/null; then
    echo "Instalando cava (visualizador de áudio do player)..."
    if command -v pacman &>/dev/null; then
        sudo pacman -S --needed --noconfirm cava
    elif command -v apt-get &>/dev/null; then
        sudo apt-get install -y cava
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y cava
    elif command -v zypper &>/dev/null; then
        sudo zypper --non-interactive install cava
    elif command -v xbps-install &>/dev/null; then
        sudo xbps-install -y cava
    else
        false
    fi || warn "Não foi possível instalar o cava; o visualizador do player ficará vazio."
fi

# ------------------------------------------------------------------------------
# Configuração do ACCELA: mescla as chaves do tema sem apagar as do usuário
# ------------------------------------------------------------------------------
# set_conf_key <chave> <valor> <force|default>
#   force   -> sobrescreve o valor atual
#   default -> só grava se a chave ainda não existir
set_conf_key() {
    local key="$1" value="$2" mode="$3"
    if grep -q "^${key}=" "$CONF_FILE"; then
        if [ "$mode" = "force" ]; then
            local tmp
            tmp=$(mktemp)
            awk -v k="$key" -v v="$value" 'index($0, k "=") == 1 { print k "=" v; next } { print }' \
                "$CONF_FILE" > "$tmp"
            cat "$tmp" > "$CONF_FILE"
            rm -f "$tmp"
        fi
    else
        local tmp
        tmp=$(mktemp)
        awk -v line="${key}=${value}" '{ print } $0 == "[General]" { print line }' "$CONF_FILE" > "$tmp"
        cat "$tmp" > "$CONF_FILE"
        rm -f "$tmp"
    fi
}

echo "Aplicando configuração do tema..."
mkdir -p "$CONF_DIR"
touch "$CONF_FILE"
if ! grep -q '^\[General\]' "$CONF_FILE"; then
    tmp=$(mktemp)
    { echo "[General]"; cat "$CONF_FILE"; } > "$tmp"
    cat "$tmp" > "$CONF_FILE"
    rm -f "$tmp"
fi

# Na primeira aplicação o visual do tema é imposto; depois disso as escolhas
# que o usuário fizer nas configurações do ACCELA são respeitadas.
if grep -q '^gabesvr_theme_applied=true' "$CONF_FILE"; then
    THEME_MODE=default
else
    THEME_MODE=force
fi

set_conf_key accent_color "#8E3B56" "$THEME_MODE"
set_conf_key background_color "#F5F2EB" "$THEME_MODE"
set_conf_key user_accent_color "#8E3B56" "$THEME_MODE"
set_conf_key user_background_color "#F5F2EB" "$THEME_MODE"
set_conf_key play_50hz_hum false "$THEME_MODE"
set_conf_key play_etw false "$THEME_MODE"
set_conf_key play_lall false "$THEME_MODE"
set_conf_key hum_volume 0 "$THEME_MODE"
set_conf_key effects_volume 0 "$THEME_MODE"

set_conf_key master_volume 80 default
set_conf_key auto_skip_single_choice true default
set_conf_key library_mode true default
set_conf_key sls_config_management true default
set_conf_key prompt_steam_restart true default
set_conf_key max_downloads 16 default
set_conf_key use_steamless true default
set_conf_key gabesvr_theme_applied true force

# ------------------------------------------------------------------------------
# SLSsteam: garantir PlayNotOwnedGames e API habilitados
# ------------------------------------------------------------------------------
SLS_CONF="$HOME/.config/SLSsteam/config.yaml"
if [ -f "$SLS_CONF" ]; then
    if ! grep -qi "playnotownedgames" "$SLS_CONF"; then
        sed -i '/DisableFamilyShareLock:/a \\n# Enables playing of not owned games\nPlayNotOwnedGames: yes\nplayNotOwnedGames: yes' "$SLS_CONF"
    else
        sed -i -E 's/^[# ]*([Pp]lay[Nn]ot[Oo]wned[Gg]ames\s*:\s*).*/\1yes/' "$SLS_CONF"
    fi
    sed -i -E 's/^[# ]*(API\s*:\s*).*/\1yes/' "$SLS_CONF"
fi

# ------------------------------------------------------------------------------
# Hyprland: janela flutuante e centralizada
# ------------------------------------------------------------------------------
if [ -f "$HOME/.config/hypr/hyprland.lua" ]; then
    if ! grep -q "accela-float" "$HOME/.config/hypr/hyprland.lua"; then
        echo "Adicionando regra flutuante no hyprland.lua..."
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
elif [ -f "$HOME/.config/hypr/hyprland.conf" ]; then
    if ! grep -q "class:^(ACCELA" "$HOME/.config/hypr/hyprland.conf"; then
        echo "Adicionando regra flutuante no hyprland.conf..."
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
# Lançador, atalho .desktop, ícone e comando `accela`
# ------------------------------------------------------------------------------
cat > "$INSTALL_DIR/ACCELA.AppImage" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/squashfs-root/AppRun" "$@"
EOF
chmod +x "$INSTALL_DIR/ACCELA.AppImage"

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

if [ -f "$INSTALL_DIR/squashfs-root/accela.png" ]; then
    mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
    cp "$INSTALL_DIR/squashfs-root/accela.png" "$HOME/.local/share/icons/hicolor/256x256/apps/accela.png" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/accela" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/ACCELA.AppImage" "$@"
EOF
chmod +x "$HOME/.local/bin/accela"

echo -e "${GREEN}✓ Tema aplicado com sucesso no ACCELA!${NC}"
