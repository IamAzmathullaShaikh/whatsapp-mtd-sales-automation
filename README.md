# 🚀 WhatsApp Sales Automation Engine

[`https://www.python.org/`](https://www.python.org/)  \
[`https://opensource.org/licenses/MIT`](https://opensource.org/licenses/MIT)

A terminal-based automation pipeline for FMCG, Alco-Bev, and Territory Sales Executives. It turns raw daily sales dumps into per-account progress messages and dispatches them automatically through **WhatsApp Desktop** (Windows) or **WhatsApp Web** (Linux).

---

## 🚀 Quick start — no install needed (Windows GUI)

Grab the ready-made **`WhatsAppMTD.exe`** from the [Releases](https://github.com/IamAzmathullaShaikh/whatsapp-mtd-sales-automation/releases) page (Linux: the `WhatsAppMTD-x86_64.AppImage`). No Python, no packages, nothing to install.

1. **Download `WhatsAppMTD.exe`** and put it in a folder with your two Excel files:
   - `party_master.xlsx` — your account directory & monthly targets
   - your sales dump(s), e.g. `Outlet_Wise_Sales_08-08-2026.xlsx`
2. **Double-click the .exe** — the window opens instantly.
3. **🏢 Company → ➕ New** — type your agency name (first run auto-creates one from your old settings).
4. **▶ Run → Load File** — pick your sales dump; the layout is **auto-detected** and confirmed once, then remembered.
5. **🍾 Brands → ➕ Add** — map each brand's target & actual columns, then **▶ START DISPATCH**.

That's it. Everything is saved per company, so switching agencies or MTD file formats is just a dropdown change. First-time users: use the *daily* report and the **Below Achievement %** filter to start small.

**Windows will show a SmartScreen warning** for unsigned apps — click *More info → Run anyway*; the same applies to the AppImage on Linux (`chmod +x` first). See [docs/RELEASE.md](docs/RELEASE.md) for how the packages are built and how to build them yourself.

---

## ✨ Features
- **Interactive CLI Menu** – configure your profile and brand portfolio without touching code.
- **Dynamic Brand Portfolio** – manage product lines with flexible **Excel column mapping**.
- **Automated Ledger Generation** – raw Excel rows → mobile-friendly WhatsApp messages.
- **Dynamic Run Rate (DRR)** – pacing advice based on MTD volumes and days remaining.
- **Smart Eligibility Filtering** – only accounts that need attention get messaged.
- **Cross-Syndicate Consolidation** – merge outlets from different syndicates into one report for a single recipient.
- **Verified WhatsApp Delivery** – the chat window is confirmed focused (window title + screenshot diff) before each send on Windows; on Linux the message text is verified in WhatsApp Web's input box at the DOM level before Enter.
- **Management Dashboard** – Excel workbook with per-brand leaderboards and native charts.

---

## 🛠️ Prerequisites

**Windows path (WhatsApp Desktop):**
- **Windows OS** — the dispatcher uses `os.startfile` + `whatsapp://` URI handlers.
- [WhatsApp Desktop](https://apps.microsoft.com/store/detail/whatsapp/9NKSQCECGVDY) installed and logged in.

**Linux path (WhatsApp Web):**
- Any Linux distro with a display (X11 or Wayland).
- **Chromium/Chrome** and Python 3.12+ (one-command setup: `bash setup_linux.sh`).
- WhatsApp Web logged in once (QR scan) — the login persists in `.whatsapp_web_profile/`.

Both paths need Python 3.9+ (3.12 recommended) and `pip install -r requirements.txt`.

## 📦 Installation
```bash
git clone https://github.com/IamAzmathullaShaikh/whatsapp-mtd-sales-automation.git
cd whatsapp-mtd-sales-automation
pip install -r requirements.txt
```

To also run the test suite:
```bash
pip install -r requirements-dev.txt
pytest
```

---

## 📁 Data You Must Provide

Drop both files into the project root (next to `main.py`).

### 1. `party_master.xlsx` — the account directory & targets
One row per account. Columns used by the engine:

| Column | Meaning | Notes |
|---|---|---|
| `PARTY` | Account / group name | Join key — must match the syndicate or vendor name in the sales file |
| `PHONE` | Contact phone | 10-digit mobile gets `+91` automatically; keep digits only |
| `SEND` | Report preference | `YES` = always send; anything else = only when behind target |
| `PRIORITY` | Priority slab | `A`, `B`, or `C` |
| `TOTAL_TARGET` | Overall monthly target | Required |
| `<BRAND>_TARGET` | Per-brand target | One per brand, e.g. `OCW_TARGET` (names are configurable) |

### 2. `Outlet_Wise_Sales_<dd-mm-yyyy>.xlsx` — the raw daily sales dump
The **filename must embed the report date** (`Outlet_Wise_Sales_05-08-2026.xlsx`) — it is parsed to compute the report date and the days remaining in the month. Inside the workbook:

- **Sheet name:** `DATA`
- **Header row:** row 5 (0-indexed `4`) — adjust via `SALES_HEADER_ROW` in `config.py` if needed.
- **Columns used by the engine:**

| Column | Meaning | Notes |
|---|---|---|
| `Name Of Depot` | Depot owning the transaction | Used to filter which depots to process |
| `SYNDICATE NAME` | Group/syndicate of the row | Use the literal `INDIVIDUAL` for standalone outlets |
| `VENDOR_NAME` | Outlet / vendor name | The outlet identity |
| `Total` | Total volume for the row | Required |
| `<BRAND>.1` | Per-brand actual volume | One per brand, e.g. `OCW.1` (names are configurable) |

> **Column mapping is flexible.** The default convention is target columns `<CODE>_TARGET` in the master file and actual columns `<CODE>.1` in the sales dump. If your Excel uses different headers, configure the mapping in-app via **Manage Brand Portfolio** (stored in `user_settings.json`) — no code changes needed.
>
> **Mute a brand without deleting it.** Every brand has an `enabled` flag (default `true`). Set it to `false` in the Brands tab (GUI) or via **Toggle Brand Enable/Disable** (CLI) and the brand stays in your portfolio but is excluded from casting, aggregation, messages, and the dashboard — its missing columns are also no longer flagged by mapping validation. Useful for pausing a discontinued product line.

### 3. Everything else is generated for you
- `user_settings.json` — created on first run; holds your profile and brand→column mappings.
- `custom_groups.json` — created when you save a cross-syndicate consolidation preset.
- `config.py` — all runtime knobs and the expected Excel schema (see below).

---

## ⚙️ Configuration (`config.py`)

| Setting | Default | Purpose |
|---|---|---|
| `SALES_SHEET` / `SALES_HEADER_ROW` | `"DATA"` / `4` | Where the sales transactions live |
| `COL_*`, `TOTAL_TARGET_COL` | — | The expected column names — rename here if your data source changes |
| `PARTY_MASTER` | `"party_master.xlsx"` | Master file path |
| `WAIT_TIME` | `10` | Legacy web-setting wait (safely ignored for the desktop app) |
| `COOL_DOWN` | `3` | Seconds between consecutive sends (plus random +1–3s anti-block variance) |
| `TEST_MODE` / `TEST_LIMIT` | `False` / `5` | Cap the queue for dry runs |
| `MAX_RETRIES` | `2` | Refocus attempts per contact |
| `FOCUS_TIMEOUT` | `15` | Seconds to wait & verify the WhatsApp chat is focused before sending |
| `ELIGIBILITY_MAX_ACH_PCT` / `ELIGIBILITY_MIN_BALANCE` | `90.0` / `100` | "All Eligible" nudge thresholds — below/above these an account gets a message |
| `SKIP_DUPLICATE_PHONES` | `True` | Only send once per phone number |
| `MESSAGE_FOOTER` | `Regards, Sri Krishna Agencies` | Fallback signature used when no user profile is configured |
| `DISPATCH_BACKEND` | `"auto"` | `auto` = Windows→desktop app, Linux→WhatsApp Web; `desktop`/`web` force a backend |
| `WEB_USER_DATA_DIR` | `".whatsapp_web_profile"` | Persistent browser profile that keeps the WhatsApp Web login across runs |
| `WEB_HEADLESS` | `False` | Keep the browser visible during dispatch |
| `WEB_LOGIN_TIMEOUT` | `180` | Seconds to wait for the QR-code scan on first run |

---

## 🖥️ Desktop GUI

Prefer a window over a terminal? The same engine is wrapped in a native **tkinter** app (Python's built-in GUI library — zero extra dependencies). Most users never open a terminal: grab `WhatsAppMTD.exe` / `.AppImage` from [Releases](https://github.com/IamAzmathullaShaikh/whatsapp-mtd-sales-automation/releases) (see the Quick start at the top). From a checkout you can also run:

```bash
python gui.py
```

The GUI provides:
- **Company tab** — create / switch / delete companies (one per agency: own profile, brands, party master, MTD prefix, and Excel mapping).
- **Run tab** — sales-file picker (Browse or auto-detected list), report-type radios, depot checkboxes, filter-mode radios (all / priority slab / groups / custom consolidation with savable presets), and a one-click **Start Dispatch** button.
- **Profile tab** — edit the executive name, designation, and agency used in message headers/signatures.
- **Brands tab** — add / edit / remove brands, their Excel column mappings, and a **Mute/Unmute** toggle per brand (muted brands are kept but excluded from dispatch).
- **Live dispatch log** — progress streams into the panel in real time (per-contact status, focus verification, ETA), with a **Success / Failed / Skipped** summary.
- **Message preview** — after the queue is built (and before anything is sent) a preview dialog lists every queued account; clicking one renders the exact WhatsApp text it will receive, so you can eyeball formatting before dispatching.

Dispatching behaves exactly like the CLI engine — the data pipeline and dispatcher are shared unchanged. On Windows it drives WhatsApp Desktop; on Linux the **WhatsApp Web backend** (Selenium + Chromium) is selected automatically (see below).

---

## 🐧 Running natively on Linux (WhatsApp Web backend)

On Linux the engine dispatches through **WhatsApp Web** — a real Chromium window driven by Selenium. This is strictly stronger verification than the Windows path: the dispatcher waits for the chat to open, types the exact message into the input box, **reads the text back**, and only then presses Enter.

One-command setup (run from the project root):

```bash
bash setup_linux.sh
```

The script (optionally) runs the one-time system install (`sudo pacman -Sy chromium tk uv` on Arch/CachyOS), creates a Python 3.12 virtualenv with `uv`, installs `requirements.txt`, and prints the launch command. Manual launch once set up:

```bash
.venv/bin/python gui.py      # GUI
.venv/bin/python main.py     # CLI
```

**First run:** the browser opens WhatsApp Web; scan the QR code with your phone once. The login persists in `.whatsapp_web_profile/` — later runs go straight to dispatching. The browser window does not need OS focus; Selenium drives it over the WebDriver protocol (works on Wayland).

Force a specific backend with `DISPATCH_BACKEND = "desktop"` or `"web"` in `config.py` (default `auto` picks the right one for the platform).

---

## 🍷 Running the GUI on Linux (Wine, legacy/testing only)

The tkinter GUI can also run through **Wine** with a Windows Python. This is now only useful for testing the *preview and pipeline* on Windows-shaped setups — dispatching under Wine cannot work because WhatsApp Desktop is MSIX/Store-only and cannot be installed under Wine. Prefer the native Linux path above.

```bash
bash setup_wine.sh
```

The script initializes the default prefix (`~/.wine`), installs a **Windows Python 3.12**, installs `requirements.txt` inside it, and launches the GUI. It is idempotent — safe to re-run. The very first line prints the **one-time system install** it expects you to run yourself with sudo (Arch: `pacman -Sy --needed wine wine-gecko wine-mono winetricks`); on Debian/Ubuntu use the `wine` package from your distro instead.

Manual launch once set up:

```bash
wine "$HOME/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python312/python.exe" gui.py
```

> **The one-time Wine install needs root** (run the printed pacman/apt command with sudo yourself); everything in the script runs as your normal user. Needs an X/Wayland display — the GUI window is rendered by Wine on your current display.

---

## 🏢 Multiple companies, brands & MTD file types (newbie-friendly)

The tool is **per-company**: each agency/distributor gets its own profile,
brand portfolio, party master, MTD file prefix, and Excel mapping. Companies
live in `companies/` (one JSON per company — see `companies/README.md`), the
GUI has a **🏢 Company** tab to create/switch/delete them, and the CLI takes
`--company <slug>` (`python main.py --company my-agency`).

**Different MTD layouts just work.** Each company stores its own schema
mapping — which sheet, which header row, and which columns hold the depot,
syndicate, vendor, total (sales) and party, phone, send, priority, target
(master). The first time you load a sales dump for a company, the layout is
**auto-detected** (`schema.py` fuzzy-matches column headers against synonym
sets) and confirmed in a one-shot dialog; after that every file of that type
loads silently. Files with different spellings, header rows, or sheet names
are renamed to the canonical schema at load time, so the dispatch engine never
changes.

**Newbie quickstart (no config knowledge needed):**

1. `python gui.py` → **🏢 Company → ➕ New** → type the agency name.
2. **▶ Run → Browse… → Load File** → confirm the auto-detected sales mapping.
3. Confirm the party master mapping (party / phone / send / priority / target).
4. **🍾 Brands → ➕ Add** each brand (target + actual columns) and run.

Existing users are unaffected: the first run seeds a **Default Company** from
your current `user_settings.json`, keeping your profile and brands exactly as
 they were.

---

## 📌 Usage (CLI)

```bash
python main.py
```

**Main menu:**
1. **Run Sales Dispatch Engine** — the full pipeline (below).
2. **Edit My Profile** — name, designation, agency (used in the message header/signature).
3. **Manage Brand Portfolio** — add/edit/remove brands, their Excel column mappings, and mute/unmute brands without removing them.

**Inside the dispatch engine:**
1. Pick the sales file (auto-detected, newest first) and the report type:
   - *Daily Sales Progress Report* (invoiced + balance + DRR advice), or
   - *Start-of-Month Target Announcement* (targets only).
2. Select the **depot(s)** to process.
3. Select the **filter strategy**:
   - **All Eligible Accounts** — standard pacing rules (see below).
   - **Filter by Priority Slabs** — e.g. Priority A only.
   - **Accounts Below Achievement %** — target only the laggards, e.g. everyone under 80% of target (threshold is askable; default from `ELIGIBILITY_MAX_ACH_PCT`).
   - **Select Individual Groups/Syndicates/Outlets** — hand-pick accounts.
   - **Custom Consolidation** — combine outlets from any syndicates into a single report for one recipient (presets can be saved to `custom_groups.json`).
4. In filtered modes, multi-outlet syndicates prompt you to **drill down** and isolate specific outlets.

**What the engine computes per account:**
- MTD actual per brand (summed from the sales dump, joined by syndicate/vendor name).
- Achievement % = `actual / target × 100` and balance = `max(0, target − actual)`.
- Traffic light: 🟢 ≥ 90% · 🟡 70–90% · 🔴 < 70%.
- Required DRR: `ceil(balance ÷ days remaining)`.
- **Eligibility:** in "All Eligible" mode only accounts below `ELIGIBILITY_MAX_ACH_PCT` (default 90%) achievement, with balance above `ELIGIBILITY_MIN_BALANCE` (default 100), or Priority A are messaged; completed accounts are hidden. In filtered/consolidation modes, the selected accounts are always messaged.
- **Mapping validation:** before every run the tool checks that every mapped brand column actually exists in the loaded files and warns if not (a misspelled column would otherwise silently zero that brand). The brand editors also offer **column dropdowns auto-detected from the loaded files** — in the GUI *Brands* tab after loading a file, and via the *Validate Column Mapping* option in the CLI brand menu.
- Accounts with `SEND = YES` but no sales rows are flagged as **missing contacts** instead of being messaged.

**Dispatch order:** Priority A first, then lowest achievement %, then highest balance.

**During dispatch (Windows):** the tool opens each chat via `whatsapp://send`, verifies the chat window is focused before pressing Enter (title + screenshot check, `FOCUS_TIMEOUT`), retries on failure, applies a randomized cooldown, and writes audit trails.

**During dispatch (Linux):** each chat is opened in WhatsApp Web via `web.whatsapp.com/send?phone=…`, the dispatcher waits for the compose box (rejects invalid numbers), types the message, verifies the exact text landed, then presses Enter — same retries, cooldown, and audit trails.

---

## 📤 Outputs

| Output | Location |
|---|---|
| Management dashboard (leaderboards + charts) | `exports/territory_intelligence_dashboard_<date>.xlsx` |
| Accounts missing from the sales dump | `logs/missing_contacts_<date>.csv` |
| Send receipts (SENT / FAILED per contact) | `logs/dispatch_receipts_<rundate>.txt` |
| Structured dispatch log (SUCCESS / WARN / FAIL / SKIP) | `logs/dispatch_log_<rundate>.log` |

*(Dashboard & missing-contacts filenames use the report date from the sales file; receipts & logs use the date the run happened.)*

---

## 🧪 Testing

The pure logic (calculations, message templates, pipeline helpers) is covered by a pytest suite in `tests/`:

```bash
pip install -r requirements-dev.txt
pytest
```

---

## ⚠️ Notes & Troubleshooting
- **Windows** — dispatching relies on `os.startfile` and the WhatsApp Desktop URI handler; **Linux** — the WhatsApp Web backend needs Chromium + selenium (see `setup_linux.sh`) and one QR-code login.
- **Phone format** — keep 10-digit mobile numbers; the tool prefixes `+91`. Non-10-digit values are sent as `+<digits>`.
- **Filename date matters** — if no date is found in the sales filename, the current date is used instead (can produce a misleading "days remaining").
- **Message length** — the Windows URI handler may truncate very long messages; the Linux web backend types the message into the box so it is not truncated.
- **First run (Linux)** — if the browser opens on the QR screen, scan it and the login is remembered; if a number is rejected WhatsApp shows an "invalid phone number" popup and the contact is marked FAILED rather than sent.
- **First run (all)** — `user_settings.json` is created automatically with a default profile and brand portfolio; edit it via the menu before your first real run.

---

## 🧠 Agent Skills

This repo ships a small set of **agent skills** (`.agents/skills/`) that teach an AI coding assistant how to work in this codebase — where logic lives, how to run and verify the tests, how to launch the GUI on Linux (including the HiDPI/font quirks), how the dispatch pipeline is wired, the Excel schema, and the git conventions.

The set was authored by studying the public skills ecosystem (`anthropics/skills`, `obra/superpowers`, `mattpocock/skills`, `google/skills`, `vercel-labs/skills`, `MiniMax-AI/skills`, `emilkowalski/skills`, `slavingia/skills`, `MengTo/Skills`, `multica-ai/andrej-karpathy-skills`, `VoltAgent/awesome-openclaw-skills`). Every skill is versioned and records which upstream repos informed it.

**Keeping them updatable:** run `.agents/skills/scripts/update.sh` to re-fetch those upstream repos, refresh `upstream-manifest.md` (repo → commit SHA), and see which of them have moved since the last refresh — so improvements upstream can be folded in. See `.agents/skills/README.md` for the full table and conventions.

## 📚 Skill Library (router + ingest pipeline)

Beyond the curated set above, this repo ships a **skill library** — a small engine that ingests upstream skill repos, normalizes them, indexes them, and routes tasks to the best-matching skill:

```
skills/            sources/ (committed snapshots, refresh via sync) · normalized/ · index/ · manifests/
router/            stdlib-only scorer + router (tokenizer, scoring, route)
scripts/           skilllib CLI: sync · build · route · stats
prompts/           route + skill-use templates
config/            library.toml (sources, paths, router weights)
```

```bash
python -m scripts.skilllib sync                 # shallow-clone enabled sources
python -m scripts.skilllib build                # normalize + index + manifests
python -m scripts.skilllib route "fix my flaky tests"   # best-matching skills
python -m scripts.skilllib stats                # index summary
```

`mattpocock/skills`, `anthropics/skills`, `vercel-labs/skills`, `openai/skills`, `vercel-labs/agent-skills`, `cloudflare/skills`, and `supabase/agent-skills` are enabled by default — **133 skills across 8 sources** (122 upstream + 11 curated project skills); flip `enabled = true` in `config/library.toml` (or pass `--all`) to pull in more ecosystem repos (google, obra/superpowers, emilkowalski, MiniMax-AI, slavingia, MengTo, multica-ai, VoltAgent, JetBrains, antfu, vercel-kb). The router is pure Python — no dependencies — and covered by the same pytest suite (`tests/test_skilllib.py`).

**Export / import — take the skills to another model or machine:**

```bash
python -m scripts.skilllib export   # -> export/skills-bundle.json (data) + export/skills-prompt.md (prompt)
python -m scripts.skilllib import export/skills-bundle.json   # offline restore on any machine
```

The **bundle** is a self-contained data file: all 11 curated project skills (full text), all 122 upstream library skills (metadata + full bodies), the index, and provenance manifests — nothing is fetched at import time. The **prompt pack** is the same content as a structured markdown document you can hand to another model directly (curated skills in full, library skills with triggers + bodies, provenance table). Import restores `.agents/skills/` + `skills/` and rebuilds the index; the router works immediately afterwards.

See **[`skills-migration.md`](skills-migration.md)** for the full how-to: delivering the prompt pack to another model, and the 3-command offline restore on a fresh machine.

## 🤖 Local agent (Ollama) — skill-aware, no retraining

The library is wired to a **local model** so you can ask questions and get answers grounded in your own + upstream skills — without sending anything to the cloud and without dumping every SKILL.md into the prompt. Each request is **routed** to the best-matching skills and only those instructions are injected:

```
user request → router picks top-k skills → excerpts injected → qwen3:4b (local) → answer
```

Requirements: [Ollama](https://ollama.com/) installed with a model pulled (`ollama pull qwen3:4b`). Everything else is stdlib Python.

```bash
python -m scripts.skilllib ollama      # status: server up? which models?
python -m scripts.skilllib agent "What command runs the test suite in this repo?"   # route + ask
python -m scripts.skilllib chat        # interactive REPL: re-routes every turn
python -m scripts.skilllib modelfile   # render Modelfile from prompts/agent-system.md
ollama create azmath-agent -f Modelfile   # optional: persistent agent personality
```

`chat` is a REPL that keeps a rolling conversation (last `max_history_turns` exchanges) while **re-routing every turn** against the skill index — so a follow-up question pulls in fresh skills for that question. In-session commands: `/skills <query>` to preview routing, `/clear` to reset context, `/exit` to quit.

The agent personality lives in `prompts/agent-system.md` — a deliberately tight prompt (answer directly, never narrate internal reasoning, skills are external and only what's supplied). Tune `[agent]` in `config/library.toml`: model, `num_ctx` (16384 on CPU boxes — 32K eats RAM and slows generation), `max_tokens` (capped so CPU runs stay bounded; must cover the thinking trace + the answer), `max_skills` injected per request, and `timeout`. The client **streams** responses so progress flows even on slow CPU-only inference. Curated project skills (`.agents/skills/`, source `curated/local`) are injected alongside upstream ones. See `agent/` and `tests/test_agent.py`.

**`think` is `"auto"` by default**: each request is classified — greetings/small talk get a small `simple_max_tokens` cap (fast, concise), everything else gets the full `max_tokens` reasoning budget. `think` stays `true` in both tiers: on this Ollama build (0.32.6), `think: false` makes qwen3 narrate its deliberation *into the answer* (the "Okay, the user said…" leak), while `think: true` keeps the trace in a separate `thinking` field the client ignores — so output stays clean. In interactive `ollama run azmath-agent`, the CLI shows the trace by design; use `--hidethinking` (or `/set nothink` inside a session) to hide it. Avoid `--think=false` for this model.

## 🤖 azmath — the autonomous local agent platform

The same model + skill library now sit inside a **general-purpose agent runtime** (`azmath/`): tools, permissions, an iterative loop, verification, memory, and observability — so it can *do* things, not just answer.

```bash
./bin/azmath run "List the Python files at the root of this repository"   # uses fs.list, verifies, answers
./bin/azmath chat                        # interactive session
./bin/azmath doctor                      # environment self-diagnostics
./bin/azmath tools list                  # 21 capabilities with permission levels
./bin/azmath skills search "excel schema"
./bin/azmath models list
./bin/azmath config
```

**How it works** — each request is routed to the relevant skills, tool schemas are injected into the prompt, and the model decides what to do. If it emits a tool call (`{"tool": ...}`), the runtime checks the **permission policy** (reads are safe; writes, deletes, pushes, shell, and Python execution require approval — blocked in non-interactive runs), executes the tool, feeds the observation back, and loops. The runtime owns termination (iteration cap, timeouts, empty-response detection), a **verifier** checks the trace before declaring success, and everything emits structured events to `~/.azmath/events.jsonl` (secrets redacted). Provider-agnostic: the loop knows `ModelProvider`, not Ollama.

Configuration: `config/agent.toml` + `config/permissions.toml`, overridable via `AZMATH_*` env vars. See `docs/ARCHITECTURE.md`, `docs/TOOLS.md`, `docs/CONFIGURATION.md`, `docs/SECURITY.md`, `docs/SKILLS.md`, `docs/TROUBLESHOOTING.md`, `docs/DEVELOPMENT.md`.

> ⏱️ **Honest speed note**: CPU-only qwen3:4b generates at ~4 tok/s. `hello` ≈ 1 min; a real tool-use task ≈ 5–11 min. Bounded by the token cap, streaming throughout.

---

## 📄 License
MIT License – free to use, modify, and distribute.
