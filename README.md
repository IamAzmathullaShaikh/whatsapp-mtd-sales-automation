# 🚀 WhatsApp Sales Automation Engine

[`https://www.python.org/`](https://www.python.org/)  \
[`https://opensource.org/licenses/MIT`](https://opensource.org/licenses/MIT)

A terminal-based automation pipeline for FMCG, Alco-Bev, and Territory Sales Executives. It turns raw daily sales dumps into per-account progress messages and dispatches them automatically through **WhatsApp Desktop**.

---

## ✨ Features
- **Interactive CLI Menu** – configure your profile and brand portfolio without touching code.
- **Dynamic Brand Portfolio** – manage product lines with flexible **Excel column mapping**.
- **Automated Ledger Generation** – raw Excel rows → mobile-friendly WhatsApp messages.
- **Dynamic Run Rate (DRR)** – pacing advice based on MTD volumes and days remaining.
- **Smart Eligibility Filtering** – only accounts that need attention get messaged.
- **Cross-Syndicate Consolidation** – merge outlets from different syndicates into one report for a single recipient.
- **Verified WhatsApp Delivery** – the chat window is confirmed focused (window title + screenshot diff) before each send.
- **Management Dashboard** – Excel workbook with per-brand leaderboards and native charts.

---

## 🛠️ Prerequisites
- **Windows OS** (the dispatcher uses `os.startfile` + `whatsapp://` URI handlers — Linux/macOS cannot send).
- [WhatsApp Desktop](https://apps.microsoft.com/store/detail/whatsapp/9NKSQCECGVDY) installed and logged in.
- Python 3.9+.

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
| `SKIP_DUPLICATE_PHONES` | `True` | Only send once per phone number |
| `MESSAGE_FOOTER` | `Regards, Sri Krishna Agencies` | Fallback signature used when no user profile is configured |

---

## 🖥️ Desktop GUI (optional)

Prefer a window over a terminal? The same engine is wrapped in a native **tkinter** app (Python's built-in GUI library — zero extra dependencies):

```bash
python gui.py
```

The GUI provides:
- **Run tab** — sales-file picker (Browse or auto-detected list), report-type radios, depot checkboxes, filter-mode radios (all / priority slab / groups / custom consolidation with savable presets), and a one-click **Start Dispatch** button.
- **Profile tab** — edit the executive name, designation, and agency used in message headers/signatures.
- **Brands tab** — add / edit / remove brands and their Excel column mappings.
- **Live dispatch log** — progress streams into the panel in real time (per-contact status, focus verification, ETA), with a **Success / Failed / Skipped** summary.
- **Message preview** — after the queue is built (and before anything is sent) a preview dialog lists every queued account; clicking one renders the exact WhatsApp text it will receive, so you can eyeball formatting before dispatching.

Dispatching still requires WhatsApp Desktop (Windows) and behaves exactly like the CLI engine — the data pipeline and dispatcher are shared unchanged.

---

## 🍷 Running the GUI on Linux (Wine)

The tkinter GUI runs on Linux through **Wine** (the engine's data pipeline, dashboard export, and message preview all work there). Dispatching to WhatsApp still requires the real WhatsApp Desktop, which is MSIX/Store-only and **cannot be installed under Wine** — so runs on Wine must stay in **`TEST_MODE = True`** (dry-run) or use a Windows machine for live dispatch.

One-command setup (run from the project root):

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

## 📌 Usage (CLI)

```bash
python main.py
```

**Main menu:**
1. **Run Sales Dispatch Engine** — the full pipeline (below).
2. **Edit My Profile** — name, designation, agency (used in the message header/signature).
3. **Manage Brand Portfolio** — add/edit/remove brands and their Excel column mappings.

**Inside the dispatch engine:**
1. Pick the sales file (auto-detected, newest first) and the report type:
   - *Daily Sales Progress Report* (invoiced + balance + DRR advice), or
   - *Start-of-Month Target Announcement* (targets only).
2. Select the **depot(s)** to process.
3. Select the **filter strategy**:
   - **All Eligible Accounts** — standard pacing rules (see below).
   - **Filter by Priority Slabs** — e.g. Priority A only.
   - **Select Individual Groups/Syndicates/Outlets** — hand-pick accounts.
   - **Custom Consolidation** — combine outlets from any syndicates into a single report for one recipient (presets can be saved to `custom_groups.json`).
4. In filtered modes, multi-outlet syndicates prompt you to **drill down** and isolate specific outlets.

**What the engine computes per account:**
- MTD actual per brand (summed from the sales dump, joined by syndicate/vendor name).
- Achievement % = `actual / target × 100` and balance = `max(0, target − actual)`.
- Traffic light: 🟢 ≥ 90% · 🟡 70–90% · 🔴 < 70%.
- Required DRR: `ceil(balance ÷ days remaining)`.
- **Eligibility:** in "All Eligible" mode only accounts with <90% achievement, balance > 100, or Priority A are messaged; completed accounts are hidden. In filtered/consolidation modes, the selected accounts are always messaged.
- Accounts with `SEND = YES` but no sales rows are flagged as **missing contacts** instead of being messaged.

**Dispatch order:** Priority A first, then lowest achievement %, then highest balance.

**During dispatch:** the tool opens each chat via `whatsapp://send`, verifies the chat window is focused before pressing Enter (title + screenshot check, `FOCUS_TIMEOUT`), retries on failure, applies a randomized cooldown, and writes audit trails.

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
- **Windows only** — dispatching relies on `os.startfile` and the WhatsApp Desktop URI handler.
- **Phone format** — keep 10-digit mobile numbers; the tool prefixes `+91`. Non-10-digit values are sent as `+<digits>`.
- **Filename date matters** — if no date is found in the sales filename, the current date is used instead (can produce a misleading "days remaining").
- **Message length** — very long messages may be truncated by WhatsApp's URI handler; delivery confirmation beyond "window focused" is not possible without reading the app UI.
- **First run** — `user_settings.json` is created automatically with a default profile and brand portfolio; edit it via the menu before your first real run.

---

## 📄 License
MIT License – free to use, modify, and distribute.
