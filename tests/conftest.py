"""Shared Pytest fixtures for the Old School Inventory & Supply Chain test suite."""
from decimal import Decimal
import pytest
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.catalog.services import create_product_with_variants
from apps.inventory.services import set_opening_stock
from apps.purchasing.models import NhaCungCap


@pytest.fixture
def branches(db):
    cs1 = CoSo.objects.create(
        ma_co_so="CS1",
        ten_co_so="Cơ sở 1 - Hải Châu (Kho tổng)",
        dia_chi="423 Trưng Nữ Vương, Đà Nẵng",
        sdt="02363888101",
        is_central_warehouse=True,
    )
    cs2 = CoSo.objects.create(
        ma_co_so="CS2",
        ten_co_so="Cơ sở 2 - Thanh Khê",
        dia_chi="446 Điện Biên Phủ, Đà Nẵng",
        sdt="02363888102",
        is_central_warehouse=False,
    )
    cs3 = CoSo.objects.create(
        ma_co_so="CS3",
        ten_co_so="Cơ sở 3 - Ngũ Hành Sơn",
        dia_chi="635 Ngô Quyền, Đà Nẵng",
        sdt="02363888103",
        is_central_warehouse=False,
    )
    return {"CS1": cs1, "CS2": cs2, "CS3": cs3}


@pytest.fixture
def users(branches):
    pw = "OldSchool@123"
    admin = User.objects.create_user(
        username="admin_owner",
        password=pw,
        full_name="Chủ cửa hàng Admin",
        role=User.Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )
    mgr_cs1 = User.objects.create_user(
        username="manager_cs1",
        password=pw,
        full_name="Quản lý CS1",
        role=User.Role.MANAGER,
        branch=branches["CS1"],
    )
    mgr_cs2 = User.objects.create_user(
        username="manager_cs2",
        password=pw,
        full_name="Quản lý CS2",
        role=User.Role.MANAGER,
        branch=branches["CS2"],
    )
    mgr_cs3 = User.objects.create_user(
        username="manager_cs3",
        password=pw,
        full_name="Quản lý CS3",
        role=User.Role.MANAGER,
        branch=branches["CS3"],
    )
    staff_cs1 = User.objects.create_user(
        username="staff_cs1",
        password=pw,
        full_name="Nhân viên CS1",
        role=User.Role.STAFF,
        branch=branches["CS1"],
    )
    staff_cs2 = User.objects.create_user(
        username="staff_cs2",
        password=pw,
        full_name="Nhân viên CS2",
        role=User.Role.STAFF,
        branch=branches["CS2"],
    )
    return {
        "admin": admin,
        "mgr_cs1": mgr_cs1,
        "mgr_cs2": mgr_cs2,
        "mgr_cs3": mgr_cs3,
        "staff_cs1": staff_cs1,
        "staff_cs2": staff_cs2,
        "password": pw,
    }


@pytest.fixture
def supplier(db):
    return NhaCungCap.objects.create(
        ma_nha_cung_cap="NCC001",
        ten_nha_cung_cap="Xưởng May Vintage Đà Nẵng",
        dia_chi="KCN Hòa Khánh, Đà Nẵng",
        sdt="0905111222",
    )


@pytest.fixture
def sample_catalog(branches, users):
    product = create_product_with_variants(
        actor=users["admin"],
        ma_san_pham="SP001",
        ten_hang_hoa="Áo khoác Bomber Old School",
        nhom_hang="Áo khoác",
        don_vi_tinh="Cái",
        don_gia_niem_yet=Decimal("450000"),
        variants_data=[
            {"ma_sku": "SP001-DEN-M", "mau_sac": "Đen", "kich_co": "M", "don_gia": Decimal("450000"), "muc_ton_toi_thieu": 5},
            {"ma_sku": "SP001-DEN-L", "mau_sac": "Đen", "kich_co": "L", "don_gia": Decimal("450000"), "muc_ton_toi_thieu": 5},
        ],
        min_threshold=5,
    )
    v_m = BienThe.objects.get(ma_sku="SP001-DEN-M")
    v_l = BienThe.objects.get(ma_sku="SP001-DEN-L")

    set_opening_stock(branch=branches["CS1"], variant=v_m, quantity=30, actor=users["admin"])
    set_opening_stock(branch=branches["CS1"], variant=v_l, quantity=20, actor=users["admin"])
    set_opening_stock(branch=branches["CS2"], variant=v_m, quantity=10, actor=users["admin"])
    set_opening_stock(branch=branches["CS2"], variant=v_l, quantity=4, actor=users["admin"])
    set_opening_stock(branch=branches["CS3"], variant=v_m, quantity=0, actor=users["admin"])

    return {"product": product, "v_m": v_m, "v_l": v_l}
