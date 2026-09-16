from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Tên đăng nhập",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control os-input",
                "placeholder": "Nhập tên đăng nhập...",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control os-input",
                "placeholder": "Nhập mật khẩu...",
                "autocomplete": "current-password",
            }
        ),
    )
