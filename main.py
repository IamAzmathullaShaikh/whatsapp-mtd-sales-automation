import os
import sys
import json
import argparse
import questionary

from config import (
    WAIT_TIME, TAB_CLOSE, CLOSE_TIME,
    COOL_DOWN, TEST_MODE, TEST_LIMIT, MAX_RETRIES, FOCUS_TIMEOUT,
    SALES_FILE_PREFIX, SALES_FILE_EXTENSION, DISPATCH_BACKEND,
    COL_DEPOT, COL_VENDOR, COL_PARTY, COL_PRIORITY,
    ELIGIBILITY_MAX_ACH_PCT,
)
import pipeline
import dashboard
import dispatcher

SETTINGS_FILE = "user_settings.json"

def load_settings():
    """Loads settings and automatically migrates old string-based brands to custom column mappings."""
    default_settings = {
        "profile": {
            "name": "Azmathulla Sk",
            "designation": "Sales Executive",
            "agency": "Sri Krishna Agencies"
        },
        "brands": {
            "OCW": {"name": "Officer's Choice Whisky", "target_col": "OCW_TARGET", "actual_col": "OCW.1", "enabled": True},
            "OCBL": {"name": "Officer's Choice Blue", "target_col": "OCBL_TARGET", "actual_col": "OCBL.1", "enabled": True},
            "SRB10": {"name": "B10", "target_col": "SRB10_TARGET", "actual_col": "SRB10.1", "enabled": True},
            "SRB7": {"name": "B7", "target_col": "SRB7_TARGET", "actual_col": "SRB7.1", "enabled": True},
            "IQW": {"name": "Iconiq White", "target_col": "IQW_TARGET", "actual_col": "IQW.1", "enabled": True},
            "KYRON": {"name": "KYRON", "target_col": "KYRON_TARGET", "actual_col": "KYRON.1", "enabled": True},
            "OCBRANDY": {"name": "Officer's Choice Brandy", "target_col": "OCBRANDY_TARGET", "actual_col": "OCBRANDY.1", "enabled": True}
        }
    }
    
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            
        # Background migration: Upgrades old simple format to new advanced column-mapping
        # format, and defaults the per-brand 'enabled' toggle to True.
        needs_save = False
        for k, v in data.get("brands", {}).items():
            if isinstance(v, str):
                data["brands"][k] = {
                    "name": v,
                    "target_col": f"{k}_TARGET",
                    "actual_col": f"{k}.1",
                    "enabled": True
                }
                needs_save = True
            elif isinstance(v, dict) and "enabled" not in v:
                v["enabled"] = True
                needs_save = True
        
        if needs_save:
            with open(SETTINGS_FILE, "w") as fw:
                json.dump(data, fw, indent=4)
                
        return data
    else:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default_settings, f, indent=4)
        return default_settings

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings_data, f, indent=4)
    print("✅ Settings successfully saved!")

def manage_profile(settings):
    print("\n--- 👤 EDIT USER PROFILE ---")
    settings["profile"]["name"] = questionary.text("Enter Executive Name:", default=settings["profile"]["name"]).ask()
    settings["profile"]["designation"] = questionary.text("Enter Designation:", default=settings["profile"]["designation"]).ask()
    settings["profile"]["agency"] = questionary.text("Enter Agency/Distributor Name:", default=settings["profile"]["agency"]).ask()
    save_settings(settings)

def _detected_columns():
    """Best-effort column detection from the master file; returns (targets, actuals)
    or (None, None) when the files can't be read yet (user can still type names)."""
    try:
        df_sales, df_master = pipeline.load_dataframes(select_sales_file())
        return pipeline.detect_column_candidates(df_sales, df_master)
    except Exception:
        return None, None


