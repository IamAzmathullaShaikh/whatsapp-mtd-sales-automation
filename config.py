# ==========================================================
# File & Path Settings
# ==========================================================
FILE = "OFFTAKE_24.6.26.xlsx"
PARTY_MASTER = "party_master.xlsx"
DEPOT = "Guntur-I"

# ==========================================================
# Excel Data Schema (rename here when the data source changes)
# ==========================================================
SALES_FILE_PREFIX = "Outlet_Wise_Sales_"   # Prefix of the daily sales dump files to auto-detect
SALES_FILE_EXTENSION = ".xlsx"
SALES_SHEET = "DATA"                       # Sheet inside the sales dump holding the transactions
SALES_HEADER_ROW = 4                        # 0-indexed header row of the sales dump

TOTAL_TARGET_COL = "TOTAL_TARGET"          # Master: overall monthly target column
COL_DEPOT = "Name Of Depot"                # Sales: depot owning the transaction
COL_SYNDICATE = "SYNDICATE NAME"           # Sales: group/syndicate of the row
COL_VENDOR = "VENDOR_NAME"                 # Sales: outlet/vendor of the row
COL_PARTY = "PARTY"                        # Master: account/party name (join key)
COL_SEND = "SEND"                          # Master: whether the account receives reports
COL_PRIORITY = "PRIORITY"                  # Master: priority slab (A/B/C)
COL_PHONE = "PHONE"                        # Master: contact phone number
COL_TOTAL = "Total"                        # Sales: total volume column

INDIVIDUAL_SYNDICATE = "INDIVIDUAL"        # Sales: sentinel for standalone outlets (compared as-is; case-sensitive)
SEND_YES = "YES"                           # Master: SEND value meaning "always report" (any case is fine)

# ==========================================================
# Windows WhatsApp Native Application Automation Configuration
# ==========================================================
WAIT_TIME = 10         # Time for Windows Desktop App to focus chat & paste text
COOL_DOWN = 3         # Cooldown spacing cushion between consecutive account dispatches
TAB_CLOSE = False     # Legacy Web setting (Safe to ignore for Windows App)
CLOSE_TIME = 0        # Legacy Web setting (Safe to ignore for Windows App)

# ==========================================================
# Run Controls & Execution Rules (REAL-TIME PRODUCTION MODE)
# ==========================================================
TEST_MODE = False     # Set to False to uncap queue and send to all distributors
TEST_LIMIT = 5        # Safely bypassed because TEST_MODE is False
MAX_RETRIES = 2       # Automated refocus attempts if a window cycle lags
FOCUS_TIMEOUT = 15    # Seconds to wait & verify the WhatsApp chat window is focused before sending
SKIP_DUPLICATE_PHONES = True

# ==========================================================
# Account Eligibility Rules ("All Eligible Accounts" filter)
# ==========================================================
# An account is messaged automatically when it is behind target (achievement %
# below ELIGIBILITY_MAX_ACH_PCT), has a balance above ELIGIBILITY_MIN_BALANCE,
# or is Priority A. Completed accounts stay quiet.
ELIGIBILITY_MAX_ACH_PCT = 90.0   # Below this achievement % an account needs a nudge
ELIGIBILITY_MIN_BALANCE = 100     # Above this remaining balance an account needs a nudge

# ==========================================================
# Dispatch Backend Selection (Windows Desktop vs Linux WhatsApp Web)
# ==========================================================
# "auto"    -> Windows uses the native desktop app; Linux uses WhatsApp Web (Selenium).
# "desktop" -> always the Windows Desktop URI dispatcher (os.startfile + whatsapp://).
# "web"     -> always the Linux WhatsApp Web dispatcher (Selenium + Chromium).
DISPATCH_BACKEND = "auto"

WEB_USER_DATA_DIR = ".whatsapp_web_profile"  # Persistent browser profile (keeps the WhatsApp Web login)
WEB_HEADLESS = False                          # Keep the browser visible so you can see what happens
WEB_LOGIN_TIMEOUT = 180                       # Seconds to wait for the QR-code scan on first run

# ==========================================================
# Dynamic Notifications Sign-Off
# ==========================================================
MESSAGE_FOOTER = """
Regards,
Sri Krishna Agencies
"""
