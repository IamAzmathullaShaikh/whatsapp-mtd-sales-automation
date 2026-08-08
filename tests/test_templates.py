from config import MESSAGE_FOOTER
from templates import _build_signature, build_whatsapp_message, build_monthly_target_message

PROFILE = {"name": "Azmathulla Sk", "designation": "Sales Executive", "agency": "Sri Krishna Agencies"}
MARKET = {"OCW": "Officer's Choice Whisky", "OCBL": "Officer's Choice Blue"}
BRANDS = [
    {"label": "OCW", "actual": 100, "balance": 50, "target": 150},
    {"label": "OCBL", "actual": 80, "balance": 0, "target": 80},
]


def _daily(**overrides):
    kwargs = dict(
        party_name="Party A", report_date="08-Aug-2026", total_target=230, total_actual=180,
        total_ach_pct=78.3, total_balance=50, remaining_days=24, required_drr=3,
        brand_strings=BRANDS, market_names=MARKET, user_profile=PROFILE,
    )
    kwargs.update(overrides)
    return build_whatsapp_message(**kwargs)


class TestBuildWhatsappMessage:
    def test_header_and_account_blocks(self):
        msg = _daily()
        assert "SRI KRISHNA AGENCIES" in msg
        assert "DAILY SALES PROGRESS REPORT" in msg
        assert "Party A" in msg
        assert "08-Aug-2026" in msg

    def test_brandwise_invoiced_and_balance_lines(self):
        msg = _daily()
        assert "Officer's Choice Whisky" in msg
        assert "100 Cases" in msg
        assert "50 Cases" in msg          # OCW balance line

    def test_completed_target_block(self):
        msg = _daily(total_balance=0, target_completed=True)
        assert "All brand targets fully completed!" in msg
        assert "Congratulations" in msg
        assert "Target Speed" not in msg

    def test_partial_target_has_drr_line(self):
        msg = _daily()
        assert "Target Speed" in msg
        assert "3 Cases daily" in msg
        assert "for the next 24 days" in msg

    def test_profile_signature_used(self):
        msg = _daily()
        assert "*Azmathulla Sk*" in msg
        assert "Sales Executive" in msg
        assert "*Sri Krishna Agencies*" in msg

    def test_fallback_signature_when_no_profile(self):
        msg = _daily(user_profile={})
        assert msg.endswith(MESSAGE_FOOTER.strip("\n"))
        assert "*Azmathulla Sk*" not in msg


class TestBuildMonthlyTargetMessage:
    def test_lists_positive_targets(self):
        msg = build_monthly_target_message("Party A", 230, BRANDS, MARKET, PROFILE)
        assert "MONTHLY SALES TARGET ANNOUNCEMENT" in msg
        assert "Officer's Choice Whisky" in msg
        assert "150 Cases" in msg
        assert "Officer's Choice Blue" in msg
        assert "80 Cases" in msg

    def test_zero_target_brand_omitted(self):
        msg = build_monthly_target_message(
            "Party A", 230, [{"label": "OCW", "target": 0}], MARKET, PROFILE
        )
        assert "Officer's Choice Whisky" not in msg

    def test_fallback_signature_when_no_profile(self):
        msg = build_monthly_target_message("Party A", 230, BRANDS, MARKET, None)
        assert msg.endswith(MESSAGE_FOOTER.strip("\n"))


class TestBuildSignature:
    def test_full_profile_signature(self):
        assert _build_signature(PROFILE) == (
            "Regards,\n*Azmathulla Sk*\nSales Executive\n*Sri Krishna Agencies*"
        )

    def test_partial_profile_omits_missing_fields(self):
        assert _build_signature({"name": "Bob"}) == "Regards,\n*Bob*"

    def test_empty_profile_falls_back_to_footer(self):
        assert _build_signature({}) == MESSAGE_FOOTER.strip("\n")

    def test_none_profile_falls_back_to_footer(self):
        assert _build_signature(None) == MESSAGE_FOOTER.strip("\n")