def _validate_mapping_columns(settings):
    """Loads the current files and reports any brand column that does not exist
    in the actual data — the engine would silently zero those brands."""
    try:
        df_sales, df_master = pipeline.load_dataframes(select_sales_file())
    except Exception as e:
        print(f"⚠️ Could not validate mapping: {e}")
        return
    missing = pipeline.validate_brand_columns(settings, df_sales, df_master)
    if missing:
        print("\n❌ The following mapped columns are MISSING from the loaded files (brands will count as zero):")
        for m in missing:
            print(f"   • {m['brand']}: column '{m['column']}' missing from {m['file']}")
    else:
        print("\n✅ All mapped brand columns exist in the current files.")


def manage_brands(settings):
    while True:
        print("\n--- 🍾 MANAGE BRAND PORTFOLIO ---")
        action = questionary.select(
            "Choose an action:",
            choices=[
                "➕ Add a New Brand",
                "✏️ Edit an Existing Brand (Name & Column Mappings)",
                "🔕 Toggle Brand Enable/Disable (mute without removing)",
                "🔎 Validate Column Mapping Against Current Files",
                "❌ Remove a Brand",
                "🔙 Back to Main Menu"
            ]
        ).ask()

        if "Validate Column Mapping" in action:
            _validate_mapping_columns(settings)

        elif "Add" in action:
            b_code = questionary.text("Enter Brand Short Code (e.g., MH):").ask().strip().upper()
            if b_code:
                if b_code in settings["brands"]:
                    print(f"⚠️ Brand '{b_code}' already exists!")
                else:
                    b_name = questionary.text(f"Enter Full Display Name for {b_code}:").ask().strip()
                    print("\n[Column Mapping] Select from the detected columns, or type a custom name.")
                    tgt_candidates, act_candidates = _detected_columns()
                    tgt_default = f"{b_code}_TARGET"
                    if tgt_candidates and tgt_default in tgt_candidates:
                        tgt_default += " (detected)"
                    tgt_col = questionary.select(
                        f"Target Column in Master File (default {b_code}_TARGET):",
                        choices=[f"{b_code}_TARGET (type custom)"] + (tgt_candidates or [])
                    ).ask()
                    if "(type custom)" in tgt_col:
                        tgt_col = questionary.text("Type the exact target column name:",
                                                   default=f"{b_code}_TARGET").ask().strip()
                    act_col = questionary.select(
                        f"Actual Column in Sales Dump (default {b_code}.1):",
                        choices=[f"{b_code}.1 (type custom)"] + (act_candidates or [])
                    ).ask()
                    if "(type custom)" in act_col:
                        act_col = questionary.text("Type the exact actual column name:",
                                                   default=f"{b_code}.1").ask().strip()

                    settings["brands"][b_code] = {
                        "name": b_name,
                        "target_col": tgt_col,
                        "actual_col": act_col,
                        "enabled": True
                    }
                    save_settings(settings)
                    print(f"✅ Successfully added {b_code}: {b_name}")
                    
        elif "Toggle Brand" in action:
            if not settings["brands"]:
                print("No brands currently in portfolio.")
                continue
            b_code = questionary.select("Select brand to toggle:", choices=list(settings["brands"].keys())).ask()
            if b_code:
                b_data = settings["brands"][b_code]
                b_data["enabled"] = not b_data.get("enabled", True)
                save_settings(settings)
                state = "✅ ENABLED" if b_data["enabled"] else "🔕 MUTED (not dispatched)"
                print(f"🔄 Brand '{b_code}' is now {state}.")

        elif "Edit" in action:
            if not settings["brands"]:
                print("No brands currently in portfolio.")
                continue
            b_code = questionary.select("Select brand to edit:", choices=list(settings["brands"].keys())).ask()
            if b_code:
                b_data = settings["brands"][b_code]
                print(f"\nEditing configuration for: {b_code}")
                new_name = questionary.text(f"Display Name:", default=b_data["name"]).ask().strip()
                new_tgt = questionary.text(f"Master File Target Column Name:", default=b_data.get("target_col", f"{b_code}_TARGET")).ask().strip()
                new_act = questionary.text(f"Sales Dump Actual Column Name:", default=b_data.get("actual_col", f"{b_code}.1")).ask().strip()
                
                settings["brands"][b_code] = {
                    "name": new_name,
                    "target_col": new_tgt,
                    "actual_col": new_act,
                    "enabled": b_data.get("enabled", True)  # preserve mute state
                }
                save_settings(settings)
                print(f"✅ Updated configuration mapping for {b_code}")

        elif "Remove" in action:
            if not settings["brands"]:
                print("No brands currently in portfolio.")
                continue
            b_code = questionary.select("Select brand to remove:", choices=list(settings["brands"].keys())).ask()
            if b_code:
                confirm = questionary.confirm(f"Are you sure you want to completely remove '{b_code}' from tracking?").ask()
                if confirm:
                    del settings["brands"][b_code]
                    save_settings(settings)
                    print(f"🗑️ Removed brand '{b_code}' from the tracker.")

        elif "Back" in action:
            break

        elif "Back" in action:
            break

