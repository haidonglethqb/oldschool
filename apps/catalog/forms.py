from pathlib import Path
import re
import uuid
from django import forms
from django.core.files.uploadedfile import UploadedFile
from apps.catalog.models import SanPham


class ProductForm(forms.ModelForm):
    muc_ton_toi_thieu = forms.IntegerField(
        label="Định mức tồn tối thiểu (Cảnh báo sắp hết)",
        min_value=0,
        initial=5,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control os-input", "min": "0"}),
    )

    class Meta:
        model = SanPham
        fields = [
            "ma_san_pham",
            "ten_hang_hoa",
            "nhom_hang",
            "don_vi_tinh",
            "don_gia_niem_yet",
            "trang_thai",
            "hinh_anh",
            "ghi_chu",
        ]
        widgets = {
            "ma_san_pham": forms.TextInput(attrs={"class": "form-control os-input", "placeholder": "VD: SP001"}),
            "ten_hang_hoa": forms.TextInput(attrs={"class": "form-control os-input", "placeholder": "VD: Áo khoác Bomber"}),
            "nhom_hang": forms.TextInput(attrs={"class": "form-control os-input", "placeholder": "VD: Áo khoác, Áo nữ, Quần nữ..."}),
            "don_vi_tinh": forms.TextInput(attrs={"class": "form-control os-input", "placeholder": "VD: Cái"}),
            "don_gia_niem_yet": forms.NumberInput(attrs={"class": "form-control os-input", "min": "0"}),
            "trang_thai": forms.Select(attrs={"class": "form-select os-input"}),
            "hinh_anh": forms.ClearableFileInput(attrs={"class": "form-control os-input", "accept": "image/*"}),
            "ghi_chu": forms.Textarea(
                attrs={
                    "class": "form-control os-input",
                    "rows": 4,
                    "placeholder": "Nhập mô tả chất liệu, màu sắc, kích cỡ, đặc tính sản phẩm...",
                }
            ),
        }

    def clean_hinh_anh(self):
        image = self.cleaned_data.get("hinh_anh")
        if isinstance(image, UploadedFile) and image.name:
            parsed = Path(image.name)
            ext = parsed.suffix.lower()[:10]
            stem = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.stem).strip("._-") or "product"
            if len(f"products/{image.name}") > 180 or len(image.name) > 120:
                image.name = f"{stem[:60]}_{uuid.uuid4().hex[:8]}{ext}"
        return image
