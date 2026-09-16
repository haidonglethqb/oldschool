"""Forms for Warehouse Import Receipts & Supplier Creation."""
from django import forms
from apps.purchasing.models import NhaCungCap, PhieuNhapKho


class SupplierForm(forms.ModelForm):
    class Meta:
        model = NhaCungCap
        fields = ["ma_nha_cung_cap", "ten_nha_cung_cap", "dia_chi", "sdt"]
        widgets = {
            "ma_nha_cung_cap": forms.TextInput(attrs={"class": "form-control", "placeholder": "VD: NCC004"}),
            "ten_nha_cung_cap": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên công ty / xưởng may"}),
            "dia_chi": forms.TextInput(attrs={"class": "form-control", "placeholder": "Địa chỉ nhà cung cấp"}),
            "sdt": forms.TextInput(attrs={"class": "form-control", "placeholder": "Số điện thoại liên hệ"}),
        }


class ImportReceiptHeaderForm(forms.Form):
    ma_phieu_nhap_kho = forms.CharField(
        label="Mã phiếu nhập kho",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Tự động sinh nếu để trống"}),
    )
    nha_cung_cap = forms.ModelChoiceField(
        label="Nhà cung cấp",
        queryset=NhaCungCap.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ly_do_nhap = forms.CharField(
        label="Lý do nhập kho",
        required=False,
        initial="Nhập hàng định kỳ từ nhà cung cấp",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    ghi_chu = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
