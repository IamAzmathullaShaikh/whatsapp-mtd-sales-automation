import pandas as pd

from config import (
    COL_PARTY, COL_PHONE, COL_PRIORITY, COL_SEND, COL_SYNDICATE, COL_TOTAL,
    COL_VENDOR, INDIVIDUAL_SYNDICATE, SEND_YES, TOTAL_TARGET_COL,
)
from pipeline import (
    aggregate_actuals,
    build_brand_map,
    build_brand_strings,
    build_custom_item,
    build_dispatch_queue,
    build_regular_items,
    cast_sales_columns,
    cast_target_columns,
    compute_required_drr,
    compute_run_dates,
    export_missing_contacts,
    normalize_phone,
    render_message,
)

SETTINGS = {
    "brands": {
        "OCW": {"name": "Officer's Choice Whisky", "target_col": "OCW_TARGET", "actual_col": "OCW.1"},
        "OCBL": {"name": "Officer's Choice Blue", "target_col": "OCBL_TARGET", "actual_col": "OCBL.1"},
    }
}
PROFILE = {"name": "Azmathulla Sk", "designation": "Sales Executive", "agency": "Sri Krishna Agencies"}
BRAND_MAP = {"OCW": ("OCW_TARGET", "OCW.1")}
MARKET = {"OCW": "Officer's Choice Whisky"}


class TestNormalizePhone:
    def test_ten_digit_gets_country_code(self):
        assert normalize_phone("9876543210") == "+919876543210"

    def test_float_artifact_stripped(self):
        assert normalize_phone("9876543210.0") == "+919876543210"

    def test_eleven_digit_prefixed_without_country_guess(self):
        assert normalize_phone("919876543210") == "+919876543210"

    def test_empty_value(self):
        assert normalize_phone("") == ""
        assert normalize_phone(None) == ""


class TestComputeRequiredDrr:
    def test_exact_division(self):
        assert compute_required_drr(100, 10) == 10

    def test_rounds_up(self):
        assert compute_required_drr(101, 10) == 11

    def test_zero_remaining_days(self):
        assert compute_required_drr(100, 0) == 0

    def test_zero_balance(self):
        assert compute_required_drr(0, 10) == 0


class TestBuildBrandMap:
    def test_mappings_and_column_lists(self):
        brand_map, sales_brands, target_cols, market_names = build_brand_map(SETTINGS)
        assert brand_map == {
            "OCW": ("OCW_TARGET", "OCW.1"),
            "OCBL": ("OCBL_TARGET", "OCBL.1"),
        }
        assert sales_brands == ["OCW.1", "OCBL.1"]
        assert target_cols == [TOTAL_TARGET_COL, "OCW_TARGET", "OCBL_TARGET"]
        assert market_names["OCW"] == "Officer's Choice Whisky"


class TestCastColumns:
    def test_missing_sales_columns_created_as_zero(self):
        df = pd.DataFrame({"OCW.1": ["10", "20"], COL_TOTAL: ["5", "5"]})
        cast_sales_columns(df, ["OCW.1", "OCBL.1"])
        assert df["OCBL.1"].tolist() == [0, 0]
        assert df["OCW.1"].tolist() == [10, 20]
        assert df[COL_TOTAL].dtype == int

    def test_missing_target_columns_created_as_zero(self):
        df = pd.DataFrame({"OCW_TARGET": ["100", None]})
        cast_target_columns(df, [TOTAL_TARGET_COL, "OCW_TARGET"])
        assert df[TOTAL_TARGET_COL].tolist() == [0, 0]
        assert df["OCW_TARGET"].tolist() == [100, 0]


