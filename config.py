# ==========================================================
# File & Path Settings
# ==========================================================
FILE = "OFFTAKE_24.6.26.xlsx"
PARTY_MASTER = "party_master.xlsx"
DEPOT = "Guntur-I"

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
SKIP_DUPLICATE_PHONES = True

# ==========================================================
# Dynamic Notifications Sign-Off
# ==========================================================
MESSAGE_FOOTER = """
Regards,
Sri Krishna Agencies
"""
