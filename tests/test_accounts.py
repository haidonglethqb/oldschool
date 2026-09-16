"""Tests for Authentication, Role-Based Access Control, and Branch Isolation (UC-1, UC-2, Scenario 2)."""
import pytest
from django.urls import reverse
from apps.accounts.models import User


@pytest.mark.django_db
class TestAuthenticationAndRBAC:
    def test_valid_login_and_logout_flow(self, client, users):
        """UC-1 & UC-2: User can log in with valid credentials and log out."""
        resp = client.post(
            reverse("accounts:login"),
            {"username": "manager_cs1", "password": users["password"]},
        )
        assert resp.status_code == 302
        assert resp.url == reverse("catalog:product_list")

        logout_get = client.get(reverse("accounts:logout"))
        assert logout_get.status_code == 200
        logout_post = client.post(reverse("accounts:logout"))
        assert logout_post.status_code == 302
        assert logout_post.url == reverse("accounts:login")

    def test_login_lockout_after_five_failed_attempts(self, client, users):
        """UC-1: Account locks temporarily after 5 consecutive failed password attempts."""
        for _ in range(5):
            resp = client.post(
                reverse("accounts:login"),
                {"username": "manager_cs1", "password": "WrongPassword!"},
            )
            assert resp.status_code == 200

        mgr = User.objects.get(username="manager_cs1")
        assert mgr.failed_login_attempts >= 5
        assert mgr.is_temporarily_locked() is True

        # Even with valid password, locked user is rejected
        resp_valid = client.post(
            reverse("accounts:login"),
            {"username": "manager_cs1", "password": users["password"]},
        )
        assert resp_valid.status_code == 200
        assert "khóa tạm thời" in resp_valid.content.decode("utf-8")

    def test_scenario_2_branch_isolation_blocks_other_branch_switch(self, client, users, branches):
        """Scenario 2: Manager of CS2 cannot switch context to CS1 or access CS1-only import screens."""
        client.force_login(users["mgr_cs2"])

        # Attempting to switch branch to CS1 must raise 403 PermissionDenied
        resp_switch = client.post(
            reverse("accounts:switch_branch"),
            {"branch_id": str(branches["CS1"].id)},
        )
        assert resp_switch.status_code == 403

        # Attempting to access CS1 import screen as CS2 manager must return 403
        resp_import = client.get(reverse("purchasing:import_list"))
        assert resp_import.status_code == 403

    def test_staff_blocked_from_management_screens(self, client, users):
        """Sales staff (STAFF) cannot access stocktakes, reports, or product creation."""
        client.force_login(users["staff_cs1"])
        assert client.get(reverse("stocktakes:stocktake_list")).status_code == 403
        assert client.get(reverse("reports:report_dashboard")).status_code == 403
        assert client.get(reverse("catalog:product_create")).status_code == 403

    def test_scenario_8_direct_unauthorized_post_blocked_for_staff_and_wrong_branch_manager(
        self, client, users, branches, supplier, sample_catalog
    ):
        """
        Scenario 8 & Mục 10:
        Verify that direct POST requests (bypassing UI buttons) from unauthorized roles
        or wrong-branch managers are rejected with HTTP 403 PermissionDenied.
        """
        from decimal import Decimal
        from apps.purchasing.services import ImportLineSpec, create_import_receipt
        from apps.sales_outbound.services import OutboundReceiptLineSpec, create_outbound_receipt
        from apps.stocktakes.services import StocktakeLineSpec, create_stocktake

        v_m = sample_catalog["v_m"]
        receipt = create_import_receipt(
            actor=users["mgr_cs1"],
            nha_cung_cap=supplier,
            ma_phieu_nhap_kho="PNK-RBAC-001",
            line_specs=[ImportLineSpec(variant_id=v_m.id, so_luong=5, don_gia=Decimal("200000"))],
        )
        out_cs1 = create_outbound_receipt(
            actor=users["mgr_cs1"],
            co_so=branches["CS1"],
            ma_phieu_xuat_hang_ban="PXB-RBAC-001",
            ten_khach_hang="Khách CS1",
            sdt="0905111222",
            dia_chi="Đà Nẵng",
            phuong_thuc_giao="COUNTER",
            line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=1)],
            finalize_immediately=False,
        )
        st_cs1 = create_stocktake(
            actor=users["mgr_cs1"],
            co_so=branches["CS1"],
            ma_kiem_ke="KK-RBAC-001",
            nguoi_kiem_ke="Quản lý CS1",
            muc_dich="Kiểm kê định kỳ",
            ghi_chu="",
            line_specs=[StocktakeLineSpec(variant_id=v_m.id, so_luong_thuc_te=20)],
        )

        # 1. STAFF attempting direct POST to approve/finalize/delete endpoints -> 403
        client.force_login(users["staff_cs1"])
        assert client.post(reverse("purchasing:import_approve", args=[receipt.id])).status_code == 403
        assert client.post(reverse("purchasing:import_delete", args=[receipt.id])).status_code == 403
        assert client.post(reverse("sales_outbound:outbound_finalize", args=[out_cs1.id])).status_code == 403
        assert client.post(reverse("sales_outbound:outbound_delete", args=[out_cs1.id])).status_code == 403
        assert client.post(reverse("stocktakes:stocktake_approve", args=[st_cs1.id])).status_code == 403

        # 2. CS1 Manager attempting Admin-only approval endpoints -> 403
        client.force_login(users["mgr_cs1"])
        assert client.post(reverse("purchasing:import_approve", args=[receipt.id])).status_code == 403
        assert client.post(reverse("purchasing:import_return", args=[receipt.id])).status_code == 403
        assert client.post(reverse("stocktakes:stocktake_approve", args=[st_cs1.id])).status_code == 403
        assert client.post(reverse("stocktakes:stocktake_reject", args=[st_cs1.id])).status_code == 403

        # 3. CS2 Manager attempting cross-branch ID-guessing on CS1 documents -> 403
        client.force_login(users["mgr_cs2"])
        assert client.get(reverse("sales_outbound:outbound_detail", args=[out_cs1.id])).status_code == 403
        assert client.post(reverse("sales_outbound:outbound_finalize", args=[out_cs1.id])).status_code == 403
        assert client.get(reverse("stocktakes:stocktake_detail", args=[st_cs1.id])).status_code == 403