class TestAggregateActuals:
    def test_syndicates_and_individuals(self):
        df = pd.DataFrame({
            COL_SYNDICATE: ["SYN-A", "SYN-A", INDIVIDUAL_SYNDICATE, INDIVIDUAL_SYNDICATE],
            COL_VENDOR: ["Outlet1", "Outlet2", "Solo1", "Solo2"],
            "OCW.1": [10, 20, 5, 5],
            COL_TOTAL: [10, 20, 5, 5],
        })
        actual_perf, brand_level_outlets = aggregate_actuals(df, ["OCW.1"])
        assert actual_perf["SYN-A"]["OCW.1"] == 30
        assert actual_perf["SYN-A"]["TOTAL_ACTUAL"] == 30
        assert len(brand_level_outlets["SYN-A"]) == 2
        assert actual_perf["Solo1"]["OCW.1"] == 5
        assert actual_perf["Solo2"]["OCW.1"] == 5


class TestBuildDispatchQueue:
    def test_priority_a_first_then_ascending_ach(self):
        queue = [
            {"party": "Low", "priority": "B", "ach_pct": 10.0, "balance": 500, "message": ""},
            {"party": "High", "priority": "A", "ach_pct": 80.0, "balance": 50, "message": ""},
            {"party": "Mid", "priority": "A", "ach_pct": 50.0, "balance": 100, "message": ""},
        ]
        ordered = build_dispatch_queue(queue)
        assert [i["party"] for i in ordered] == ["Mid", "High", "Low"]


class TestBuildRegularItems:
    def _master(self):
        return pd.DataFrame({
            COL_PARTY: ["SYN-A", "Solo1", "NoData"],
            COL_PHONE: ["9876543210", "8765432109.0", "9999999999"],
            COL_SEND: [SEND_YES, SEND_YES, SEND_YES],
            COL_PRIORITY: ["A", "B", "C"],
            TOTAL_TARGET_COL: [100, 50, 60],
            "OCW_TARGET": [100, 50, 60],
        })

    def _actuals(self):
        return {
            "SYN-A": {"OCW.1": 30, "TOTAL_ACTUAL": 30},
            "Solo1": {"OCW.1": 50, "TOTAL_ACTUAL": 50},
        }, {
            "SYN-A": [
                {"vendor_name": "Outlet1", "data": {"OCW.1": 10}, "total": 10},
                {"vendor_name": "Outlet2", "data": {"OCW.1": 20}, "total": 20},
            ],
        }

    def test_queue_dashboard_and_missing_contacts(self):
        df_master = self._master()
        actual_perf, outlets = self._actuals()
        queue, dashboard, missing = build_regular_items(
            df_master, actual_perf, outlets, BRAND_MAP, ["OCW.1"],
            MARKET, PROFILE, "Daily Sales Progress Report (Invoiced / Balance)", "08-Aug-2026", 24,
        )
        # SYN-A (30% ach) qualifies; Solo1 (100% ach, no balance, priority B) does not.
        assert [i["party"] for i in queue] == ["SYN-A"]
        assert queue[0]["balance"] == 70
        assert len(dashboard) == 2
        assert missing[0]["PARTY"] == "NoData"
        assert missing[0]["PHONE"] == "+919999999999"

    def test_filtered_mode_includes_all_selected_parties(self):
        df_master = self._master()
        actual_perf, outlets = self._actuals()
        queue, _, _ = build_regular_items(
            df_master, actual_perf, outlets, BRAND_MAP, ["OCW.1"],
            MARKET, PROFILE, "Daily Sales Progress Report (Invoiced / Balance)", "08-Aug-2026", 24,
            allowed_parties={"SYN-A", "Solo1"},
        )
        assert [i["party"] for i in queue] == ["SYN-A", "Solo1"]

    def test_drill_down_resolver_isolates_outlets(self):
        df_master = self._master()
        actual_perf, outlets = self._actuals()
        queue, _, _ = build_regular_items(
            df_master, actual_perf, outlets, BRAND_MAP, ["OCW.1"],
            MARKET, PROFILE, "Daily Sales Progress Report (Invoiced / Balance)", "08-Aug-2026", 24,
            allowed_parties={"SYN-A", "Solo1"},
            drill_down_resolver=lambda party, o: ["Outlet2"],
        )
        assert queue[0]["party"] == "SYN-A"
        assert queue[0]["balance"] == 100 - 20  # only Outlet2's volume counted

    def test_drill_down_empty_selection_skips_party(self):
        df_master = self._master()
        actual_perf, outlets = self._actuals()
        queue, _, _ = build_regular_items(
            df_master, actual_perf, outlets, BRAND_MAP, ["OCW.1"],
            MARKET, PROFILE, "Daily Sales Progress Report (Invoiced / Balance)", "08-Aug-2026", 24,
            allowed_parties={"SYN-A", "Solo1"},
            drill_down_resolver=lambda party, o: [],
        )
        assert [i["party"] for i in queue] == ["Solo1"]