def resolve_dispatcher():
    """
    Returns the dispatch function matching DISPATCH_BACKEND (auto = Windows
    desktop on Windows, WhatsApp Web on Linux). dispatcher_web is imported
    lazily so the module stays importable on machines without selenium.
    """
    backend = (DISPATCH_BACKEND or "auto").strip().lower()
    if backend == "desktop" or (backend == "auto" and sys.platform == "win32"):
        if sys.platform != "win32":
            raise RuntimeError(
                "DISPATCH_BACKEND='desktop' needs Windows (os.startfile + WhatsApp Desktop). "
                "Use 'web' or 'auto' on this platform."
            )
        return dispatcher.process_dispatch_queue
    if backend == "web" or backend == "auto":
        import dispatcher_web
        return dispatcher_web.process_dispatch_queue_web
    raise ValueError(f"Unknown DISPATCH_BACKEND: '{DISPATCH_BACKEND}' (use auto, desktop or web)")


def select_sales_file(prefix=SALES_FILE_PREFIX):
    files = [f for f in os.listdir('.') if f.startswith(prefix) and f.endswith(SALES_FILE_EXTENSION)]
    if not files:
        raise FileNotFoundError(
            f"No '{prefix}*{SALES_FILE_EXTENSION}' files detected in your directory."
        )
    files.sort(reverse=True)
    return questionary.select("📅 Select the historical target report date file to process:", choices=files).ask()

