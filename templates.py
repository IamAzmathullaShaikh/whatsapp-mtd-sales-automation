from config import MESSAGE_FOOTER

def build_whatsapp_message(
    party_name,
    report_date,
    total_target,     
    total_actual,
    total_ach_pct,
    total_balance,
    remaining_days,
    required_drr,
    brand_strings,
    target_completed=False
):
    """
    Builds the daily tracking layout showing Invoiced and Balance volumes.
    """
    market_names = {
        "OCW": "Officer's Choice Whisky",
        "OCBL": "Officer's Choice Blue",
        "SRB10": "B10",
        "SRB7": "B7",
        "IQW": "Iconiq White",
        "KYRON": "KYRON",
        "OCBRANDY": "Officer's Choice Brandy"
    }

    invoiced_lines = []
    balance_lines = []

    for item in brand_strings:
        raw_code = item["label"].strip()
        actual = item["actual"]
        balance = item["balance"]

        full_brand_name = market_names.get(raw_code, raw_code)
        
        invoiced_lines.append(f"🔹 *{full_brand_name}* : {actual} Cases")
        
        if balance > 0:
            balance_lines.append(f"🔸 *{full_brand_name}* : {balance} Cases")

    # Dynamic closing block based on completion status
    if target_completed:
        balance_block = "✅ *All brand targets fully completed!*"
        drr_line = "🏆 *Congratulations! You have successfully achieved your 100% Monthly Target!*"
    elif not balance_lines:
        balance_block = "✅ *All brand targets fully completed!*"
        drr_line = ""
    else:
        balance_block = chr(10).join(balance_lines)
        drr_line = f"👉 *Target Speed:* Order an average of *{required_drr} Cases daily* for the next {remaining_days} days to complete target."

    return f"""📊 *SRI KRISHNA AGENCIES*
*DAILY SALES PROGRESS REPORT*
━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 *Report Date* : {report_date}
🏢 *Account* : {party_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 *BRANDWISE INVOICED VOLUME*

{chr(10).join(invoiced_lines)}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 *BRANDWISE BALANCE VOLUME*

{balance_block}

{drr_line}
━━━━━━━━━━━━━━━━━━━━━━━━━━
Regards,
*Azmathulla Sk*
Sales Executive
*Sri Krishna Agencies*"""


def build_monthly_target_message(party_name, total_target, brand_strings):
    """
    Builds a clean start-of-month target announcement layout for old-school retailers.
    """
    market_names = {
        "OCW": "Officer's Choice Whisky",
        "OCBL": "Officer's Choice Blue",
        "SRB10": "B10",
        "SRB7": "B7",
        "IQW": "Iconiq White",
        "KYRON": "KYRON",
        "OCBRANDY": "Officer's Choice Brandy"
    }

    target_lines = []

    for item in brand_strings:
        raw_code = item["label"].strip()
        target_val = item.get("target", 0)

        full_brand_name = market_names.get(raw_code, raw_code)
        
        if target_val > 0:
            target_lines.append(f"🎯 *{full_brand_name}* : {target_val} Cases")

    return f"""📊 *SRI KRISHNA AGENCIES*
*MONTHLY SALES TARGET ANNOUNCEMENT*
━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 *Account* : {party_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 *YOUR ALLOCATED TARGETS FOR THIS MONTH*

{chr(10).join(target_lines)}
━━━━━━━━━━━━━━━━━━━━━━━━━━
Regards,
*Azmathulla Sk*
Sales Executive
*Sri Krishna Agencies*"""
