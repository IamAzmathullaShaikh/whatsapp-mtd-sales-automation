#!/usr/bin/env bash
# ============================================================
#  Build the Linux release: dist/WhatsAppMTD-<arch>.AppImage
#  A single file — download, chmod +x, double-click (or run).
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "${PYBIN:-}" ]; then
  :  # caller chose the interpreter
elif [ -x ".venv/bin/python" ]; then
  PYBIN=".venv/bin/python"
else
  PYBIN="python3"
fi
ARCH="$(uname -m)"

echo "[1/4] Ensuring PyInstaller in ${PYBIN} ..."
if "$PYBIN" -c "import PyInstaller" 2>/dev/null; then
  echo "      PyInstaller already available."
elif "$PYBIN" -m pip install -q pyinstaller 2>/dev/null; then
  :
else
  uv pip install --python "$PYBIN" pyinstaller
fi

echo "[2/4] Building the bundled binary with PyInstaller ..."
"$PYBIN" -m PyInstaller --noconfirm WhatsAppMTD.spec

echo "[3/4] Assembling the AppDir ..."
rm -rf build/AppDir
mkdir -p build/AppDir/usr/bin build/AppDir/usr/share/applications build/AppDir/usr/share/icons/hicolor/64x64/apps
cp dist/WhatsAppMTD build/AppDir/usr/bin/WhatsAppMTD

# Minimal launcher — the PyInstaller onefile binary is a normal executable.
cat > build/AppDir/AppRun <<'EOF'
#!/bin/bash
SELF="$(dirname "$(readlink -f "$0")")"
exec "$SELF/usr/bin/WhatsAppMTD" "$@"
EOF
chmod +x build/AppDir/AppRun

cat > build/AppDir/usr/share/applications/whatsapp-mtd.desktop <<'EOF'
[Desktop Entry]
Name=WhatsApp MTD Sales Automation
Comment=Daily sales progress reports over WhatsApp
Exec=WhatsAppMTD
Icon=whatsapp-mtd
Type=Application
Categories=Office;
Terminal=false
EOF
# appimagetool also wants the .desktop at the AppDir root.
cp build/AppDir/usr/share/applications/whatsapp-mtd.desktop build/AppDir/whatsapp-mtd.desktop

# Generate a simple icon (solid WhatsApp-green PNG) so appimagetool is happy.
"$PYBIN" - <<'EOF'
import os, struct, zlib
w = h = 256
raw = b"".join(b"\x00" + b"".join(bytes((0x25, 0xd3, 0x66, 255)) for _ in range(w)) for _ in range(h))
def chunk(tag, data):
    c = tag + data
    return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw))
       + chunk(b"IEND", b""))
for path in ("build/AppDir/whatsapp-mtd.png",
             "build/AppDir/usr/share/icons/hicolor/64x64/apps/whatsapp-mtd.png"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(png)
EOF

echo "[4/4] Wrapping with appimagetool ..."
ROOT="$(pwd)"
TOOL="${ROOT}/build/appimagetool"
if [ ! -x "$TOOL" ]; then
  curl -L --fail -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  chmod +x "$TOOL"
fi
# --appimage-extract-and-run avoids needing FUSE on the build machine. It
# changes CWD to the extracted runtime, so pass ABSOLUTE paths only.
"$TOOL" --appimage-extract-and-run "${ROOT}/build/AppDir" "${ROOT}/dist/WhatsAppMTD-${ARCH}.AppImage"

echo
echo "Done: dist/WhatsAppMTD-${ARCH}.AppImage"
echo "Make it executable (chmod +x) and double-click it — no Python needed."
