from calculations import get_brand_status, get_pacing_recommendation


class TestGetBrandStatus:
    def test_green_at_exactly_90_percent(self):
        light, pct, balance = get_brand_status(100, 90)
        assert light == "🟢"
        assert pct == 90.0
        assert balance == 10

    def test_green_over_target_balance_never_negative(self):
        light, pct, balance = get_brand_status(100, 120)
        assert light == "🟢"
        assert pct == 120.0
        assert balance == 0

    def test_yellow_at_70_percent(self):
        light, _, _ = get_brand_status(100, 70)
        assert light == "🟡"

    def test_yellow_just_below_90(self):
        light, _, _ = get_brand_status(100, 89)
        assert light == "🟡"

    def test_red_below_70_percent(self):
        light, _, _ = get_brand_status(100, 69)
        assert light == "🔴"

    def test_zero_target_defaults_to_full(self):
        light, pct, balance = get_brand_status(0, 50)
        assert light == "🟢"
        assert pct == 100.0
        assert balance == 0

    def test_pct_rounding_to_one_decimal(self):
        _, pct, _ = get_brand_status(3, 1)
        assert pct == 33.3

    def test_partial_balance(self):
        _, _, balance = get_brand_status(150, 100)
        assert balance == 50


class TestGetPacingRecommendation:
    def test_critical_shortfall_over_250(self):
        result = get_pacing_recommendation(50, 300)
        assert "CRITICAL SHORTFALL EXPECTED" in result

    def test_warning_shortfall_over_100(self):
        result = get_pacing_recommendation(60, 150)
        assert "PACING BEHIND TARGET" in result

    def test_on_track_when_ach_high(self):
        result = get_pacing_recommendation(96, 50)
        assert "ON TRACK" in result

    def test_stable_pace_default(self):
        result = get_pacing_recommendation(80, 50)
        assert "STABLE PACE" in result

    def test_shortfall_priority_wins_over_ach(self):
        # Even a high-achieving account with a >250 shortfall gets the critical message.
        result = get_pacing_recommendation(98, 300)
        assert "CRITICAL SHORTFALL EXPECTED" in result
