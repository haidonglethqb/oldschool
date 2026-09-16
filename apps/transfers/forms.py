"""Forms for Interbranch Transfers."""
from django import forms
from apps.branches.models import CoSo


class TransferCreateForm(forms.Form):
    ma_phieu_dieu_chuyen = forms.CharField(
        label="Mã phiếu điều chuyển",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Tự động sinh nếu để trống"}),
    )
    co_so_xuat = forms.ModelChoiceField(
        label="Cơ sở xuất hàng (Nguồn)",
        queryset=CoSo.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    co_so_nhan = forms.ModelChoiceField(
        label="Cơ sở nhận hàng (Đích)",
        queryset=CoSo.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ly_do = forms.CharField(
        label="Lý do điều chuyển",
        initial="Bổ sung tồn kho cơ sở thiếu hàng",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    ghi_chu = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def clean(self):
        cleaned = super().clean()
        src = cleaned.get("co_so_xuat")
        dst = cleaned.get("co_so_nhan")
        if src and dst and src.id == dst.id:
            raise forms.ValidationError("Cơ sở xuất và Cơ sở nhận phải khác nhau.")
        return cleaned
