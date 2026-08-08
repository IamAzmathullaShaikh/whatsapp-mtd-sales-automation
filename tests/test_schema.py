"""Tests for MTD / party schema detection (schema.py)."""

from openpyxl import Workbook

import schema
from config import COL_DEPOT, COL_PARTY, COL_TOTAL, COL_VENDOR


def _write(path, sheet_name, header_row_index, headers, rows, sheet2=False):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for _ in range(header_row_index):          # junk rows above the header
        ws.append(["Company confidential"])
    ws.append(headers)
    for r in rows:
        ws.append(r)
    if sheet2:
        ws2 = wb.create_sheet("Other")
        ws2.append(["unrelated", "data"])
    wb.save(path)


class TestDetectSalesSchema:
    def test_noncanonical_layout(self, tmp_path):
        """Different sheet name, junk rows, different spellings -> detected."""
        p = tmp_path / "mtd.xlsx"
        _write(p, "SalesData", 2,
               ["Depot Name", "Syndicate", "Vendor Name", "Total", "OCW", "OCBL"],
               [["Guntur-I", "SYN-A", "Outlet1", 100, 60, 40],
                ["Guntur-II", "SYN-B", "Outlet2", 200, 120, 80]])
        d = schema.detect_sales_schema(p)
        assert d is not None
        assert d["sheet"] == "SalesData"
        assert d["header_row"] == 2
        assert d["columns"]["depot"] == "Depot Name"
        assert d["columns"]["syndicate"] == "Syndicate"
        assert d["columns"]["vendor"] == "Vendor Name"
        assert d["columns"]["total"] == "Total"
        assert d["confidence"] == 1.0

    def test_canonical_layout(self, tmp_path):
        """The project's own format is detected with the canonical names."""
        p = tmp_path / "canonical.xlsx"
        _write(p, "DATA", 4,
               ["Name Of Depot", "SYNDICATE NAME", "VENDOR_NAME", "Total"],
               [["Guntur-I", "SYN-A", "Outlet1", 10]])
        d = schema.detect_sales_schema(p)
        assert d is not None
        assert d["header_row"] == 4
        assert d["columns"]["depot"] == "Name Of Depot"

    def test_no_match_returns_none(self, tmp_path):
        p = tmp_path / "nope.xlsx"
        _write(p, "Sheet1", 0, ["A", "B", "C"], [["1", "2", "3"]])
        assert schema.detect_sales_schema(p) is None

    def test_partial_match_needs_three_roles(self, tmp_path):
        p = tmp_path / "partial.xlsx"
        _write(p, "Data", 0, ["Depot", "Vendor"], [["X", "Y"]])
        assert schema.detect_sales_schema(p) is None  # only 2 roles


class TestDetectPartySchema:
    def test_detects_roles(self, tmp_path):
        p = tmp_path / "master.xlsx"
        _write(p, "Master", 0,
               ["Party", "Phone", "Send", "Priority", "Monthly Target"],
               [["SYN-A", "9876543210", "YES", "A", 100]])
        d = schema.detect_party_schema(p)
        assert d is not None
        assert d["columns"]["party"] == "Party"
        assert d["columns"]["phone"] == "Phone"
        assert d["columns"]["total_target"] == "Monthly Target"

    def test_no_match_returns_none(self, tmp_path):
        p = tmp_path / "nope.xlsx"
        _write(p, "Sheet1", 0, ["X", "Y"], [["1", "2"]])
        assert schema.detect_party_schema(p) is None


class TestApplyMapping:
    def test_maps_roles_to_canonical_names(self):
        rename = schema.apply_mapping(
            {"depot": "Depot Name", "vendor": "Vendor Name", "total": "Total"},
            ["Depot Name", "Vendor Name", "Total", "OCW.1"])
        assert rename[COL_DEPOT] == "Depot Name"
        assert rename[COL_VENDOR] == "Vendor Name"
        assert rename[COL_TOTAL] == "Total"
        assert COL_PARTY not in rename  # no party role given

    def test_skips_roles_absent_from_file(self):
        rename = schema.apply_mapping(
            {"depot": "Depot Name", "total": "Missing Total"},
            ["Depot Name"])
        assert COL_DEPOT in rename
        assert COL_TOTAL not in rename  # 'Missing Total' not in the file