class TestBuildCustomItem:
    def test_consolidates_selected_outlets_for_recipient(self):
        df_master = pd.DataFrame({
            COL_PARTY: ["Head Office"],
            COL_PHONE: ["9876543210"],
            COL_PRIORITY: ["A"],
            TOTAL_TARGET_COL: [100],
            "OCW_TARGET": [100],
        })
        df_sales = pd.DataFrame({
            COL_VENDOR: ["Outlet1", "Outlet2", "Other"],
            "OCW.1": [10, 20, 5],
            COL_TOTAL: [10, 20, 5],
        })
        item = build_custom_item(
            df_master, df_sales, BRAND_MAP, MARKET, PROFILE,
            "Daily Sales Progress Report (Invoiced / Balance)", "08-Aug-2026", 24,
            {"recipient": "Head Office", "outlets": ["Outlet1", "Outlet2"]},
        )
        assert item["party"] == "Head Office"
        assert item["phone"] == "+919876543210"
        assert item["balance"] == 70  # target 100 - actual 30
        assert item["ach_pct"] == 30.0


class TestRenderMessage:
    def test_daily_report_branch(self):
        msg = render_message(
            "Daily Sales Progress Report (Invoiced / Balance)", "Party A", "08-Aug-2026",
            230, 180, 78.3, 50, 24, 3,
            [{"label": "OCW", "actual": 100, "balance": 50, "target": 150}],
            MARKET, PROFILE,
        )
        assert "DAILY SALES PROGRESS REPORT" in msg
        assert "Target Speed" in msg

    def test_monthly_announcement_branch(self):
        msg = render_message(
            "Start-of-Month Target Announcement", "Party A", "08-Aug-2026",
            150, 0, 0.0, 150, 24, 7,
            [{"label": "OCW", "actual": 0, "balance": 150, "target": 150}],
            MARKET, PROFILE,
        )
        assert "MONTHLY SALES TARGET ANNOUNCEMENT" in msg
        assert "DAILY SALES PROGRESS REPORT" not in msg

    def test_completed_daily_message_sets_congratulations(self):
        msg = render_message(
            "Daily Sales Progress Report (Invoiced / Balance)", "Party A", "08-Aug-2026",
            150, 150, 100.0, 0, 24, 0,
            [{"label": "OCW", "actual": 150, "balance": 0, "target": 150}],
            MARKET, PROFILE,
        )
        assert "Congratulations" in msg


class TestBuildBrandStrings:
    def test_builds_status_entries_from_row_and_actuals(self):
        row = pd.Series({"OCW_TARGET": 150})
        strings = build_brand_strings(row, {"OCW.1": 100}, BRAND_MAP)
        assert strings == [{"label": "OCW", "actual": 100, "balance": 50, "target": 150}]


class TestComputeRunDates:
    def test_parses_date_and_remaining_days(self):
        report_date, file_date_str, remaining_days = compute_run_dates("Outlet_Wise_Sales_08-08-2026.xlsx")
        assert report_date == "08-Aug-2026"
        assert file_date_str == "2026-08-08"
        assert remaining_days == 24  # August has 31 days: (31 - 8) + 1


class TestExportMissingContacts:
    def test_writes_csv_under_logs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        export_missing_contacts([{"PARTY": "X", "PHONE": "+91", "PRIORITY": "A", "TARGET": 5}], "2026-08-08")
        assert (tmp_path / "logs" / "missing_contacts_2026-08-08.csv").exists()

    def test_empty_list_is_noop(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        export_missing_contacts([], "2026-08-08")
        assert not (tmp_path / "logs").exists()
