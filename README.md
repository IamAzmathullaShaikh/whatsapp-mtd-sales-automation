# 🚀 WhatsApp Sales Automation Engine

[`https://www.python.org/`](https://www.python.org/)
[`https://opensource.org/licenses/MIT`](https://opensource.org/licenses/MIT)

A lightweight, terminal-based automation pipeline for FMCG, Alco-Bev, and Territory Sales Executives.  
This engine transforms raw daily sales dumps into structured progress ledgers and dispatches them directly via the native WhatsApp Desktop app — eliminating manual data entry and saving hours of effort.

---

## ✨ Features

- **Automated Ledger Generation** – Convert raw Excel rows into clean, mobile-friendly text messages.  
- **Dynamic Run Rate (DRR)** – Calculate required daily pacing based on MTD volumes and remaining days.  
- **Cross-Syndicate Consolidation** – Merge outlet-level data across depots into consolidated reports.  
- **Smart Zero-Balance Filtering** – Hide brands that have already achieved 100% of target.  
- **Native WhatsApp Routing** – Use Windows URI handlers (`whatsapp://`) for safe, cost-free dispatch.  

---

## 🛠️ Setup

### Prerequisites
- Windows OS (required for URI shell handling)  
- [WhatsApp Desktop](https://apps.microsoft.com/store/detail/whatsapp/9NKSQCECGVDY) installed & authenticated  
- Python 3.9+  

### Installation
```bash
git clone https://github.com/YOUR-USERNAME/whatsapp-sales-automation.git
cd whatsapp-sales-automation
```

---

## 📌 Usage
Run the pipeline from terminal after placing your daily sales dump in the designated input folder.  
The engine will generate formatted ledgers and push them directly to WhatsApp contacts/groups.

---

## 📄 License
MIT License – free to use, modify, and distribute.

---