#!/usr/bin/env bash
# Desenvolvimento: copia só o código do tema para o ACCELA instalado, sem mexer
# na configuração, músicas ou dependências. Uso: ./dev-sync.sh [--run]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
SRC_DIR="$HOME/.local/share/ACCELA/squashfs-root/bin/src"
cp -rf "$SCRIPT_DIR/theme/app_files/." "$SRC_DIR/"
cp -rf "$SCRIPT_DIR/theme/gifs/." "$HOME/.local/share/ACCELA/gifs/"
echo "Tema sincronizado em $SRC_DIR"
if [ "${1:-}" = "--run" ]; then
    exec "$HOME/.local/share/ACCELA/ACCELA.AppImage"
fi
