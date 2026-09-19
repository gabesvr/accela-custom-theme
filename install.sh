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
OFFICIAL_DEPS_URL="https://github.com/ciscosweater/enter-the-wired/releases/download/latest/deps.tar.gz"

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
echo -e "Baseado no instalador e utilitários do projeto Enter The Wired"
echo -e "Repositório original: https://github.com/ciscosweater/enter-the-wired"
echo -e "${CYAN}================================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Detecção da Distribuição Linux
# ------------------------------------------------------------------------------
detect_distro_family() {
    if [ -f /etc/os-release ]; then
        source /etc/os-release
    fi

    local ID_VAL="${ID:-}"
    local ID_LIKE_VAL="${ID_LIKE:-}"

    if [[ "$ID_VAL" == "arch" || "$ID_VAL" == "cachyos" || "$ID_VAL" == "endeavouros" || "$ID_VAL" == "manjaro" || "$ID_LIKE_VAL" =~ "arch" ]] || [ -f "/etc/arch-release" ]; then
        echo "arch"
        return 0
    fi

    if [[ "$ID_VAL" == "fedora" || "$ID_VAL" == "bazzite" || "$ID_VAL" == "rhel" || "$ID_VAL" == "centos" || "$ID_LIKE_VAL" =~ "fedora" ]]; then
        echo "fedora"
        return 0
    fi

    if [[ "$ID_VAL" == "debian" || "$ID_VAL" == "ubuntu" || "$ID_VAL" == "linuxmint" || "$ID_VAL" == "pop" || "$ID_LIKE_VAL" =~ "debian" || "$ID_LIKE_VAL" =~ "ubuntu" ]]; then
        echo "debian"
        return 0
    fi

    if [[ "$ID_VAL" =~ opensuse || "$ID_LIKE_VAL" =~ opensuse ]]; then
        echo "opensuse"
        return 0
    fi

    if [[ "$ID_VAL" == "void" ]]; then
        echo "void"
        return 0
    fi

    echo "unknown"
}

# ------------------------------------------------------------------------------
# 2. Instalação de Dependências
# ------------------------------------------------------------------------------
install_system_deps() {
    local FAMILY
    FAMILY=$(detect_distro_family)
    echo -e "${GREEN}[1/4] Verificando dependências do sistema (${FAMILY})...${NC}"

    case "$FAMILY" in
        arch)
            local PKGS=("python" "xcb-util-cursor" "libnotify" "git" "tar" "curl")
            local MISSING=()
            for p in "${PKGS[@]}"; do
                if ! pacman -Q "$p" &>/dev/null; then
                    MISSING+=("$p")
                fi
            done

            # Verificar 7zip ou p7zip
            if ! pacman -Q 7zip &>/dev/null && ! pacman -Q p7zip &>/dev/null; then
                MISSING+=("7zip")
            fi

            if [ ${#MISSING[@]} -gt 0 ]; then
                echo -e "${YELLOW}Instalando pacotes necessários: ${MISSING[*]}${NC}"
                sudo pacman -S --noconfirm "${MISSING[@]}" || true
            else
                echo -e "${GREEN}✓ Todas as dependências do sistema já estão instaladas.${NC}"
            fi
            ;;
        debian)
            sudo apt update -y 2>/dev/null || true
            sudo apt-get install -y python3 python3-venv libxcb-cursor0 libnotify-bin git p7zip-full curl tar || true
            ;;
        fedora)
            sudo dnf install -y --setopt=install_weak_deps=False python3 libxcb-cursor libnotify git p7zip p7zip-plugins curl tar || true
            ;;
        opensuse)
            sudo zypper install -y python3 libxcb-cursor0 libnotify-tools git p7zip-full curl tar || true
            ;;
        void)
            sudo xbps-install -y python3 xcb-util-cursor libnotify git 7zip curl tar || true
            ;;
        *)
            echo -e "${YELLOW}[AVISO] Distribuição não identificada diretamente. Verifique se possui python3, git, curl e xcb-util instalados.${NC}"
            ;;
    esac
}

