"""Notification and deduplicated low-stock warning services (Mục 7.7, 14 & UC-5.13)."""
from django.db.models import Q
from django.urls import reverse
from apps.accounts.models import User
from apps.inventory.models import TonKho
from apps.notifications.models import ThongBao


def create_notification(
    *,
    notification_type: str,
    title: str,
    content: str,
    recipient: User | None = None,
    branch=None,
    variant=None,
    related_entity_type: str = "",
    related_entity_id: int | None = None,
    target_url: str = "",
) -> ThongBao:
    return ThongBao.objects.create(
        nguoi_nhan=recipient,
        co_so=branch,
        bien_the=variant,
        loai_thong_bao=notification_type,
        tieu_de=title,
        noi_dung=content,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        target_url=target_url,
    )


def notify_users(
    *,
    users,
    notification_type: str,
    title: str,
    content: str,
    branch=None,
    variant=None,
    related_entity_type: str = "",
    related_entity_id: int | None = None,
    target_url: str = "",
) -> list[ThongBao]:
    created = []
    seen_ids = set()
    for user in users:
        if not user or not user.is_active or user.id in seen_ids:
            continue
        seen_ids.add(user.id)
        created.append(
            create_notification(
                recipient=user,
                branch=branch,
                variant=variant,
                notification_type=notification_type,
                title=title,
                content=content,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                target_url=target_url,
            )
        )
    return created


def notify_admins(
    *,
    notification_type: str,
    title: str,
    content: str,
    branch=None,
    related_entity_type: str = "",
    related_entity_id: int | None = None,
    target_url: str = "",
) -> list[ThongBao]:
    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    return notify_users(
        users=admins,
        notification_type=notification_type,
        title=title,
        content=content,
        branch=branch,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        target_url=target_url,
    )


def notify_branch_managers(
    *,
    branch,
    notification_type: str,
    title: str,
    content: str,
    variant=None,
    related_entity_type: str = "",
    related_entity_id: int | None = None,
    target_url: str = "",
) -> list[ThongBao]:
    target_users = User.objects.filter(
        (Q(role=User.Role.MANAGER, branch=branch) | Q(role=User.Role.ADMIN)),
        is_active=True,
    )
    if not target_users.exists():
        return [
            create_notification(
                recipient=None,
                branch=branch,
                variant=variant,
                notification_type=notification_type,
                title=title,
                content=content,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                target_url=target_url,
            )
        ]
    return notify_users(
        users=target_users,
        notification_type=notification_type,
        title=title,
        content=content,
        branch=branch,
        variant=variant,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        target_url=target_url,
    )


def sync_low_stock_alert(ton_kho: TonKho) -> None:
    """
    Evaluate `ton_kho` against `muc_ton_toi_thieu` (UC-5.13 & Section 14).
    - If `so_luong <= muc_ton_toi_thieu`: create or update an unresolved LOW_STOCK_ALERT
      for `(co_so, bien_the)` without creating duplicate unresolved warnings.
    - If `so_luong > muc_ton_toi_thieu`: mark any open alerts for `(co_so, bien_the)` as resolved.
    - If the product or variant is discontinued / inactive: automatically resolve any open alerts.
    """
    variant = ton_kho.bien_the
    product = variant.san_pham
    open_alerts = ThongBao.objects.filter(
        loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
        co_so=ton_kho.co_so,
        bien_the=variant,
        da_xu_ly=False,
    )

    if variant.trang_thai != "ACTIVE" or product.trang_thai != "ACTIVE":
        if open_alerts.exists():
            open_alerts.update(da_xu_ly=True, da_doc=True)
        return

    if ton_kho.so_luong > ton_kho.muc_ton_toi_thieu:
        if open_alerts.exists():
            open_alerts.update(da_xu_ly=True, da_doc=True)
        return

    status_label = "Hết hàng" if ton_kho.so_luong == 0 else "Sắp hết hàng"
    title = f"[{ton_kho.co_so.ma_co_so}] Cảnh báo {status_label.lower()}: {variant.ma_sku}"
    content = (
        f"Mã SP: {product.ma_san_pham} | SKU: {variant.ma_sku} ({product.ten_hang_hoa} - "
        f"{variant.mau_sac}/{variant.kich_co}) tại {ton_kho.co_so.ten_co_so}: "
        f"Tồn hiện tại = {ton_kho.so_luong} {product.don_vi_tinh} "
        f"(Định mức tối thiểu: {ton_kho.muc_ton_toi_thieu})."
    )
    try:
        target_url = f"{reverse('catalog:product_detail', args=[product.id])}?branch={ton_kho.co_so.id}"
    except Exception:
        target_url = "/catalog/"

    if open_alerts.exists():
        open_alerts.update(tieu_de=title, noi_dung=content, da_doc=False)
        return

    notify_branch_managers(
        branch=ton_kho.co_so,
        variant=variant,
        notification_type=ThongBao.NotificationType.LOW_STOCK_ALERT,
        title=title,
        content=content,
        related_entity_type="TonKho",
        related_entity_id=ton_kho.id,
        target_url=target_url,
    )
