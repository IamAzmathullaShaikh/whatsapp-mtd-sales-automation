import os
import time
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import questionary

# Central Import Modules
from config import (
    PARTY_MASTER, WAIT_TIME, TAB_CLOSE, CLOSE_TIME, 
    COOL_DOWN, TEST_MODE, TEST_LIMIT, MAX_RETRIES, SKIP_DUPLICATE_PHONES
)
import utils
import calculations
import templates
import dashboard
import dispatcher

def select_sales_file():
    """Scans the local directory and prompts user to select a target sales dump file."""
    files = [f for f in os.listdir('.') if f.startswith('Outlet_Wise_Sales_') and f.endswith('.xlsx')]
    if not files:
        raise FileNotFoundError("No 'Outlet_Wise_Sales_*.xlsx' files detected in your directory.")
    
    files.sort(reverse=True)
    
    selected = questionary.select(
        "📅 Select the historical target report date file to process:",
        choices=files
    ).ask()
    return selected

def main():
    selected_file = select_sales_file()
    print(f"🔄 Ingesting chosen file target: {selected_file}")

    report_type = questionary.select(
        "📝 Select the type of WhatsApp communication to send:",
        choices=[
            "Daily Sales Progress Report (Invoiced / Balance)",
            "Start-of-Month Target Announcement"
        ]
    ).ask()

    report_date, file_date_str, current_dt = utils.parse_report_date(selected_file)
    current_day = current_dt.day
    total_days_in_month = pd.Period(current_dt.strftime("%Y-%m")).days_in_month
    remaining_days = max(1, (total_days_in_month - current_day) + 1)
    
    df_sales = pd.read_excel(selected_file, sheet_name="DATA", header=4, dtype=str)
    df_master = pd.read_excel(PARTY_MASTER, dtype=str)
    
    df_sales.columns = df_sales.columns.str.strip()
    df_master.columns = df_master.columns.str.strip()
    
    df_sales["Name Of Depot"] = df_sales["Name Of Depot"].fillna("").astype(str).str.strip()
    df_sales["SYNDICATE NAME"] = df_sales["SYNDICATE NAME"].fillna("").astype(str).str.strip()
    df_sales["VENDOR_NAME"] = df_sales["VENDOR_NAME"].fillna("").astype(str).str.strip()
    df_master["PARTY"] = df_master["PARTY"].fillna("").astype(str).str.strip()
    
    available_depots = sorted([d for d in df_sales["Name Of Depot"].unique() if d])
    if not available_depots:
        raise ValueError("No valid depots found in the sales file.")
        
    selected_depots = questionary.checkbox(
        "🏢 Select the Depot(s) to process (Space to select, Enter to confirm):",
        choices=available_depots
    ).ask()
    
    if not selected_depots:
        print("🛑 No depots selected. Terminating run execution.")
        return
        
    df_sales = df_sales[df_sales["Name Of Depot"].isin(selected_depots)].copy()
    if df_sales.empty:
        raise ValueError("No transactions found for the selected depot(s).")
        
    sales_brands = ["OCW.1", "OCBL.1", "SRB10.1", "SRB7.1", "IQW.1", "KYRON.1", "OCBRANDY.1"]
    for c in sales_brands + ["Total"]:
        df_sales[c] = pd.to_numeric(df_sales[c], errors="coerce").fillna(0).astype(int)
        
    target_cols = ["TOTAL_TARGET", "OCW_TARGET", "OCBL_TARGET", "SRB10_TARGET", "SRB7_TARGET", "IQW_TARGET", "KYRON_TARGET", "OCBRANDY_TARGET"]
    for c in target_cols:
        df_master[c] = pd.to_numeric(df_master[c], errors="coerce").fillna(0).astype(int)
        
    filter_mode = questionary.select(
        "🎯 Select dispatch filter targeting rule strategy:",
        choices=[
            "All Eligible Accounts (Standard Automated Pacing Rules)",
            "Filter by Specific Priority Slabs (e.g., Priority A Only)",
            "Select Individual Group/Syndicates or Specific Outlets",
            "🧩 Custom Consolidation (Combine Cross-Syndicate Outlets for a Single Recipient)"
        ]
    ).ask()

    allowed_parties = None
    custom_run_config = None

    if "Priority Slabs" in filter_mode:
        target_priority = questionary.select("Select target priority tier:", choices=["A", "B", "C"]).ask()
        allowed_parties = set(df_master[df_master["PRIORITY"].str.upper() == target_priority]["PARTY"])
        
    elif "Individual Group" in filter_mode:
        all_master_options = sorted(list(df_master["PARTY"].unique()))
        chosen_groups = questionary.checkbox(
            "Select one or more accounts/groups to broadcast updates to (Space to select, Enter to confirm):",
            choices=all_master_options
        ).ask()
        if not chosen_groups:
            print("🛑 No options selected. Terminating run execution.")
            return
        allowed_parties = set(chosen_groups)
        
    elif "Custom Consolidation" in filter_mode:
        config_file = "custom_groups.json"
        saved_groups = {}
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                saved_groups = json.load(f)

        recipient = questionary.select(
            "👤 Select the Target Recipient (This account's Target & Phone Number will be used):",
            choices=sorted(list(df_master["PARTY"].unique()))
        ).ask()

        selected_outlets = []
        
        if recipient in saved_groups:
            use_saved = questionary.confirm(
                f"💾 Found a saved custom group for '{recipient}' containing {len(saved_groups[recipient])} outlets. Use this saved group?"
            ).ask()
            if use_saved:
                selected_outlets = saved_groups[recipient]
                
        if not selected_outlets:
            all_outlets = sorted(list(df_sales["VENDOR_NAME"].unique()))
            selected_outlets = questionary.checkbox(
                f"🏪 Select ALL outlets to combine into this report (Showing outlets from {', '.join(selected_depots)}):",
                choices=all_outlets
            ).ask()

            if not selected_outlets:
                print("🛑 No outlets selected. Terminating run execution.")
                return
                
            save_preset = questionary.confirm(
                f"📝 Do you want to save this combination of {len(selected_outlets)} outlets for future use under '{recipient}'?"
            ).ask()
            
            if save_preset:
                saved_groups[recipient] = selected_outlets
                with open(config_file, "w") as f:
                    json.dump(saved_groups, f, indent=4)
                print(f"✅ Successfully saved custom group mapping for '{recipient}'.")

        custom_run_config = {
            "recipient": recipient,
            "outlets": selected_outlets
        }

    actual_perf = {}
    brand_level_outlets = {}
    
    for snd, grp in df_sales[df_sales["SYNDICATE NAME"] != "INDIVIDUAL"].groupby("SYNDICATE NAME"):
        actual_perf[snd] = grp[sales_brands].sum().to_dict()
        actual_perf[snd]["TOTAL_ACTUAL"] = grp["Total"].sum()
        
        brand_level_outlets[snd] = []
        for v_name, v_grp in grp.groupby("VENDOR_NAME"):
            brand_level_outlets[snd].append({
                "vendor_name": v_name,
                "data": v_grp[sales_brands].sum().to_dict(),
                "total": v_grp["Total"].sum()
            })
        
    for vnd, grp in df_sales[df_sales["SYNDICATE NAME"] == "INDIVIDUAL"].groupby("VENDOR_NAME"):
        actual_perf[vnd] = grp[sales_brands].sum().to_dict()
        actual_perf[vnd]["TOTAL_ACTUAL"] = grp["Total"].sum()

    brand_map = {
        "OCW": ("OCW_TARGET", "OCW.1"), "OCBL": ("OCBL_TARGET", "OCBL.1"),
        "SRB10": ("SRB10_TARGET", "SRB10.1"), "SRB7": ("SRB7_TARGET", "SRB7.1"),
        "IQW": ("IQW_TARGET", "IQW.1"), "KYRON": ("KYRON_TARGET", "KYRON.1"),
        "OCBRANDY": ("OCBRANDY_TARGET", "OCBRANDY.1")
    }
    
    dashboard_rows = []
    unordered_queue = []
    missing_contacts = []
    
    if custom_run_config:
        recipient = custom_run_config["recipient"]
        selected_outlets = custom_run_config["outlets"]
        
        row = df_master[df_master["PARTY"] == recipient].iloc[0]
        priority = str(row["PRIORITY"]).strip().upper()
        
        raw_phone = str(row["PHONE"]).strip()
        if raw_phone.endswith(".0"): raw_phone = raw_phone[:-2]
        clean_digits = "".join(filter(str.isdigit, raw_phone))
        phone = "+91" + clean_digits if len(clean_digits) == 10 else ("+" + clean_digits if clean_digits else "")
        
        df_custom = df_sales[df_sales["VENDOR_NAME"].isin(selected_outlets)]
        total_actual = int(df_custom["Total"].sum())
        total_target = row["TOTAL_TARGET"]
        
        total_light, total_ach_pct, total_balance = calculations.get_brand_status(total_target, total_actual)
        required_drr = int(np.ceil(total_balance / remaining_days)) if remaining_days > 0 else 0
        
        brand_strings = []
        for b_lbl, (tgt_k, act_k) in brand_map.items():
            b_tgt = row[tgt_k]
            b_act = int(df_custom[act_k].sum())
            b_light, b_pct, b_bal = calculations.get_brand_status(b_tgt, b_act)
            brand_strings.append({"label": b_lbl, "actual": b_act, "balance": b_bal, "target": b_tgt})
                
        if "Target Announcement" in report_type:
            message = templates.build_monthly_target_message(recipient, total_target, brand_strings)
        else:
            is_completed = True if total_balance <= 0 else False
            message = templates.build_whatsapp_message(
                recipient, report_date, total_target, total_actual, total_ach_pct, 
                total_balance, remaining_days, required_drr, brand_strings, target_completed=is_completed
            )
            
        unordered_queue.append({"party": recipient, "phone": phone, "priority": priority, "ach_pct": total_ach_pct, "balance": total_balance, "message": message})
        
    else:
        for _, row in df_master.iterrows():
            party = row["PARTY"]
            should_send = str(row["SEND"]).strip().upper()
            priority = str(row["PRIORITY"]).strip().upper()
            
            if allowed_parties is not None and party not in allowed_parties:
                continue

            raw_phone = str(row["PHONE"]).strip()
            if raw_phone.endswith(".0"): raw_phone = raw_phone[:-2]
            clean_digits = "".join(filter(str.isdigit, raw_phone))
            phone = "+91" + clean_digits if len(clean_digits) == 10 else ("+" + clean_digits if clean_digits else "")

            if party not in actual_perf:
                if should_send == "YES":
                    missing_contacts.append({"PARTY": party, "PHONE": phone, "PRIORITY": priority, "TARGET": row["TOTAL_TARGET"]})
                continue
                
            act = actual_perf[party]
            total_target = row["TOTAL_TARGET"]
            total_actual = act["TOTAL_ACTUAL"]
            
            total_light, total_ach_pct, total_balance = calculations.get_brand_status(total_target, total_actual)
            required_drr = int(np.ceil(total_balance / remaining_days)) if remaining_days > 0 else 0
            
            if party in brand_level_outlets and allowed_parties is not None:
                drill_down = questionary.confirm(f"🔎 Syndicate '{party}' contains multiple outlets. Do you want to isolate specific outlets from this group?").ask()
                if drill_down:
                    choices_outlets = [questionary.Choice(title=f"{o['vendor_name']} (MTD Vol: {o['total']})", value=o['vendor_name']) for o in brand_level_outlets[party]]
                    selected_outlet_names = questionary.checkbox("Select the outlets to include:", choices=choices_outlets).ask()
                    
                    if not selected_outlet_names:
                        continue
                    
                    custom_act = {brand: 0 for brand in sales_brands}
                    custom_total = 0
                    for o in brand_level_outlets[party]:
                        if o["vendor_name"] in selected_outlet_names:
                            custom_total += o["total"]
                            for brand in sales_brands:
                                custom_act[brand] += o["data"][brand]
                    
                    act = custom_act
                    total_actual = custom_total
                    total_light, total_ach_pct, total_balance = calculations.get_brand_status(total_target, total_actual)
                    required_drr = int(np.ceil(total_balance / remaining_days)) if remaining_days > 0 else 0

            brand_strings = []
            row_metrics = {"Party Name": party, "Priority": priority, "Monthly Target": total_target, "MTD Invoiced": total_actual, "Gap Balance": total_balance, "Achievement %": total_ach_pct}
            
            for b_lbl, (tgt_k, act_k) in brand_map.items():
                b_light, b_pct, b_bal = calculations.get_brand_status(row[tgt_k], act[act_k])
                row_metrics[f"{b_lbl} Target"] = row[tgt_k]
                row_metrics[f"{b_lbl} MTD"] = act[act_k]
                brand_strings.append({"label": b_lbl, "actual": act[act_k], "balance": b_bal, "target": row[tgt_k]})
                
            if "Target Announcement" in report_type:
                message = templates.build_monthly_target_message(party, total_target, brand_strings)
            else:
                is_completed = True if total_balance <= 0 else False
                message = templates.build_whatsapp_message(
                    party, report_date, total_target, total_actual, total_ach_pct, 
                    total_balance, remaining_days, required_drr, brand_strings, target_completed=is_completed
                )
            
            item = {"party": party, "phone": phone, "priority": priority, "ach_pct": total_ach_pct, "balance": total_balance, "message": message}
            
            if allowed_parties is not None or (total_ach_pct < 90.0 or total_balance > 100 or priority == "A"):
                unordered_queue.append(item)
                
            dashboard_rows.append(row_metrics)
            
    if not custom_run_config and dashboard_rows:
        dashboard.export_territory_dashboard(dashboard_rows, file_date_str, brand_map.keys())
    
    if missing_contacts and not custom_run_config:
        pd.DataFrame(missing_contacts).to_csv(f"logs/missing_contacts_{file_date_str}.csv", index=False)
        
    dispatch_queue = sorted(unordered_queue, key=lambda x: (0 if x["priority"] == "A" else 1, x["ach_pct"], -x["balance"]))
    
    if TEST_MODE:
        dispatch_queue = dispatch_queue[:TEST_LIMIT]
        
    success, failed, skipped = dispatcher.process_dispatch_queue(dispatch_queue, WAIT_TIME, TAB_CLOSE, CLOSE_TIME, COOL_DOWN, MAX_RETRIES)
    print(f"\n🏁 Run Completed Cleanly. Success: {success} | Failed: {failed}")

if __name__ == "__main__":
    main()