# ------------------------------------------------------------------------------
# 3. Preparação do ACCELA e Extração
# ------------------------------------------------------------------------------
setup_accela_base() {
    echo -e "${GREEN}[2/4] Preparando base do ACCELA...${NC}"

    local LOCAL_ARCHIVE=""
    # Procura arquivo local meutemaACCELA se existir
    if [ -f "$HOME/Downloads/meutemaACCELA.tar.gz" ]; then
        LOCAL_ARCHIVE="$HOME/Downloads/meutemaACCELA.tar.gz"
    fi

    if [ -n "$LOCAL_ARCHIVE" ]; then
        echo -e "${CYAN}Arquivo completo encontrado em: $LOCAL_ARCHIVE${NC}"
        echo "Extraindo ACCELA e componentes..."
        mkdir -p "$HOME/.local/share"
        tar -xzf "$LOCAL_ARCHIVE" -C "$HOME/.local/share/"
        echo -e "${GREEN}✓ ACCELA extraído com sucesso!${NC}"
    else
        # Se não tiver o tarball gigante local, baixa a base oficial do ciskao
        if [ ! -d "$INSTALL_DIR/squashfs-root" ]; then
            echo -e "${YELLOW}Instalação local não encontrada. Baixando base oficial do ACCELA...${NC}"
            local TMP_DIR
            TMP_DIR=$(mktemp -d)
            trap 'rm -rf "$TMP_DIR"' EXIT

            curl -fsSL --retry 3 --retry-delay 2 -o "$TMP_DIR/deps.tar.gz" "$OFFICIAL_DEPS_URL"
            mkdir -p "$TMP_DIR/extracted"
            tar -xzf "$TMP_DIR/deps.tar.gz" -C "$TMP_DIR/extracted"

            if [ -f "$TMP_DIR/extracted/ACCELAINSTALL" ]; then
                chmod +x "$TMP_DIR/extracted/ACCELAINSTALL"
                (cd "$TMP_DIR/extracted" && ./ACCELAINSTALL)
            fi

            # Extrair AppImage se ainda não tiver o squashfs-root
            if [ -f "$INSTALL_DIR/ACCELA.AppImage" ] && [ ! -d "$INSTALL_DIR/squashfs-root" ]; then
                echo "Extraindo AppImage para customização..."
                mv "$INSTALL_DIR/ACCELA.AppImage" "$INSTALL_DIR/ACCELA.AppImage.orig"
                (cd "$INSTALL_DIR" && "$INSTALL_DIR/ACCELA.AppImage.orig" --appimage-extract)
            fi
        fi
    fi
}

