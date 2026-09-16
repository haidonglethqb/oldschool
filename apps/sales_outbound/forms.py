"""Forms for Sales Outbound Requests & Receipts."""
from django import forms
from apps.sales_outbound.models import PhieuXuatHangBan, YeuCauXuatHang


class OutboundRequestForm(forms.Form):
    ten_khach_hang = forms.CharField(
        label="Tên khách hàng / Mã đơn",
        initial="Khách lẻ tại quầy",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    sdt_khach_hang = forms.CharField(
        label="Số điện thoại",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "SĐT khách hàng (nếu có)"}),
    )
    dia_chi_giao = forms.CharField(
        label="Địa chỉ nhận hàng",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Để trống nếu bán tại quầy"}),
    )
    phuong_thuc_giao = forms.ChoiceField(
        label="Hình thức bán / giao",
        choices=YeuCauXuatHang.DeliveryMethod.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ghi_chu = forms.CharField(
        label="Ghi chú yêu cầu",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


class OutboundReceiptHeaderForm(forms.Form):
    ma_phieu_xuat_hang_ban = forms.CharField(
        label="Mã phiếu xuất",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Tự động sinh nếu để trống"}),
    )
    ten_khach_hang = forms.CharField(
        label="Khách hàng / Người nhận",
        initial="Khách mua lẻ tại quầy",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    sdt = forms.CharField(
        label="Số điện thoại liên hệ",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    dia_chi = forms.CharField(
        label="Địa chỉ xuất / giao hàng",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phuong_thuc_giao = forms.ChoiceField(
        label="Phương thức giao nhận",
        choices=PhieuXuatHangBan.DeliveryMethod.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ghi_chu = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
