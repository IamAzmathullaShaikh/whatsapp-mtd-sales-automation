import os
import re
from datetime import datetime

def parse_report_date(filename):
    """Dynamically parses and extracts the execution date context from target filename."""
    date_match = re.search(r"(\d{2})[._-](\d{2})[._-](\d{4})", os.path.basename(filename))
    if date_match:
        raw_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        parsed_dt = datetime.strptime(raw_date, "%d-%m-%Y")
        return parsed_dt.strftime("%d-%b-%Y"), parsed_dt.strftime("%Y-%m-%d"), parsed_dt
    else:
        now = datetime.now()
        return now.strftime("%d-%b-%Y"), now.strftime("%Y-%m-%d"), now
