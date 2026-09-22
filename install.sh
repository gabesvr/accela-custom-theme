#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# USOLINUX - Instalador (ACCELA + SLSsteam + tema dreamy + music player)
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
REPO_URL="https://github.com/gabesvr/usolinux"

echo -e "${MAGENTA}${BOLD}"
cat << 'EOF'
  _   _ ____   ___  _     ___ _   _ _   ___  __
 | | | / ___| / _ \| |   |_ _| \ | | | | \ \/ /
 | | | \___ \| | | | |    | ||  \| | | | |\  /
 | |_| |___) | |_| | |___ | || |\  | |_| |/  \
  \___/|____/ \___/|_____|___|_| \_|\___//_/\_\
      [ baseado no ACCELA • tema by gabesvr ]
EOF
echo -e "${NC}"
echo -e "${CYAN}================================================================${NC}"
echo -e "${BOLD}CRÉDITOS ESPECIAIS AO CISKÃO (ciscosweater):${NC}"
echo -e "Executando instaladores base do projeto Enter The Wired..."
echo -e "Repositório original: https://github.com/ciscosweater/enter-the-wired"
echo -e "${CYAN}================================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# 1. Executar os Scripts Originais do Ciskão (Enter The Wired)
# ------------------------------------------------------------------------------
echo -e "${GREEN}[1/4] Executando dependências do sistema (fix-deps do Ciskão)...${NC}"
curl -fsSL https://raw.githubusercontent.com/ciscosweater/enter-the-wired/main/fix-deps | bash || true

echo ""
echo -e "${GREEN}[2/4] Instalando base oficial do ACCELA (accela do Ciskão)...${NC}"
curl -fsSL https://raw.githubusercontent.com/ciscosweater/enter-the-wired/main/accela | bash

# ------------------------------------------------------------------------------
# 2. Instalação e Configuração Automática do SLSsteam (100% Automatizado)
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}[3/4] Instalando e configurando SLSsteam automaticamente...${NC}"

SLS_TMP=$(mktemp -d)
TMP_CLONE=""
trap 'rm -rf "$SLS_TMP" ${TMP_CLONE:+"$TMP_CLONE"}' EXIT

SLS_URL=$(curl -fsSL https://api.github.com/repos/AceSLS/SLSsteam/releases/latest 2>/dev/null | grep -o 'https://[^"]*SLSsteam-Any-release\.7z' | head -n 1 || true)
if [ -z "$SLS_URL" ]; then
    SLS_URL="https://github.com/AceSLS/SLSsteam/releases/download/20260903114323/SLSsteam-Any-release.7z"
fi

echo "Baixando SLSsteam ($SLS_URL)..."
curl -fsSL "$SLS_URL" -o "$SLS_TMP/SLSsteam-Any-release.7z"

echo "Extraindo arquivos do SLSsteam..."
bsdtar -xf "$SLS_TMP/SLSsteam-Any-release.7z" -C "$SLS_TMP"

mkdir -p "$HOME/.config/fish/conf.d"
(cd "$SLS_TMP" && chmod +x setup.sh && ./setup.sh install)

if [ -d "$HOME/.config/fish" ]; then
    echo 'export PATH="$HOME/.local/share/SLSsteam/path:$PATH"' > "$HOME/.config/fish/conf.d/SLSsteam.fish"
fi

echo "Configurando ~/.config/SLSsteam/config.yaml (PlayNotOwnedGames: yes & API: yes)..."
mkdir -p "$HOME/.config/SLSsteam"
if [ ! -f "$HOME/.config/SLSsteam/config.yaml" ] && [ -f "$SLS_TMP/res/config.yaml" ]; then
    cp "$SLS_TMP/res/config.yaml" "$HOME/.config/SLSsteam/config.yaml"
fi

# PlayNotOwnedGames e API são ativados pelo apply-theme.sh (etapa 4)

# ------------------------------------------------------------------------------
# 3. Obter os arquivos do tema e aplicar (apply-theme.sh)
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}[4/4] Aplicando tema, music player, configuração, janela flutuante e atalhos...${NC}"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")" && pwd)"

# Rodando via `curl | bash` não há arquivos locais: clona o repositório
if [ ! -f "$SCRIPT_DIR/apply-theme.sh" ] || [ ! -d "$SCRIPT_DIR/theme" ]; then
    echo "Clonando arquivos do tema do repositório GitHub..."
    TMP_CLONE=$(mktemp -d)
    git clone --depth 1 "$REPO_URL.git" "$TMP_CLONE"
    SCRIPT_DIR="$TMP_CLONE"
fi

bash "$SCRIPT_DIR/apply-theme.sh"

echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}${BOLD}✨ USOLINUX INSTALADO COM SUCESSO! ✨${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "🎮 ${BOLD}Como iniciar:${NC}"
echo -e "  • Menu de aplicativos: ${BOLD}USOLINUX${NC}"
echo -e "  • Pelo terminal: ${BOLD}usolinux${NC}"
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
