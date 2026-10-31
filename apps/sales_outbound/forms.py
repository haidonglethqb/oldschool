"""Forms for Sales Outbound Requests & Receipts."""
from django import forms
from apps.sales_outbound.models import PhieuXuatHangBan, YeuCauXuatHang


class OutboundRequestForm(forms.Form):
    ly_do_xuat = forms.CharField(
        label="Lý do xuất kho *",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "VD: Hết hàng trên kệ trưng bày / Khách hỏi mua cần lấy bổ sung...",
                "required": "required",
            }
        ),
        required=False,
    )
    ghi_chu_them = forms.CharField(
        label="Ghi chú thêm",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 2, "placeholder": "Ghi chú thêm nếu có..."}
        ),
    )
    # Backward-compatible fields
    ten_khach_hang = forms.CharField(required=False)
    sdt_khach_hang = forms.CharField(required=False)
    dia_chi_giao = forms.CharField(required=False)
    phuong_thuc_giao = forms.CharField(required=False)
    ghi_chu = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        ly_do = (
            cleaned_data.get("ly_do_xuat")
            or cleaned_data.get("ghi_chu")
            or cleaned_data.get("ten_khach_hang")
            or ""
        ).strip()
        if not ly_do:
            raise forms.ValidationError("Vui lòng nhập lý do xuất kho.")
        cleaned_data["ly_do_xuat"] = ly_do
        return cleaned_data


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
