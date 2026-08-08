"""
Execution pipeline: pure, testable data-processing helpers used by the dispatch engine.

Everything here is free of interactive prompts (questionary) and dispatching side
effects — functions take data and decisions in, and return structured results, so the
core logic can be unit-tested and reused outside the CLI.
"""

import os

import numpy as np
import pandas as pd

from config import (
    PARTY_MASTER,
    SALES_SHEET, SALES_HEADER_ROW,
    TOTAL_TARGET_COL, COL_DEPOT, COL_SYNDICATE, COL_VENDOR, COL_PARTY,
    COL_SEND, COL_PRIORITY, COL_PHONE, COL_TOTAL,
    INDIVIDUAL_SYNDICATE, SEND_YES,
)
import utils
import calculations
import templates


def normalize_phone(raw_phone):
    """Normalizes a raw phone value into an international dialable form (+91 for 10 digits)."""
    raw_phone = str(raw_phone).strip()
    if raw_phone.endswith(".0"):
        raw_phone = raw_phone[:-2]
    clean_digits = "".join(filter(str.isdigit, raw_phone))
    if len(clean_digits) == 10:
        return "+91" + clean_digits
    return "+" + clean_digits if clean_digits else ""


def compute_run_dates(selected_file):
    """Parses the report date context from the selected sales file."""
    report_date, file_date_str, current_dt = utils.parse_report_date(selected_file)
    current_day = current_dt.day
    total_days_in_month = pd.Period(current_dt.strftime("%Y-%m")).days_in_month
    remaining_days = max(1, (total_days_in_month - current_day) + 1)
    return report_date, file_date_str, remaining_days


def load_dataframes(selected_file):
    """Reads and normalizes the sales dump and party master dataframes."""
    df_sales = pd.read_excel(selected_file, sheet_name=SALES_SHEET, header=SALES_HEADER_ROW, dtype=str)
    df_master = pd.read_excel(PARTY_MASTER, dtype=str)

    df_sales.columns = df_sales.columns.str.strip()
    df_master.columns = df_master.columns.str.strip()

    df_sales[COL_DEPOT] = df_sales[COL_DEPOT].fillna("").astype(str).str.strip()
    df_sales[COL_SYNDICATE] = df_sales[COL_SYNDICATE].fillna("").astype(str).str.strip()
    df_sales[COL_VENDOR] = df_sales[COL_VENDOR].fillna("").astype(str).str.strip()
    df_master[COL_PARTY] = df_master[COL_PARTY].fillna("").astype(str).str.strip()

    return df_sales, df_master


def build_brand_map(settings):
    """
    Builds brand -> (target_col, actual_col) mappings plus the supporting column lists
    used for casting and aggregation.
    """
    brand_map = {}
    sales_brands = []
    target_cols = [TOTAL_TARGET_COL]
    market_names_for_template = {}

    for b_code, b_data in settings["brands"].items():
        tgt_col = b_data["target_col"]
        act_col = b_data["actual_col"]
        brand_map[b_code] = (tgt_col, act_col)
        sales_brands.append(act_col)
        target_cols.append(tgt_col)
        market_names_for_template[b_code] = b_data["name"]

    return brand_map, sales_brands, target_cols, market_names_for_template


def cast_sales_columns(df_sales, sales_brands):
    """Coerces mapped actual columns (and 'Total') to int, creating them as 0 if missing."""
    for c in sales_brands + [COL_TOTAL]:
        if c not in df_sales.columns:
            df_sales[c] = 0
        df_sales[c] = pd.to_numeric(df_sales[c], errors="coerce").fillna(0).astype(int)
    return df_sales


def cast_target_columns(df_master, target_cols):
    """Coerces target columns to int, creating them as 0 if missing."""
    for c in target_cols:
        if c not in df_master.columns:
            df_master[c] = 0
        df_master[c] = pd.to_numeric(df_master[c], errors="coerce").fillna(0).astype(int)
    return df_master