def run_dispatch_engine(settings, company=None):
    """
    Interactive orchestration of the full dispatch run.

    Owns all user prompts (questionary) and I/O side effects; delegates the data
    processing to the pure, testable helpers in pipeline.py.
    """
    if not settings["brands"]:
        print("🛑 Your brand portfolio is empty! Please add brands via the Main Menu before running the engine.")
        return
    if not any(b.get("enabled", True) for b in settings["brands"].values()):
        print("🛑 All brands are muted (enabled=False). Enable at least one brand "
              "via 'Toggle Brand Enable/Disable' in Manage Brand Portfolio.")
        return

    prefix = (company or {}).get("sales_prefix") or SALES_FILE_PREFIX
    selected_file = select_sales_file(prefix)
    print(f"🔄 Ingesting chosen file target: {selected_file}")

    report_type = questionary.select(
        "📝 Select the type of WhatsApp communication to send:",
        choices=[
            "Daily Sales Progress Report (Invoiced / Balance)",
            "Start-of-Month Target Announcement"
        ]
    ).ask()

    report_date, file_date_str, remaining_days = pipeline.compute_run_dates(selected_file)

    if company:
        company_schema = (company.get("schema") or {})
        df_sales, df_master = pipeline.load_dataframes(
            selected_file,
            party_master=company.get("party_master"),
            sales_mapping=company_schema.get("sales") or {},
            party_mapping=company_schema.get("party") or {})
    else:
        df_sales, df_master = pipeline.load_dataframes(selected_file)

    available_depots = sorted([d for d in df_sales[COL_DEPOT].unique() if d])
    if not available_depots:
        raise ValueError("No valid depots found in the sales file.")

    selected_depots = questionary.checkbox(
        "🏢 Select the Depot(s) to process (Space to select, Enter to confirm):",
        choices=available_depots
    ).ask()

    if not selected_depots:
        print("🛑 No depots selected. Terminating run execution.")
        return

    df_sales = df_sales[df_sales[COL_DEPOT].isin(selected_depots)].copy()
    if df_sales.empty:
        raise ValueError("No transactions found for the selected depot(s).")

    # ==========================================
    # ADVANCED CUSTOM COLUMN MAPPING INJECTION
    # ==========================================
    # Surface silent mapping failures before the run (engine would zero the brands).
    missing_cols = pipeline.validate_brand_columns(settings, df_sales, df_master)
    if missing_cols:
        print("\n⚠️ The following mapped columns are MISSING from the loaded files "
              "(those brands will count as zero):")
        for m in missing_cols:
            print(f"   • {m['brand']}: column '{m['column']}' missing from {m['file']}")
        if not questionary.confirm("Continue anyway?").ask():
            print("🛑 Run aborted — fix the mapping in Manage Brand Portfolio first.")
            return

    brand_map, sales_brands, target_cols, market_names = pipeline.build_brand_map(settings)
    pipeline.cast_sales_columns(df_sales, sales_brands)
    pipeline.cast_target_columns(df_master, target_cols)

    actual_perf, brand_level_outlets = pipeline.aggregate_actuals(df_sales, sales_brands)

    filter_mode = questionary.select(
        "🎯 Select dispatch filter targeting rule strategy:",
        choices=[
            "All Eligible Accounts (Standard Automated Pacing Rules)",
            "Filter by Specific Priority Slabs (e.g., Priority A Only)",
            f"Accounts Below Achievement % (default {int(ELIGIBILITY_MAX_ACH_PCT)}%)",
            "Select Individual Group/Syndicates or Specific Outlets",
            "🧩 Custom Consolidation (Combine Cross-Syndicate Outlets for a Single Recipient)"
        ]
    ).ask()

    allowed_parties = None
    custom_run_config = None

    if "Priority Slabs" in filter_mode:
        target_priority = questionary.select("Select target priority tier:", choices=["A", "B", "C"]).ask()
        allowed_parties = set(df_master[df_master[COL_PRIORITY].str.upper() == target_priority][COL_PARTY])

    elif "Below Achievement" in filter_mode:
        max_ach = questionary.text(
            "Target accounts below what achievement %?",
            default=str(int(ELIGIBILITY_MAX_ACH_PCT))
        ).ask()
        try:
            max_ach = float(max_ach)
        except (TypeError, ValueError):
            print("🛑 Invalid percentage — aborting run.")
            return
        allowed_parties = pipeline.filter_parties_by_achievement(df_master, actual_perf, max_ach)
        if not allowed_parties:
            print(f"🛑 No accounts below {max_ach:.0f}% achievement — terminating run execution.")
            return

    elif "Individual Group" in filter_mode:
        all_master_options = sorted(list(df_master[COL_PARTY].unique()))
        chosen_groups = questionary.checkbox(
            "Select one or more accounts/groups to broadcast updates to:",
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
            choices=sorted(list(df_master[COL_PARTY].unique()))
        ).ask()

        selected_outlets = []

        if recipient in saved_groups:
            use_saved = questionary.confirm(
                f"💾 Found a saved custom group for '{recipient}' containing {len(saved_groups[recipient])} outlets. Use this saved group?"
            ).ask()
            if use_saved:
                selected_outlets = saved_groups[recipient]

        if not selected_outlets:
            all_outlets = sorted(list(df_sales[COL_VENDOR].unique()))
            selected_outlets = questionary.checkbox(
                f"🏪 Select ALL outlets to combine into this report (Showing outlets from {', '.join(selected_depots)}):",
                choices=all_outlets
            ).ask()

            if not selected_outlets:
                print("🛑 No outlets selected. Terminating run execution.")
                return

            save_preset = questionary.confirm(f"📝 Save this combination of {len(selected_outlets)} outlets for future use under '{recipient}'?").ask()
            if save_preset:
                saved_groups[recipient] = selected_outlets
                with open(config_file, "w") as json_file:
                    json.dump(saved_groups, json_file, indent=4)
                print(f"✅ Successfully saved custom group mapping for '{recipient}'.")

        custom_run_config = {
            "recipient": recipient,
            "outlets": selected_outlets
        }

    user_profile = settings["profile"]

    if custom_run_config:
        unordered_queue = [pipeline.build_custom_item(
            df_master, df_sales, brand_map, market_names, user_profile,
            report_type, report_date, remaining_days, custom_run_config
        )]
        dashboard_rows = []
        missing_contacts = []
    else:
        def drill_down_resolver(party, outlets):
            """Interactive outlet isolation for multi-outlet syndicates (used only in filtered modes)."""
            drill_down = questionary.confirm(
                f"🔎 Syndicate '{party}' contains multiple outlets. Do you want to isolate specific outlets from this group?"
            ).ask()
            if not drill_down:
                return None
            choices_outlets = [
                questionary.Choice(title=f"{o['vendor_name']} (MTD Vol: {o['total']})", value=o['vendor_name'])
                for o in outlets
            ]
            selected = questionary.checkbox("Select the outlets to include:", choices=choices_outlets).ask()
            return selected if selected is not None else []

        unordered_queue, dashboard_rows, missing_contacts = pipeline.build_regular_items(
            df_master, actual_perf, brand_level_outlets, brand_map, sales_brands,
            market_names, user_profile, report_type, report_date, remaining_days,
            allowed_parties=allowed_parties, drill_down_resolver=drill_down_resolver
        )

    if not custom_run_config and dashboard_rows:
        dashboard.export_territory_dashboard(dashboard_rows, file_date_str, brand_map.keys())

    pipeline.export_missing_contacts(missing_contacts, file_date_str)

    dispatch_queue = pipeline.build_dispatch_queue(unordered_queue)

    if TEST_MODE:
        dispatch_queue = dispatch_queue[:TEST_LIMIT]

    dispatch_fn = resolve_dispatcher()
    success, failed, skipped = dispatch_fn(
        dispatch_queue, WAIT_TIME, TAB_CLOSE, CLOSE_TIME, COOL_DOWN, MAX_RETRIES, FOCUS_TIMEOUT
    )
    print(f"\n🏁 Run Completed Cleanly. Success: {success} | Failed: {failed} | Skipped: {skipped}")

def main(company=None):
    settings = company if company else load_settings()

    while True:
        print("\n" + "="*40)
        print(" 🚀 WHATSAPP SALES AUTOMATION ENGINE")
        print("="*40)
        action = questionary.select(
            "Main Menu:",
            choices=[
                "📡 Run Sales Dispatch Engine",
                "👤 Edit My Profile (Name, Role, Agency)",
                "🍾 Manage Brand Portfolio",
                "❌ Exit"
            ]
        ).ask()

        if "Run Sales Dispatch" in action:
            run_dispatch_engine(settings)
            break
        elif "Edit My Profile" in action:
            manage_profile(settings)
        elif "Manage Brand Portfolio" in action:
            manage_brands(settings)
        else:
            print("Exiting Engine. Have a great day!")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhatsApp Sales Automation Engine")
    parser.add_argument("--company", default=None,
                        help="company slug (see companies/); defaults to the active company")
    args = parser.parse_args()
    company = None
    if args.company:
        import companies
        company = companies.load_company(args.company)
        if company is None:
            sys.exit(f"Unknown company '{args.company}' — available: {companies.list_companies()}")
    elif os.path.isdir("companies"):
        import companies
        slug = companies.ensure_default_company()
        company = companies.load_company(slug)
    main(company)
