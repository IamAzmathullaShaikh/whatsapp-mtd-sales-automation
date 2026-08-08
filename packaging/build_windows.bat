@echo off
REM ============================================================
REM  Build the Windows release: dist\WhatsAppMTD.exe
REM  Run this ON WINDOWS (Python 3.12 + pip). Everything needed
REM  is bundled — the .exe runs on machines with no Python.
REM ============================================================
cd /d "%~dp0.."
echo [1/2] Installing build + runtime dependencies...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
echo [2/2] Building WhatsAppMTD.exe ...
python -m PyInstaller --noconfirm WhatsAppMTD.spec
if errorlevel 1 exit /b 1
echo.
echo Done: dist\WhatsAppMTD.exe
echo Keep it next to your party_master.xlsx and MTD dump files, then double-click.