def aggregate_actuals(df_sales, sales_brands):
    """
    Aggregates per-syndicate actual volumes (and per-vendor for INDIVIDUAL rows),
    plus outlet-level breakdowns for drill-down support.
    """
    actual_perf = {}
    brand_level_outlets = {}

    for snd, grp in df_sales[df_sales[COL_SYNDICATE] != INDIVIDUAL_SYNDICATE].groupby(COL_SYNDICATE):
        actual_perf[snd] = grp[sales_brands].sum().to_dict()
        actual_perf[snd]["TOTAL_ACTUAL"] = grp[COL_TOTAL].sum()

        brand_level_outlets[snd] = []
        for v_name, v_grp in grp.groupby(COL_VENDOR):
            brand_level_outlets[snd].append({
                "vendor_name": v_name,
                "data": v_grp[sales_brands].sum().to_dict(),
                "total": v_grp[COL_TOTAL].sum()
            })

    for vnd, grp in df_sales[df_sales[COL_SYNDICATE] == INDIVIDUAL_SYNDICATE].groupby(COL_VENDOR):
        actual_perf[vnd] = grp[sales_brands].sum().to_dict()
        actual_perf[vnd]["TOTAL_ACTUAL"] = grp[COL_TOTAL].sum()

    return actual_perf, brand_level_outlets


def compute_required_drr(total_balance, remaining_days):
    """Daily required rate needed to close the remaining balance before month end."""
    return int(np.ceil(total_balance / remaining_days)) if remaining_days > 0 else 0


def build_brand_strings(row, actual, brand_map):
    """Builds per-brand status entries for the templates from a master row and actuals."""
    brand_strings = []
    for b_lbl, (tgt_k, act_k) in brand_map.items():
        _light, _pct, b_bal = calculations.get_brand_status(row[tgt_k], actual[act_k])
        brand_strings.append({"label": b_lbl, "actual": actual[act_k], "balance": b_bal, "target": row[tgt_k]})
    return brand_strings


def render_message(report_type, party, report_date, total_target, total_actual,
                   total_ach_pct, total_balance, remaining_days, required_drr,
                   brand_strings, market_names, user_profile):
    """Renders either the daily progress report or the monthly target announcement message."""
    if "Target Announcement" in report_type:
        return templates.build_monthly_target_message(
            party, total_target, brand_strings, market_names, user_profile
        )
    return templates.build_whatsapp_message(
        party, report_date, total_target, total_actual, total_ach_pct,
        total_balance, remaining_days, required_drr, brand_strings,
        market_names, user_profile, target_completed=(total_balance <= 0)
    )


def build_custom_item(df_master, df_sales, brand_map, market_names, user_profile,
                      report_type, report_date, remaining_days, custom_run_config):
    """
    Builds the single consolidated dispatch item for the custom cross-syndicate run.
    Returns the queue item dict.
    """
    recipient = custom_run_config["recipient"]
    selected_outlets = custom_run_config["outlets"]

    row = df_master[df_master[COL_PARTY] == recipient].iloc[0]
    priority = str(row[COL_PRIORITY]).strip().upper()
    phone = normalize_phone(row[COL_PHONE])

    df_custom = df_sales[df_sales[COL_VENDOR].isin(selected_outlets)]
    total_actual = int(df_custom[COL_TOTAL].sum())
    total_target = row[TOTAL_TARGET_COL]

    _light, total_ach_pct, total_balance = calculations.get_brand_status(total_target, total_actual)
    required_drr = compute_required_drr(total_balance, remaining_days)

    brand_strings = []
    for b_lbl, (tgt_k, act_k) in brand_map.items():
        b_tgt = row[tgt_k]
        b_act = int(df_custom[act_k].sum())
        _light, _pct, b_bal = calculations.get_brand_status(b_tgt, b_act)
        brand_strings.append({"label": b_lbl, "actual": b_act, "balance": b_bal, "target": b_tgt})

    message = render_message(
        report_type, recipient, report_date, total_target, total_actual,
        total_ach_pct, total_balance, remaining_days, required_drr,
        brand_strings, market_names, user_profile
    )

    return {
        "party": recipient, "phone": phone, "priority": priority,
        "ach_pct": total_ach_pct, "balance": total_balance, "message": message
    }


