"""
Tests for Interbranch Transfer Two-Step Stock Accounting (UC-5.3, Scenario 5).
"""
import pytest
from django.core.exceptions import ValidationError
from apps.inventory.models import TonKho
from apps.transfers.models import PhieuDieuChuyen
from apps.transfers.services import (
    TransferRequestLineSpec,
    accept_transfer,
    create_transfer_request,
    dispatch_transfer,
    receive_transfer,
)


@pytest.mark.django_db
class TestTransfersModule:
    def test_scenario_5_two_step_interbranch_transfer_accounting(
        self, users, branches, sample_catalog
    ):
        """
        Scenario 5:
        1. CS2 (stock=10 for v_m) requests 8 units from CS1 (stock=30 for v_m).
        2. At REQUESTED/ACCEPTED state, neither CS1 nor CS2 stock changes.
        3. CS1 dispatches the transfer (`DISPATCHED`) -> CS1 stock becomes 30 - 8 = 22;
           CS2 stock is STILL 10 (goods are in-transit).
        4. CS2 confirms receipt (`RECEIVED`) -> CS2 stock becomes 10 + 8 = 18.
        """
        cs1, cs2 = branches["CS1"], branches["CS2"]
        v_m = sample_catalog["v_m"]

        assert TonKho.objects.get(co_so=cs1, bien_the=v_m).so_luong == 30
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10

        transfer = create_transfer_request(
            actor=users["mgr_cs2"],
            co_so_xuat=cs1,
            co_so_nhan=cs2,
            ma_phieu_dieu_chuyen="PDC-TEST-001",
            ly_do="Bổ sung hàng tại CS2",
            line_specs=[TransferRequestLineSpec(variant_id=v_m.id, so_luong_yeu_cau=8)],
        )
        assert transfer.trang_thai == PhieuDieuChuyen.Status.REQUESTED
        assert TonKho.objects.get(co_so=cs1, bien_the=v_m).so_luong == 30
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10

        accept_transfer(actor=users["mgr_cs1"], transfer=transfer)
        dispatch_transfer(actor=users["mgr_cs1"], transfer=transfer)
        transfer.refresh_from_db()
        assert transfer.trang_thai == PhieuDieuChuyen.Status.DISPATCHED

        # Source deducted, destination NOT yet increased
        assert TonKho.objects.get(co_so=cs1, bien_the=v_m).so_luong == 22
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10

        # Destination confirms receipt
        receive_transfer(actor=users["mgr_cs2"], transfer=transfer)
        transfer.refresh_from_db()
        assert transfer.trang_thai == PhieuDieuChuyen.Status.RECEIVED
        assert TonKho.objects.get(co_so=cs1, bien_the=v_m).so_luong == 22
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 18

    def test_transfer_shortage_requires_note_and_adds_actual_received_only(
        self, users, branches, sample_catalog
    ):
        cs1, cs2 = branches["CS1"], branches["CS2"]
        v_m = sample_catalog["v_m"]

        transfer = create_transfer_request(
            actor=users["mgr_cs2"],
            co_so_xuat=cs1,
            co_so_nhan=cs2,
            line_specs=[TransferRequestLineSpec(variant_id=v_m.id, so_luong_yeu_cau=5)],
        )
        dispatch_transfer(actor=users["mgr_cs1"], transfer=transfer)
        line = transfer.lines.first()

        # Receiving 4 instead of 5 without note must raise ValidationError
        with pytest.raises(ValidationError):
            receive_transfer(
                actor=users["mgr_cs2"],
                transfer=transfer,
                received_quantities={line.id: 4},
                shortage_note="",
            )

        # With shortage note, status becomes RECEIVED_WITH_SHORTAGE and CS2 increases by +4
        receive_transfer(
            actor=users["mgr_cs2"],
            transfer=transfer,
            received_quantities={line.id: 4},
            shortage_note="Thiếu 1 áo do rách bao bì khi vận chuyển, trả về CS1",
        )
        transfer.refresh_from_db()
        assert transfer.trang_thai == PhieuDieuChuyen.Status.RECEIVED_WITH_SHORTAGE
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10 + 4

    def test_dispatch_exceeding_requested_quantity_blocked(
        self, users, branches, sample_catalog
    ):
        """Edge Case: Source branch cannot dispatch more units than requested on the transfer line."""
        cs1, cs2 = branches["CS1"], branches["CS2"]
        v_m = sample_catalog["v_m"]

        transfer = create_transfer_request(
            actor=users["mgr_cs2"],
            co_so_xuat=cs1,
            co_so_nhan=cs2,
            line_specs=[TransferRequestLineSpec(variant_id=v_m.id, so_luong_yeu_cau=4)],
        )
        line = transfer.lines.first()
        with pytest.raises(ValidationError):
            dispatch_transfer(
                actor=users["mgr_cs1"],
                transfer=transfer,
                dispatched_quantities={line.id: 6},
            )
