#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Reproducible Wine setup for running the WhatsApp Sales Automation GUI on Linux.
#
# Tested on CachyOS (Arch-based), Wine 11.14, Windows Python 3.12.4.
# The GUI, engine, queue building and message preview all work under Wine.
#
# NOTE: the final WhatsApp dispatch step still requires the Windows WhatsApp
# Desktop app, which is MSIX/Store-only and cannot be installed under Wine yet
# (see the README / conversation notes).
# ---------------------------------------------------------------------------
set -euo pipefail

WINE_PY="$HOME/.wine/drive_c/users/$(whoami)/AppData/Local/Programs/Python/Python312/python.exe"
PROJECT="$(cd "$(dirname "$0")" && pwd)"

echo "[1/4] Wine system packages (run this once with sudo):"
echo "      pacman -Sy --noconfirm --needed wine wine-gecko wine-mono winetricks"
echo

echo "[2/4] Initializing Wine prefix + installing Windows Python ..."
wineboot -u || true
mkdir -p "$HOME/Downloads"
PY_INSTALLER="$HOME/Downloads/python-3.12.4-amd64.exe"
if [ ! -f "$PY_INSTALLER" ]; then
    curl -sL -o "$PY_INSTALLER" https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
fi
wine "$PY_INSTALLER" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=0 Include_pip=1

echo "[3/4] Installing project requirements into the Wine Python ..."
cd "$PROJECT"
wine "$WINE_PY" -m pip install --disable-pip-version-check -r requirements.txt

echo "[4/4] Launching the GUI ..."
wine "$WINE_PY" gui.py
