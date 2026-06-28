# 🚀 WhatsApp Sales Automation Engine

[`https://www.python.org/`](https://www.python.org/)  
[`https://opensource.org/licenses/MIT`](https://opensource.org/licenses/MIT)

A terminal-based automation pipeline for FMCG, Alco-Bev, and Territory Sales Executives.  
Transforms raw daily sales dumps into structured progress ledgers and dispatches them via WhatsApp Desktop — ready to use out-of-the-box, no code edits required.

---

## ✨ Features
- **Interactive Menu** – Configure executive profile and agency directly from CLI.  
- **Dynamic Brand Portfolio** – Manage product lines with **Excel Column Mapping** for flexible headers.  
- **Automated Ledger Generation** – Convert raw Excel rows into mobile-friendly messages.  
- **Dynamic Run Rate (DRR)** – Calculate pacing based on MTD volumes and remaining days.  
- **Cross-Syndicate Consolidation** – Merge outlet-level data into consolidated reports.  
- **Smart Zero-Balance Filtering** – Hide brands that hit 100% target.  
- **Native WhatsApp Routing** – Safe dispatch via Windows URI handlers (`whatsapp://`).  

---

## 🛠️ Setup

### Prerequisites
- Windows OS  
- [WhatsApp Desktop](https://apps.microsoft.com/store/detail/whatsapp/9NKSQCECGVDY) installed & authenticated  
- Python 3.9+  

### Installation
```bash
git clone https://github.com/YOUR-USERNAME/whatsapp-sales-automation.git
cd whatsapp-sales-automation
pip install -r requirements.txt
```

---

## 📁 Data Structure
- **party_master.xlsx** – Master territory dictionary (PARTY, PHONE, PRIORITY, target columns).  
- **Outlet_Wise_Sales_*.xlsx** – Raw transactional sales dump (latest file auto-detected).  

---

## 📌 Usage
```bash
python main.py
```

- First run generates `user_settings.json`.  
- Use CLI menu to edit profile and manage brand portfolio.  
- Run dispatch engine to parse data, calculate DRR, and push formatted ledgers to WhatsApp contacts.

---

## 📄 License
MIT License – free to use, modify, and distribute.

---