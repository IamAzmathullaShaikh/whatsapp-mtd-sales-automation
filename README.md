```markdown
# 🚀 WhatsApp Sales Automation Engine

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An automated, terminal-based pipeline designed for FMCG, Alco-Bev, and Route-to-Market Territory Sales Executives. 

This engine eliminates hours of manual data entry by ingesting raw daily sales dump files, mapping them against dynamic territory master targets, and dispatching beautifully formatted, mobile-friendly progress ledgers directly to retailers and distributors via the native Windows WhatsApp Desktop Application.

---

## ✨ Core Architecture & Features

* 📊 **Automated Ledger Generation:** Converts raw, unstructured Excel transaction rows into clean, highly readable text messages optimized for variable-width mobile fonts.
* 🎯 **Dynamic Pacing (DRR) Calculation:** Automatically calculates the Required Daily Run Rate based on remaining calendar days, current MTD volumes, and expected shortfalls.
* 🧩 **Cross-Syndicate Custom Consolidation:** Selectively combine invoiced sales data from multiple individual retail outlets across different depots and report the consolidated metrics to a single master group owner.
* 🧠 **Smart Zero-Balance Filtering:** Intelligently hides brands that have achieved 100% of their monthly target, keeping focus strictly on priority stock-lifting requirements.
* 🛡️ **Native Desktop URI Routing:** Uses native Windows OS shell handlers (`whatsapp://`) rather than third-party Web APIs or browser automation, avoiding heavy subscription costs and minimizing account ban risks.

---

## 🛠️ Installation & Setup

### Prerequisites
* Windows OS (Required for URI shell handling)
* [WhatsApp Desktop App for Windows](https://apps.microsoft.com/store/detail/whatsapp/9NKSQCECGVDY) installed and authenticated.
* Python 3.9 or higher.

### Installation
1. Clone the repository to your local machine:
   ```bash
   git clone [https://github.com/YOUR-USERNAME/whatsapp-sales-automation.git](https://github.com/YOUR-USERNAME/whatsapp-sales-automation.git)
   cd whatsapp-sales-automation

```

2. Install the required execution dependencies:
```bash
pip install -r requirements.txt

```



---

## 📁 Required Data Structure

To protect your business intelligence, this repository does not include real sales data. To run the engine, you must provide your own data files in the root directory:

1. **`party_master.xlsx`**
* The master territory dictionary. Must contain standard columns for: `PARTY`, `PHONE` (Format: +91XXXXXXXXXX), `PRIORITY`, and `TOTAL_TARGET`.


2. **`Outlet_Wise_Sales_*.xlsx`**
* The raw transactional sales dump. The script uses regex and date-string parsing to auto-detect the newest file in the directory.



---

## 🚀 Execution Guide

1. Ensure the Windows WhatsApp app is open and running in the background.
2. Launch the automation engine from your terminal:
```bash
python main.py

```


3. Follow the interactive CLI prompts to select your operational parameters:
* **Report Type:** Daily Progress Report vs. Start-of-Month Targets.
* **Depot Selection:** Select single or multi-depot runs.
* **Targeting Rule:** Filter by priority, run specific syndicates, or execute a custom multi-outlet consolidation.


4. Once the queue is compiled, follow the terminal prompt to focus your WhatsApp window and let the engine drive the dispatch.

---

## ⚙️ Configuration (`config.py`)

You can fine-tune the engine's behavior by modifying the variables in `config.py`:

* `WAIT_TIME`: The buffer (in seconds) allowed for WhatsApp to render text before sending. Increase this if messages are stuck as drafts.
* `COOL_DOWN`: The padding (in seconds) between dispatches to maintain pacing logic and avoid API throttling.
* `TEST_MODE`: Limits the dispatch queue to a safe number of accounts for dry-runs and pipeline testing.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```

```