---
name: launching-the-gui
description: Use when launching, relaunching, or troubleshooting the desktop GUI window, including on this Linux machine. Trigger when the GUI won't start, shows tiny unreadable text, or needs a fresh launch after edits.
version: 1.0.0
sources:
  - google/skills
  - anthropics/skills
license: MIT
---

# Launching the GUI

## Linux (this machine)

```bash
cd ~/Projects/whatsapp-mtd-sales-automation
setsid .venv/bin/python gui.py >/tmp/gui_launch.log 2>&1 &
```

- `setsid` detaches the process so it survives the terminal reaping backgrounded children.
- From a non-graphical shell, export `DISPLAY=:0` first.
- Check state with `pgrep -af "python gui.py"`; read `/tmp/gui_launch.log` for errors.
- The launch command itself "hangs" on inherited file descriptors — that is expected. Confirm success in a fresh command.

## HiDPI scaling

The GUI auto-scales from the screen width (2560×1440 → ~1.33×). Override live:

```bash
GUI_SCALE=2.0 setsid .venv/bin/python gui.py >/tmp/gui_launch.log 2>&1 &
```

## Tiny unreadable text = wrong interpreter

If every label renders as tiny pixelated glyphs, the Python is wrong: uv's standalone Python bundles a Tk 9.0 with no fontconfig/Xft support (its `font families` returns only `['fixed']`). This venv was rebuilt on a system-linked Python 3.12 (`~/.local/python312`, patchelf RPATH) — its tkinter sees 630 families (Noto Sans). Fix the environment per `setup_linux.sh`; never patch fonts in code to work around it.

## Windows

`python gui.py` — the desktop backend (`dispatcher.py`) is auto-selected.

## Common mistakes

- Bundling the launch into a compound `pkill ... && setsid ...` — the shell quirk swallows it; launch in its own step.
- Judging success from the launch command itself. Always confirm with `pgrep` + log in a separate call.
