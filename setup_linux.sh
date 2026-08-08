#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Reproducible Linux setup for the WhatsApp Sales Automation engine with the
# WhatsApp Web (Selenium + Chromium) dispatch backend.
#
# Tested on CachyOS (Arch-based), Chromium 151, Python 3.12 + system Tk 8.6,
# selenium 4.46.
#
# IMPORTANT (fonts): uv's standalone Python bundles a Tk 9.0 built WITHOUT
# fontconfig/Xft, so GUI text renders as tiny 'fixed' bitmap glyphs. The GUI
# therefore needs a Python 3.12 linked against the SYSTEM Tk 8.6. This script
# builds the AUR 'python312' package and uses it user-locally (no root needed
# for the venv), baking the library path into the binary with patchelf.
#
# Steps:
#   1. One-time system packages (needs sudo): chromium, tk, uv, base-devel
#      (for makepkg), and optionally install python312 system-wide instead.
#   2. Build + extract python312 user-locally (or use /usr/bin/python3.12 if
#      you installed the package with pacman).
#   3. Create the .venv with that python and install requirements.
#   4. Print the launch command.
# ---------------------------------------------------------------------------
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")" && pwd)"

echo "[1/4] System packages — Arch/CachyOS (run once, needs sudo):"
echo "      sudo pacman -Sy --needed chromium tk uv base-devel git"
echo "      (Debian/Ubuntu: sudo apt install chromium-browser python3-tk, then"
echo "       install uv from https://docs.astral.sh/uv/ — and you can skip the"
echo "       python312 build below if your distro ships python3.12 with tkinter.)"
echo
read -r -p "Run the pacman install now? [y/N] " -n 1 && echo
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    sudo pacman -Sy --needed chromium tk uv base-devel git
fi

echo "[2/4] Ensuring a system-linked Python 3.12 …"
PYBIN=""
if command -v python3.12 >/dev/null 2>&1; then
    PYBIN="$(command -v python3.12)"
    echo "      Using system python3.12: $PYBIN"
elif [ -x "$HOME/.local/python312/usr/bin/python3.12" ]; then
    PYBIN="$HOME/.local/python312/usr/bin/python3.12"
    echo "      Using previously built user-local python312: $PYBIN"
else
    echo "      Building AUR python312 (links the system Tk 8.6 with fonts) …"
    rm -rf /tmp/python312-aur
    git clone --depth=1 https://aur.archlinux.org/python312.git /tmp/python312-aur
    (cd /tmp/python312-aur && makepkg -s --noconfirm)
    PKG="$(ls /tmp/python312-aur/python312-*.pkg.tar.zst | head -1)"
    echo "      Built $PKG"
    read -r -p "Install it system-wide with sudo? [y/N] (n = use user-locally, no root) " -n 1 && echo
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        sudo pacman -U --noconfirm "$PKG"
        PYBIN="$(command -v python3.12)"
    else
        mkdir -p "$HOME/.local/python312"
        tar -xf "$PKG" -C "$HOME/.local/python312"
        PYBIN="$HOME/.local/python312/usr/bin/python3.12"
        # Bake the libpython path into the binary so no LD_LIBRARY_PATH is needed.
        "$PROJECT/.venv/bin/patchelf" --set-rpath '$ORIGIN/../lib' "$PYBIN" 2>/dev/null \
            || python3 -m pip install --user patchelf 2>/dev/null \
            || echo "NOTE: patchelf not found — set LD_LIBRARY_PATH=$HOME/.local/python312/usr/lib when launching."
    fi
fi

echo "[3/4] Creating the virtualenv with $PYBIN …"
cd "$PROJECT"
uv venv --python "$PYBIN" .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt

echo "[4/4] Done. Run the GUI (WhatsApp Web backend is auto-selected on Linux):"
echo
echo "      cd $PROJECT && .venv/bin/python gui.py"
echo
echo "Or the CLI:  cd $PROJECT && .venv/bin/python main.py"
echo
echo "If text is still tiny, scale the UI:  GUI_SCALE=2.0 .venv/bin/python gui.py"
