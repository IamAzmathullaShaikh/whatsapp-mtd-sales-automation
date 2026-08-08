# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the WhatsApp MTD Sales Automation GUI.

Builds a single, self-contained executable from gui.py:

    Windows:  dist/WhatsAppMTD.exe   (no Python or dependencies needed)
    Linux:    dist/WhatsAppMTD       (wrapped into an AppImage by build_appimage.sh)

The app reads its data from the working directory / file dialogs, so no data
files are bundled — users keep party_master.xlsx + their MTD dumps wherever
they run the executable.
"""

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scripts', 'router', 'agent', 'tests'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WhatsAppMTD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed: no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
