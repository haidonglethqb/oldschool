"""
Management command `seed_oldschool` (Mục 16 of System.md).
Idempotently seeds:
- 3 Đà Nẵng branches (CS1 Kho tổng, CS2, CS3)
- 7 role-based user accounts (Admin, 3 Branch Managers, 3 Branch Sales Staff)
- 3 Suppliers (NCC001, NCC002, NCC003)
- 6 Fashion Products (SP001..SP006) with 14 SKU Variants across colors & sizes
- Opening stock balances covering IN_STOCK, LOW_STOCK, and OUT_OF_STOCK
- Sample Import Receipts, Sales Outbound Requests & Receipts, Interbranch Transfers, Stocktakes, and Excel files
"""
from decimal import Decimal
from pathlib import Path
import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.catalog.models import BienThe, SanPham
from apps.inventory.services import ensure_stock_balance, set_opening_stock
from apps.purchasing.models import NhaCungCap, PhieuNhapKho
from apps.purchasing.services import ImportLineSpec, approve_import_receipt, create_import_receipt
from apps.sales_outbound.models import PhieuXuatHangBan, YeuCauXuatHang
from apps.sales_outbound.services import (
    OutboundReceiptLineSpec,
    OutboundRequestLineSpec,
    create_outbound_receipt,
    create_outbound_request,
)
from apps.stocktakes.models import KiemKe
from apps.stocktakes.services import StocktakeLineSpec, approve_stocktake, create_stocktake, reject_stocktake
from apps.transfers.models import PhieuDieuChuyen
from apps.transfers.services import (
    TransferRequestLineSpec,
    create_transfer_request,
    dispatch_transfer,
    receive_transfer,
)

DEFAULT_PASSWORD = "OldSchool@123"