# ------------------------------------------------------------------------------
# 4. Aplicação do Tema Personalizado & Músicas
# ------------------------------------------------------------------------------
apply_theme_files() {
    echo -e "${GREEN}[3/4] Aplicando tema customizado, player de música e recursos...${NC}"

    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
    local THEME_DIR="$SCRIPT_DIR/theme"

    # Se estiver rodando via curl | bash sem repositório local clonado
    if [ ! -d "$THEME_DIR" ]; then
        echo "Baixando arquivos do tema do GitHub..."
        local TMP_CLONE
        TMP_CLONE=$(mktemp -d)
        git clone --depth 1 "$REPO_URL.git" "$TMP_CLONE"
        THEME_DIR="$TMP_CLONE/theme"
    fi

    if [ ! -d "$THEME_DIR" ]; then
        echo -e "${RED}[ERRO] Pasta de temas não encontrada.${NC}"
        return 1
    fi

    # Criar pastas de destino
    mkdir -p "$INSTALL_DIR/music"
    mkdir -p "$INSTALL_DIR/gifs"
    mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/ui"
    mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/sonic"
    mkdir -p "$INSTALL_DIR/squashfs-root/bin/src/res/logo"

    # 1. Copiar UI e código customizado
    if [ -d "$THEME_DIR/app_files/ui" ]; then
        cp -rf "$THEME_DIR/app_files/ui/"* "$INSTALL_DIR/squashfs-root/bin/src/ui/"
    fi

    # 2. Copiar recursos Sonic e Logos
    if [ -d "$THEME_DIR/app_files/res/sonic" ]; then
        cp -rf "$THEME_DIR/app_files/res/sonic/"* "$INSTALL_DIR/squashfs-root/bin/src/res/sonic/"
    fi
    if [ -d "$THEME_DIR/app_files/res/logo" ]; then
        cp -rf "$THEME_DIR/app_files/res/logo/"* "$INSTALL_DIR/squashfs-root/bin/src/res/logo/"
    fi

    # 3. Copiar músicas e gifs
    if [ -d "$THEME_DIR/music" ]; then
        cp -rf "$THEME_DIR/music/"* "$INSTALL_DIR/music/"
    fi
    if [ -d "$THEME_DIR/gifs" ]; then
        cp -rf "$THEME_DIR/gifs/"* "$INSTALL_DIR/gifs/"
    fi

    # 4. Instalar biblioteca de áudio just_playback no venv interno se necessário
    local VENV_PYTHON="$INSTALL_DIR/squashfs-root/bin/.venv/bin/python3"
    local VENV_PIP="$INSTALL_DIR/squashfs-root/bin/.venv/bin/pip"

    if [ -f "$VENV_PYTHON" ]; then
        if ! "$VENV_PYTHON" -c "import just_playback" &>/dev/null; then
            echo "Instalando biblioteca de áudio 'just_playback' no ambiente do ACCELA..."
            "$VENV_PIP" install just_playback || true
        fi
    fi

    echo -e "${GREEN}✓ Tema, player de áudio e assets aplicados com sucesso!${NC}"
}

# ------------------------------------------------------------------------------
# 5. Configuração de Atalhos e Executável
# ------------------------------------------------------------------------------
setup_desktop_and_cli() {
    echo -e "${GREEN}[4/4] Configurando lançador e atalhos do sistema...${NC}"

    # Script lançador universal
    cat > "$INSTALL_DIR/ACCELA.AppImage" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/squashfs-root/AppRun" "$@"
EOF
    chmod +x "$INSTALL_DIR/ACCELA.AppImage"

    # Atalho Desktop
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

    # Wrapper CLI no PATH
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/accela" << 'EOF'
#!/usr/bin/env bash
exec "$HOME/.local/share/ACCELA/ACCELA.AppImage" "$@"
EOF
    chmod +x "$HOME/.local/bin/accela"

    echo -e "${GREEN}✓ Lançador (.desktop) e comando terminal 'accela' configurados!${NC}"
}

# ------------------------------------------------------------------------------
# Execução Principal
# ------------------------------------------------------------------------------
install_system_deps
setup_accela_base
apply_theme_files
setup_desktop_and_cli

echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}${BOLD}✨ INSTALAÇÃO DO ACCELA COM TEMA CONCLUÍDA COM SUCESSO! ✨${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "🎮 ${BOLD}Como iniciar:${NC}"
echo -e "  • Pelo menu de aplicativos: Procure por ${BOLD}ACCELA${NC}"
echo -e "  • Pelo terminal: Digite ${BOLD}accela${NC}"
echo ""
echo -e "🎵 ${BOLD}Recursos do Tema Gabesvr:${NC}"
echo -e "  • Player de áudio estético integrado na barra inferior"
echo -e "  • Mascote dançante Yume Nikki sincronizado com a música"
echo -e "  • Suporte a espectro de áudio em tempo real (CAVA)"
echo -e "  • Playlist personalizada em: ${CYAN}~/.local/share/ACCELA/music/${NC}"
echo -e "  • GIFs estilizados em: ${CYAN}~/.local/share/ACCELA/gifs/${NC}"
echo ""
echo -e "🙏 ${BOLD}Créditos:${NC}"
echo -e "  • Ciskão (ciscosweater) pelo projeto Enter The Wired"
echo -e "  • Tachibana Labs pelo ACCELA original"
echo -e "  • gabesvr pelo tema, player e customizações"
echo ""
