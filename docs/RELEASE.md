# 📦 Release packages — how they're built & shipped

The app ships as two **zero-install** packages so non-technical users never
touch Python:

| Platform | Artifact | Run it by |
|---|---|---|
| Windows | `WhatsAppMTD.exe` | double-click |
| Linux | `WhatsAppMTD-<arch>.AppImage` | `chmod +x` once, then double-click |

Both bundle Python + tkinter + pandas + everything else the GUI needs. The
app still reads its **data from the folder it runs in** (or via file dialogs):
`party_master.xlsx`, your MTD dumps, `companies/`, `user_settings.json` — so
keep those next to the executable.

## Where the packages come from

### CI (recommended) — `.github/workflows/build-release.yml`

Pushing a tag `v*` (or clicking **Run workflow** in the Actions tab) builds
both on their native runners and attaches them to a **GitHub Release**:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

- `windows-latest` → PyInstaller → `dist/WhatsAppMTD.exe`
- `ubuntu-latest` → PyInstaller → wrapped by appimagetool → `dist/WhatsAppMTD-x86_64.AppImage`

### Build locally

Windows (must run **on Windows**, PyInstaller can't cross-compile):

```bat
packaging\build_windows.bat
:: -> dist\WhatsAppMTD.exe
```

Linux:

```bash
bash packaging/build_appimage.sh        # uses .venv/bin/python by default
# -> dist/WhatsAppMTD-$(uname -m).AppImage
```

Both scripts install PyInstaller if missing and use the single
`WhatsAppMTD.spec` at the repo root, so the two platforms build the same app.

## What's inside / not inside

- **Bundled:** `gui.py` + all its imports (`pipeline`, `dashboard`,
  `dispatcher`, `dispatcher_web` (Selenium), `companies`, `schema`, ...),
  tkinter, pandas/numpy/openpyxl, questionary, pyautogui, selenium.
- **Not bundled:** the skill library (`skills/`, `router/`, `agent/`) — that's
  developer tooling, not part of the GUI app. Your data files are never
  bundled (they're personal); the app creates `companies/` and
  `user_settings.json` on first run.
- The build is **one-file** (`console=False`): single download, no folder to
  keep together. Slightly slower first launch (unpacks to a temp dir) is the
  trade-off for simplicity.

## Troubleshooting

- **Windows SmartScreen "Windows protected your PC"** — unsigned app; click
  *More info → Run anyway*. For a permanent fix, sign the exe with a
  code-signing cert and pass it via the spec (`codesign_identity`).
- **AppImage won't start / "cannot mount"** — older distros lack FUSE:
  `chmod +x WhatsAppMTD-x86_64.AppImage && APPIMAGE_EXTRACT_AND_RUN=1 ./WhatsAppMTD-x86_64.AppImage`.
- **GUI opens but text is tiny (Linux)** — HiDPI scaling is automatic
  (scales from screen width); override with `GUI_SCALE=2.0` when launching.
- **Antivirus false positives on the .exe** — PyInstaller one-file binaries
  occasionally trip heuristics; this is a known limitation, not malware.
- **Files "missing"** — the app looks in its working directory first. Either
  put the Excel files next to the exe, or use the browse buttons (full paths
  work from anywhere).
