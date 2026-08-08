import os
import re
from datetime import datetime

# Filename date patterns, tried in order (first match wins). Order matters:
# 4-digit years before 2-digit years, day-first before ISO so "08-06-2026"
# stays day-first (the convention this project has always used).
_DATE_PATTERNS = [
    (r"(\d{2})[._-](\d{1,2})[._-](\d{4})", "%d-%m-%Y"),  # 08-06-2026 / 24.6.2026 / 08_06_2026
    (r"(\d{4})[._-](\d{2})[._-](\d{2})", "%Y-%m-%d"),    # 2026-06-08 (ISO)
    (r"(\d{2})[._-](\d{1,2})[._-](\d{2})", "%d-%m-%y"),  # 08-06-26 / 24.6.26
]


def parse_report_date(filename):
    """Dynamically parses and extracts the execution date context from target filename.

    Supports day-first (dd-mm-yyyy), ISO (yyyy-mm-dd), and 2-digit-year
    (dd-mm-yy) separators . _ - — whichever appears first in the name wins.
    Falls back to today when no date is found.
    """
    basename = os.path.basename(filename)
    for pattern, fmt in _DATE_PATTERNS:
        date_match = re.search(pattern, basename)
        if not date_match:
            continue
        groups = [g for g in date_match.groups() if g is not None]
        raw_date = "-".join(groups)
        try:
            parsed_dt = datetime.strptime(raw_date, fmt)
        except ValueError:
            continue
        return parsed_dt.strftime("%d-%b-%Y"), parsed_dt.strftime("%Y-%m-%d"), parsed_dt
    now = datetime.now()
    return now.strftime("%d-%b-%Y"), now.strftime("%Y-%m-%d"), now
