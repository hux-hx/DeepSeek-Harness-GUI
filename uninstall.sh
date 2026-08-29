#!/usr/bin/env bash
# Uninstall DeepSeek Harness Desktop (reverses install.sh).
# Usage: ./uninstall.sh [prefix]   (default prefix: ~/.local)
set -euo pipefail

APP_ID=deepseek-harness-desktop
PREFIX="${1:-$HOME/.local}"

rm -f "$PREFIX/bin/$APP_ID"
rm -f "$PREFIX/share/applications/$APP_ID.desktop"
rm -f "${XDG_DESKTOP_DIR:-$HOME/Desktop}/$APP_ID.desktop"
rm -f "$PREFIX/share/icons/hicolor/48x48/apps/$APP_ID.png" \
      "$PREFIX/share/icons/hicolor/128x128/apps/$APP_ID.png" \
      "$PREFIX/share/icons/hicolor/256x256/apps/$APP_ID.png" \
      "$PREFIX/share/icons/hicolor/scalable/apps/$APP_ID.svg"

command -v update-desktop-database >/dev/null 2>&1 \
  && update-desktop-database "$PREFIX/share/applications" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 \
  && gtk-update-icon-cache -qf "$PREFIX/share/icons/hicolor" || true

echo "uninstalled. App data (sessions, DSH home) is kept at:"
echo "  ${XDG_DATA_HOME:-$HOME/.local/share}/$APP_ID/"
echo "Remove it manually if you no longer need it."
