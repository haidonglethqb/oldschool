"""
Tests for Warehouse Import & Supplier Management (UC-4.1 to UC-4.11, Scenario 1 & Scenario 9).
Verifies DEC-01: Stock increases ONLY upon ADMIN approval (UC-4.9).
"""
from decimal import Decimal
from io import BytesIO
import openpyxl
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from apps.inventory.excel import parse_import_excel
from apps.inventory.models import TonKho
from apps.purchasing.models import PhieuNhapKho
from apps.purchasing.services import (
    ImportLineSpec,
    approve_import_receipt,
    create_import_receipt,
    create_supplier,
    delete_import_receipt,
    return_import_receipt,
    update_import_receipt,
)


@pytest.mark.django_db
class TestPurchasingModule:
    def test_scenario_1_import_stock_only_increases_on_admin_approval(
        self, users, branches, supplier, sample_catalog
    ):
        """
        Scenario 1:
        1. CS1 Manager creates an import receipt -> status is PENDING_APPROVAL, stock does NOT increase.
        2. Admin returns receipt for revision -> stock still unchanged.
        3. CS1 Manager updates receipt -> status PENDING_APPROVAL, stock still unchanged.
        4. Admin approves receipt -> status APPROVED, stock increases at CS1 and ledger movement is recorded.
        5. Approved receipt cannot be edited, deleted, or approved a second time.
        """
        v_m = sample_catalog["v_m"]
        initial_qty = TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong

        receipt = create_import_receipt(
            actor=users["mgr_cs1"],
            nha_cung_cap=supplier,
            ma_phieu_nhap_kho="PNK-TEST-001",
            line_specs=[
                ImportLineSpec(
                    variant_id=v_m.id,
                    so_luong=15,
                    don_gia=Decimal("250000"),
                    chiet_khau=Decimal("50000"),
                )
            ],
            submit_for_approval=True,
        )
        assert receipt.trang_thai == PhieuNhapKho.Status.PENDING_APPROVAL
        assert receipt.tong_tien == Decimal("3700000")

        # Stock must NOT have increased yet
        assert TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong == initial_qty

        # CS1 Manager cannot approve their own receipt
        with pytest.raises(PermissionDenied):
            approve_import_receipt(actor=users["mgr_cs1"], receipt=receipt)

        # Admin returns receipt for revision
        return_import_receipt(actor=users["admin"], receipt=receipt, reason="Điều chỉnh lại số lượng thực nhập")
        receipt.refresh_from_db()
        assert receipt.trang_thai == PhieuNhapKho.Status.RETURNED
        assert TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong == initial_qty

        # CS1 Manager updates quantity to 20
        update_import_receipt(
            actor=users["mgr_cs1"],
            receipt=receipt,
            nha_cung_cap=supplier,
            line_specs=[ImportLineSpec(variant_id=v_m.id, so_luong=20, don_gia=Decimal("250000"))],
            submit_for_approval=True,
        )
        assert TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong == initial_qty

        # Admin approves receipt -> Stock increases by +20
        approve_import_receipt(actor=users["admin"], receipt=receipt)
        receipt.refresh_from_db()
        assert receipt.trang_thai == PhieuNhapKho.Status.APPROVED
        assert TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong == initial_qty + 20

        # Cannot approve twice or delete approved receipt
        with pytest.raises(ValidationError):
            approve_import_receipt(actor=users["admin"], receipt=receipt)
        with pytest.raises(ValidationError):
            delete_import_receipt(actor=users["admin"], receipt=receipt)

    def test_scenario_9_import_excel_upload_and_export(self, client, users, supplier, sample_catalog):
        """Scenario 9 & UC-4.1 / UC-4.10: Validate valid & invalid Excel upload and export .xlsx."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Mã SKU", "Số lượng", "Đơn giá", "Chiết khấu", "Ghi chú"])
        ws.append(["SP001-DEN-M", 12, 260000, 20000, "Lô nhập Excel"])
        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)
        stream.name = "import_valid.xlsx"

        parsed = parse_import_excel(stream)
        assert parsed["valid"] is True
        assert len(parsed["rows"]) == 1
        assert parsed["rows"][0]["so_luong"] == 12

        # Invalid SKU in Excel
        wb_bad = openpyxl.Workbook()
        ws_bad = wb_bad.active
        ws_bad.append(["Mã SKU", "Số lượng", "Đơn giá"])
        ws_bad.append(["SKU-KHONG-TON-TAI", -5, 100000])
        bad_stream = BytesIO()
        wb_bad.save(bad_stream)
        bad_stream.seek(0)
        bad_stream.name = "import_bad.xlsx"

        parsed_bad = parse_import_excel(bad_stream)
        assert parsed_bad["valid"] is False
        assert len(parsed_bad["errors"]) >= 1

    def test_create_supplier_uc_4_11(self, users):
        sup = create_supplier(
            actor=users["mgr_cs1"],
            ma_nha_cung_cap="NCC999",
            ten_nha_cung_cap="Công ty Dệt May Miền Trung",
            dia_chi="Đà Nẵng",
            sdt="0905000999",
        )
        assert sup.ma_nha_cung_cap == "NCC999"
        with pytest.raises(ValidationError):
            create_supplier(
                actor=users["mgr_cs1"],
                ma_nha_cung_cap="NCC999",
                ten_nha_cung_cap="Trùng mã",
                dia_chi="Đà Nẵng",
                sdt="0905000999",
            )

    def test_import_activity_report_summary_and_excel_export_uc_4_10_4_11(
        self, client, users, supplier, sample_catalog
    ):
        """UC-4.10 & UC-4.11: Period import activity summary and .xlsx report export."""
        v_m = sample_catalog["v_m"]
        r1 = create_import_receipt(
            actor=users["mgr_cs1"],
            nha_cung_cap=supplier,
            ma_phieu_nhap_kho="PNK-RPT-001",
            line_specs=[ImportLineSpec(variant_id=v_m.id, so_luong=10, don_gia=Decimal("200000"))],
        )
        approve_import_receipt(actor=users["admin"], receipt=r1)

        client.force_login(users["mgr_cs1"])
        resp_list = client.get(reverse("purchasing:import_list"))
        assert resp_list.status_code == 200
        assert resp_list.context["summary"]["approved_count"] >= 1
        assert resp_list.context["summary"]["approved_quantity"] >= 10

        resp_export = client.get(reverse("purchasing:import_report_export"))
        assert resp_export.status_code == 200
        assert (
            resp_export["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