class Command(BaseCommand):
    help = "Khởi tạo dữ liệu mẫu chuẩn cho hệ thống Quản lý kho Old School (Mục 16 System.md)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Bắt đầu khởi tạo dữ liệu Old School ==="))

        # 1. Branches (Mục 16.1)
        branches_spec = [
            {
                "ma_co_so": "CS1",
                "ten_co_so": "Cơ sở 1 - Hải Châu (Kho tổng)",
                "dia_chi": "423 Trưng Nữ Vương, Quận Hải Châu, TP. Đà Nẵng",
                "sdt": "02363888101",
                "is_central_warehouse": True,
            },
            {
                "ma_co_so": "CS2",
                "ten_co_so": "Cơ sở 2 - Thanh Khê",
                "dia_chi": "446 Điện Biên Phủ, Quận Thanh Khê, TP. Đà Nẵng",
                "sdt": "02363888102",
                "is_central_warehouse": False,
            },
            {
                "ma_co_so": "CS3",
                "ten_co_so": "Cơ sở 3 - Ngũ Hành Sơn",
                "dia_chi": "635 Ngô Quyền, Quận Ngũ Hành Sơn, TP. Đà Nẵng",
                "sdt": "02363888103",
                "is_central_warehouse": False,
            },
        ]
        branches = {}
        for bspec in branches_spec:
            branch, _ = CoSo.objects.update_or_create(
                ma_co_so=bspec["ma_co_so"],
                defaults=bspec,
            )
            branches[branch.ma_co_so] = branch

        cs1, cs2, cs3 = branches["CS1"], branches["CS2"], branches["CS3"]

        # 2. Users (Mục 16.2)
        users_spec = [
            ("admin_owner", "Nguyễn Văn Chủ (Admin)", User.Role.ADMIN, None, True),
            ("manager_cs1", "Trần Thị Quản Lý CS1", User.Role.MANAGER, cs1, False),
            ("manager_cs2", "Lê Văn Quản Lý CS2", User.Role.MANAGER, cs2, False),
            ("manager_cs3", "Phạm Thị Quản Lý CS3", User.Role.MANAGER, cs3, False),
            ("staff_cs1", "Hoàng Nhân Viên Bán Hàng CS1", User.Role.STAFF, cs1, False),
            ("staff_cs2", "Vũ Nhân Viên Bán Hàng CS2", User.Role.STAFF, cs2, False),
            ("staff_cs3", "Đặng Nhân Viên Bán Hàng CS3", User.Role.STAFF, cs3, False),
        ]
        users = {}
        for username, full_name, role, branch_obj, is_super in users_spec:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "full_name": full_name,
                    "role": role,
                    "branch": branch_obj,
                    "is_staff": True if is_super else False,
                    "is_superuser": is_super,
                    "is_active": True,
                    "failed_login_attempts": 0,
                    "locked_until": None,
                },
            )
            user.set_password(DEFAULT_PASSWORD)
            user.save()
            users[username] = user

        admin_user = users["admin_owner"]
        mgr_cs1 = users["manager_cs1"]
        mgr_cs2 = users["manager_cs2"]
        mgr_cs3 = users["manager_cs3"]
        staff_cs2 = users["staff_cs2"]

        # 3. Suppliers (Mục 16.3)
        suppliers_spec = [
            ("NCC001", "Xưởng May Vintage Đà Nẵng", "KCN Hòa Khánh, Quận Liên Chiểu, Đà Nẵng", "0905111222"),
            ("NCC002", "Công ty TNHH Thời trang Retro Sài Gòn", "128 Cách Mạng Tháng 8, Quận 3, TP.HCM", "0909333444"),
            ("NCC003", "Tổng Kho Phụ kiện & Denim Hà Nội", "45 Hàng Đào, Quận Hoàn Kiếm, Hà Nội", "0912555666"),
        ]
        suppliers = {}
        for code, name, addr, phone in suppliers_spec:
            sup, _ = NhaCungCap.objects.update_or_create(
                ma_nha_cung_cap=code,
                defaults={"ten_nha_cung_cap": name, "dia_chi": addr, "sdt": phone},
            )
            suppliers[code] = sup

        # 4. Products & Variants (Mục 16.4)
        catalog_spec = [
            (
                "SP001",
                "Áo khoác Bomber Old School",
                "Áo khoác",
                "Cái",
                Decimal("450000"),
                [
                    ("SP001-DEN-M", "Đen", "M", Decimal("450000"), {"CS1": 40, "CS2": 12, "CS3": 4}),
                    ("SP001-DEN-L", "Đen", "L", Decimal("450000"), {"CS1": 35, "CS2": 3, "CS3": 10}),
                    ("SP001-KEM-M", "Kem", "M", Decimal("460000"), {"CS1": 25, "CS2": 8, "CS3": 0}),
                ],
            ),
            (
                "SP002",
                "Áo sơ mi kẻ sọc cổ điển",
                "Áo nữ",
                "Cái",
                Decimal("280000"),
                [
                    ("SP002-XANH-S", "Xanh", "S", Decimal("280000"), {"CS1": 30, "CS2": 15, "CS3": 9}),
                    ("SP002-XANH-M", "Xanh", "M", Decimal("280000"), {"CS1": 28, "CS2": 5, "CS3": 11}),
                    ("SP002-TRANG-M", "Trắng", "M", Decimal("280000"), {"CS1": 20, "CS2": 0, "CS3": 7}),
                ],
            ),
            (
                "SP003",
                "Quần Jeans ống rộng Retro",
                "Quần nữ",
                "Cái",
                Decimal("390000"),
                [
                    ("SP003-XANH-M", "Xanh", "M", Decimal("390000"), {"CS1": 32, "CS2": 14, "CS3": 6}),
                    ("SP003-DEN-L", "Đen", "L", Decimal("390000"), {"CS1": 26, "CS2": 2, "CS3": 8}),
                ],
            ),
            (
                "SP004",
                "Chân váy xếp ly Tennis",
                "Váy nữ",
                "Cái",
                Decimal("250000"),
                [
                    ("SP004-TRANG-S", "Trắng", "S", Decimal("250000"), {"CS1": 30, "CS2": 10, "CS3": 12}),
                    ("SP004-DEN-M", "Đen", "M", Decimal("250000"), {"CS1": 24, "CS2": 9, "CS3": 3}),
                ],
            ),
            (
                "SP005",
                "Áo thun Graphic Vintage",
                "Áo thun",
                "Cái",
                Decimal("220000"),
                [
                    ("SP005-KEM-L", "Kem", "L", Decimal("220000"), {"CS1": 50, "CS2": 18, "CS3": 15}),
                    ("SP005-HONG-M", "Hồng", "M", Decimal("220000"), {"CS1": 22, "CS2": 4, "CS3": 0}),
                ],
            ),
            (
                "SP006",
                "Túi Tote Canvas Old School",
                "Phụ kiện",
                "Cái",
                Decimal("150000"),
                [
                    ("SP006-KEM-FS", "Kem", "Freesize", Decimal("150000"), {"CS1": 60, "CS2": 20, "CS3": 16}),
                    ("SP006-DEN-FS", "Đen", "Freesize", Decimal("150000"), {"CS1": 45, "CS2": 11, "CS3": 5}),
                ],
            ),
        ]

        variants_map = {}
        for p_code, p_name, p_group, p_unit, p_price, v_list in catalog_spec:
            product, _ = SanPham.objects.update_or_create(
                ma_san_pham=p_code,
                defaults={
                    "ten_hang_hoa": p_name,
                    "nhom_hang": p_group,
                    "don_vi_tinh": p_unit,
                    "don_gia_niem_yet": p_price,
                    "trang_thai": SanPham.Status.ACTIVE,
                    "ghi_chu": f"Sản phẩm chủ lực thuộc nhóm {p_group} của chuỗi Old School.",
                },
            )
            for sku, color, size, v_price, branch_qtys in v_list:
                variant, _ = BienThe.objects.update_or_create(
                    ma_sku=sku,
                    defaults={
                        "san_pham": product,
                        "mau_sac": color,
                        "kich_co": size,
                        "don_gia": v_price,
                        "trang_thai": BienThe.Status.ACTIVE,
                    },
                )
                variants_map[sku] = variant
                for b_code, qty in branch_qtys.items():
                    b_obj = branches[b_code]
                    ensure_stock_balance(b_obj, variant, min_threshold=5)
                    set_opening_stock(
                        branch=b_obj,
                        variant=variant,
                        quantity=qty,
                        actor=admin_user,
                        min_threshold=5,
                        notes=f"Tồn kho đầu kỳ tại {b_code}",
                    )

        # 5. Sample Import Receipts (Approved & Pending)
        if not PhieuNhapKho.objects.filter(ma_phieu_nhap_kho="PNK-DEMO-001").exists():
            r1 = create_import_receipt(
                actor=mgr_cs1,
                nha_cung_cap=suppliers["NCC001"],
                ma_phieu_nhap_kho="PNK-DEMO-001",
                ly_do_nhap="Nhập bổ sung lô Áo khoác Bomber & Áo sơ mi đầu tháng",
                line_specs=[
                    ImportLineSpec(variant_id=variants_map["SP001-DEN-M"].id, so_luong=10, don_gia=Decimal("280000")),
                    ImportLineSpec(variant_id=variants_map["SP002-XANH-S"].id, so_luong=15, don_gia=Decimal("170000")),
                ],
                submit_for_approval=True,
            )
            approve_import_receipt(actor=admin_user, receipt=r1)

        if not PhieuNhapKho.objects.filter(ma_phieu_nhap_kho="PNK-DEMO-002").exists():
            create_import_receipt(
                actor=mgr_cs1,
                nha_cung_cap=suppliers["NCC002"],
                ma_phieu_nhap_kho="PNK-DEMO-002",
                ly_do_nhap="Nhập hàng bộ sưu tập Retro mới (Đang chờ Chủ cửa hàng duyệt)",
                line_specs=[
                    ImportLineSpec(variant_id=variants_map["SP003-XANH-M"].id, so_luong=20, don_gia=Decimal("240000"), chiet_khau=Decimal("100000")),
                    ImportLineSpec(variant_id=variants_map["SP005-KEM-L"].id, so_luong=25, don_gia=Decimal("130000")),
                ],
                submit_for_approval=True,
            )

        # 6. Sample Sales Outbound Request & Receipts
        if not YeuCauXuatHang.objects.exists():
            create_outbound_request(
                actor=staff_cs2,
                co_so=cs2,
                ten_khach_hang="Chị Nguyễn Thị Minh Anh (Khách VIP CS2)",
                sdt_khach_hang="0905888999",
                phuong_thuc_giao=YeuCauXuatHang.DeliveryMethod.COUNTER,
                ghi_chu="Khách đang đợi lấy hàng tại quầy Thanh Khê",
                line_specs=[
                    OutboundRequestLineSpec(variant_id=variants_map["SP001-DEN-M"].id, so_luong=2),
                ],
            )

        if not PhieuXuatHangBan.objects.filter(ma_phieu_xuat_hang_ban="PXB-CS1-DEMO-001").exists():
            create_outbound_receipt(
                actor=mgr_cs1,
                co_so=cs1,
                ma_phieu_xuat_hang_ban="PXB-CS1-DEMO-001",
                ten_khach_hang="Anh Trần Quốc Bảo",
                sdt="0914222333",
                dia_chi="112 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
                phuong_thuc_giao=PhieuXuatHangBan.DeliveryMethod.COUNTER,
                line_specs=[
                    OutboundReceiptLineSpec(variant_id=variants_map["SP001-DEN-M"].id, so_luong=4),
                    OutboundReceiptLineSpec(variant_id=variants_map["SP006-KEM-FS"].id, so_luong=3),
                ],
                finalize_immediately=True,
            )

        if not PhieuXuatHangBan.objects.filter(ma_phieu_xuat_hang_ban="PXB-CS2-DEMO-002").exists():
            create_outbound_receipt(
                actor=mgr_cs2,
                co_so=cs2,
                ma_phieu_xuat_hang_ban="PXB-CS2-DEMO-002",
                ten_khach_hang="Chị Lê Thu Hà (Đơn giao hàng)",
                sdt="0935777888",
                dia_chi="88 Hàm Nghi, Thanh Khê, Đà Nẵng",
                phuong_thuc_giao=PhieuXuatHangBan.DeliveryMethod.DELIVERY,
                line_specs=[
                    OutboundReceiptLineSpec(variant_id=variants_map["SP002-XANH-S"].id, so_luong=2),
                ],
                finalize_immediately=False,
            )

        # 7. Sample Interbranch Transfers (In-transit & Received)
        if not PhieuDieuChuyen.objects.filter(ma_phieu_dieu_chuyen="PDC-CS1-CS2-DEMO-001").exists():
            t_in_transit = create_transfer_request(
                actor=mgr_cs2,
                co_so_xuat=cs1,
                co_so_nhan=cs2,
                ma_phieu_dieu_chuyen="PDC-CS1-CS2-DEMO-001",
                ly_do="Bổ sung Áo sơ mi trắng đang hết hàng tại CS2 Thanh Khê",
                line_specs=[
                    TransferRequestLineSpec(variant_id=variants_map["SP002-TRANG-M"].id, so_luong_yeu_cau=5),
                ],
            )
            dispatch_transfer(actor=mgr_cs1, transfer=t_in_transit)

        if not PhieuDieuChuyen.objects.filter(ma_phieu_dieu_chuyen="PDC-CS1-CS3-DEMO-002").exists():
            t_done = create_transfer_request(
                actor=mgr_cs3,
                co_so_xuat=cs1,
                co_so_nhan=cs3,
                ma_phieu_dieu_chuyen="PDC-CS1-CS3-DEMO-002",
                ly_do="Bổ sung Áo khoác Bomber Kem cho CS3 Ngũ Hành Sơn",
                line_specs=[
                    TransferRequestLineSpec(variant_id=variants_map["SP001-KEM-M"].id, so_luong_yeu_cau=4),
                ],
            )
            dispatch_transfer(actor=mgr_cs1, transfer=t_done)
            receive_transfer(actor=mgr_cs3, transfer=t_done)

        # 8. Sample Stocktake Records (Pending & Approved)
        if not KiemKe.objects.filter(ma_kiem_ke="KK-CS1-DEMO-001").exists():
            create_stocktake(
                actor=mgr_cs1,
                co_so=cs1,
                ma_kiem_ke="KK-CS1-DEMO-001",
                nguoi_kiem_ke="Trần Thị Quản Lý CS1",
                muc_dich="Kiểm kê định kỳ kệ Áo khoác & Phụ kiện tại Kho tổng",
                line_specs=[
                    StocktakeLineSpec(variant_id=variants_map["SP001-DEN-M"].id, so_luong_thuc_te=46, xu_ly="Khớp tồn kho"),
                    StocktakeLineSpec(variant_id=variants_map["SP006-KEM-FS"].id, so_luong_thuc_te=56, xu_ly="Thiếu 1 túi do trưng bày mẫu"),
                ],
            )

        if not KiemKe.objects.filter(ma_kiem_ke="KK-CS2-DEMO-002").exists():
            st2 = create_stocktake(
                actor=mgr_cs2,
                co_so=cs2,
                ma_kiem_ke="KK-CS2-DEMO-002",
                nguoi_kiem_ke="Lê Văn Quản Lý CS2",
                muc_dich="Kiểm kê cuối tuần tại Cơ sở 2 Thanh Khê",
                line_specs=[
                    StocktakeLineSpec(variant_id=variants_map["SP001-DEN-M"].id, so_luong_thuc_te=12, xu_ly="Khớp số liệu"),
                    StocktakeLineSpec(variant_id=variants_map["SP003-DEN-L"].id, so_luong_thuc_te=2, xu_ly="Sắp hết hàng, cần điều chuyển"),
                ],
            )
            approve_stocktake(actor=admin_user, stocktake=st2)

        # 9. Generate Sample Excel Files on Disk (`sample_data/excel/`)
        excel_dir = Path(settings.BASE_DIR) / "sample_data" / "excel"
        excel_dir.mkdir(parents=True, exist_ok=True)

        self._write_xlsx(
            excel_dir / "mau_nhap_kho.xlsx",
            ["Mã SKU", "Số lượng", "Đơn giá", "Chiết khấu", "Ghi chú"],
            [
                ["SP001-DEN-M", 15, 280000, 0, "Nhập lô mới"],
                ["SP004-TRANG-S", 20, 150000, 50000, "Nhập chân váy Tennis"],
            ],
        )
        self._write_xlsx(
            excel_dir / "mau_xuat_kho.xlsx",
            ["Mã SKU", "Số lượng", "Đơn giá", "Ghi chú"],
            [
                ["SP001-DEN-M", 2, 450000, "Xuất bán khách lẻ"],
                ["SP006-KEM-FS", 1, 150000, "Xuất kèm phụ kiện"],
            ],
        )
        self._write_xlsx(
            excel_dir / "mau_kiem_ke.xlsx",
            ["Mã SKU", "Số lượng thực tế", "Xử lý", "Ghi chú"],
            [
                ["SP001-DEN-M", 12, "Khớp", "Đã đếm đủ"],
                ["SP002-XANH-S", 14, "Kiểm tra lại kệ B2", "Chênh lệch 1 cái"],
            ],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "=== Hoàn tất khởi tạo dữ liệu mẫu Old School (3 cơ sở, 7 tài khoản, 6 SP / 14 SKU, đầy đủ phiếu mẫu & file Excel) ==="
            )
        )

    @staticmethod
    def _write_xlsx(path: Path, headers: list[str], rows: list[list]):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for r in rows:
            ws.append(r)
        wb.save(path)
