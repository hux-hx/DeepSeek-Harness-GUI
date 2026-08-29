#!/usr/bin/env bash
# Install DeepSeek Harness Desktop for the current user.
# Usage: ./install.sh [prefix]   (default prefix: ~/.local)
set -euo pipefail

APP_ID=deepseek-harness-desktop
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${1:-$HOME/.local}"

for required in python3; do
  command -v "$required" >/dev/null || { echo "missing dependency: $required" >&2; exit 1; }
done

mkdir -p "$PREFIX/bin" "$PREFIX/share/applications"

# The launcher stays in the checkout (single copy, repo-relative assets);
# only a symlink, the icons, and the menu entry are installed.
ln -sfn "$APP_DIR/bin/$APP_ID" "$PREFIX/bin/$APP_ID"

mkdir -p "$PREFIX/share/icons/hicolor"
cp -R "$APP_DIR/share/icons/hicolor/." "$PREFIX/share/icons/hicolor/"

sed "s|__INSTALL_DIR__|$APP_DIR|g" \
  "$APP_DIR/share/applications/$APP_ID.desktop.in" \
  > "$PREFIX/share/applications/$APP_ID.desktop"

command -v update-desktop-database >/dev/null 2>&1 \
  && update-desktop-database "$PREFIX/share/applications" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 \
  && gtk-update-icon-cache -qf "$PREFIX/share/icons/hicolor" || true

# Desktop shortcut for double-click launching (best effort; MATE/GNOME).
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
if [ -d "$DESKTOP_DIR" ]; then
  install -m 644 "$PREFIX/share/applications/$APP_ID.desktop" "$DESKTOP_DIR/"
  if command -v gio >/dev/null 2>&1; then
    gio metadata set -t boolean "$DESKTOP_DIR/$APP_ID.desktop" metadata::trusted true 2>/dev/null || true
  fi
  echo "  $DESKTOP_DIR/$APP_ID.desktop (double-click to open)"
fi

echo "installed:"
echo "  $PREFIX/bin/$APP_ID -> $APP_DIR/bin/$APP_ID"
echo "  $PREFIX/share/applications/$APP_ID.desktop"
echo "  $PREFIX/share/icons/hicolor/{48x48,128x128,256x256,scalable}/apps/$APP_ID.*"
echo "Launch it from the MATE applications menu, or run: $PREFIX/bin/$APP_ID"
