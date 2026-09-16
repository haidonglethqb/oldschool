"""Forms for Stocktake / Inventory Count Records."""
from django import forms


class StocktakeHeaderForm(forms.Form):
    ma_kiem_ke = forms.CharField(
        label="Mã biên bản kiểm kê",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Tự động sinh nếu để trống"}),
    )
    nguoi_kiem_ke = forms.CharField(
        label="Nhân sự kiểm đếm thực tế",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Họ tên người trực tiếp kiểm đếm"}),
    )
    muc_dich = forms.CharField(
        label="Mục đích kiểm kê",
        initial="Kiểm kê định kỳ cuối ngày",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    ghi_chu = forms.CharField(
        label="Ghi chú biên bản",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