def build_regular_items(df_master, actual_perf, brand_level_outlets, brand_map, sales_brands,
                        market_names, user_profile, report_type, report_date, remaining_days,
                        allowed_parties=None, drill_down_resolver=None):
    """
    Builds dispatch items, dashboard rows, and missing contacts for the standard path.

    drill_down_resolver(party, outlets) -> list[str] | None: optional callback (usually
    interactive) that lets the operator isolate specific outlets of a multi-outlet
    syndicate. Returning None keeps the full syndicate; returning an empty list skips
    the party entirely.
    """
    dashboard_rows = []
    unordered_queue = []
    missing_contacts = []

    for _, row in df_master.iterrows():
        party = row[COL_PARTY]
        should_send = str(row[COL_SEND]).strip().upper()
        priority = str(row[COL_PRIORITY]).strip().upper()

        if allowed_parties is not None and party not in allowed_parties:
            continue

        phone = normalize_phone(row[COL_PHONE])

        if party not in actual_perf:
            if should_send == SEND_YES.upper():
                # NOTE: these keys are the missing_contacts CSV column headers (an output
                # contract), not the input Excel schema — intentionally not centralized.
                missing_contacts.append({
                    "PARTY": party, "PHONE": phone, "PRIORITY": priority, "TARGET": row[TOTAL_TARGET_COL]
                })
            continue

        act = actual_perf[party]
        total_target = row[TOTAL_TARGET_COL]
        total_actual = act["TOTAL_ACTUAL"]

        _light, total_ach_pct, total_balance = calculations.get_brand_status(total_target, total_actual)
        required_drr = compute_required_drr(total_balance, remaining_days)

        if party in brand_level_outlets and allowed_parties is not None and drill_down_resolver is not None:
            selected_outlet_names = drill_down_resolver(party, brand_level_outlets[party])
            if selected_outlet_names is not None:
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
                _light, total_ach_pct, total_balance = calculations.get_brand_status(total_target, total_actual)
                required_drr = compute_required_drr(total_balance, remaining_days)

        brand_strings = build_brand_strings(row, act, brand_map)
        row_metrics = {
            "Party Name": party, "Priority": priority, "Monthly Target": total_target,
            "MTD Invoiced": total_actual, "Gap Balance": total_balance, "Achievement %": total_ach_pct
        }
        for b in brand_strings:
            row_metrics[f"{b['label']} Target"] = b["target"]
            row_metrics[f"{b['label']} MTD"] = b["actual"]

        message = render_message(
            report_type, party, report_date, total_target, total_actual,
            total_ach_pct, total_balance, remaining_days, required_drr,
            brand_strings, market_names, user_profile
        )

        item = {
            "party": party, "phone": phone, "priority": priority,
            "ach_pct": total_ach_pct, "balance": total_balance, "message": message
        }

        if allowed_parties is not None or (total_ach_pct < 90.0 or total_balance > 100 or priority == "A"):
            unordered_queue.append(item)

        dashboard_rows.append(row_metrics)

    return unordered_queue, dashboard_rows, missing_contacts


def build_dispatch_queue(unordered_queue):
    """Sorts the queue: Priority A first, then ascending achievement %, then balance desc."""
    return sorted(unordered_queue, key=lambda x: (0 if x["priority"] == "A" else 1, x["ach_pct"], -x["balance"]))


def export_missing_contacts(missing_contacts, file_date_str):
    """Writes accounts missing from the sales dump to logs/ (creating the dir as needed)."""
    if not missing_contacts:
        return
    os.makedirs("logs", exist_ok=True)
    pd.DataFrame(missing_contacts).to_csv(f"logs/missing_contacts_{file_date_str}.csv", index=False)
