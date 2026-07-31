from typing import Any, cast

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

from apps.core.models import ShopSecuritySettings


class OwnerAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Tên đăng nhập hoặc mật khẩu không chính xác.",
        "inactive": "Tài khoản này đã bị vô hiệu hóa.",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Tên đăng nhập"
        self.fields["password"].label = "Mật khẩu"
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "current-password"}
        )


class OwnerSetupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Tên đăng nhập"
        self.fields["password1"].label = "Mật khẩu"
        self.fields["password2"].label = "Nhập lại mật khẩu"
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def save(self, commit: bool = True) -> User:
        user = cast(User, super().save(commit=False))
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user


class PinUnlockForm(forms.Form):
    pin = forms.CharField(
        label="Mã PIN",
        min_length=4,
        max_length=12,
        strip=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "inputmode": "numeric", "autocomplete": "off"}
        ),
    )


class PinSetupForm(forms.Form):
    new_pin = forms.CharField(
        label="Mã PIN mới",
        min_length=4,
        max_length=12,
        widget=forms.PasswordInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )
    confirm_pin = forms.CharField(
        label="Nhập lại mã PIN",
        min_length=4,
        max_length=12,
        widget=forms.PasswordInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        new_pin = str(cleaned_data.get("new_pin", ""))
        if not new_pin.isdigit():
            self.add_error("new_pin", "Mã PIN chỉ được gồm chữ số.")
        if new_pin != cleaned_data.get("confirm_pin"):
            self.add_error("confirm_pin", "Mã PIN nhập lại không khớp.")
        return cleaned_data


class PinChangeForm(PinSetupForm):
    current_pin = forms.CharField(
        label="Mã PIN hiện tại",
        min_length=4,
        max_length=12,
        widget=forms.PasswordInput(attrs={"class": "form-control", "inputmode": "numeric"}),
    )


class SecurityTimeoutForm(forms.ModelForm):
    revision = forms.IntegerField(required=False, widget=forms.HiddenInput)
    cost_price_lock_timeout_minutes = forms.IntegerField(
        label="Tự khóa sau (phút)",
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 120}),
    )

    class Meta:
        model = ShopSecuritySettings
        fields = ("cost_price_lock_timeout_minutes",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial.setdefault("revision", self.instance.revision)

    def clean_revision(self) -> int:
        revision = self.cleaned_data.get("revision")
        if revision != self.instance.revision:
            raise forms.ValidationError(
                "Thiết lập đã thay đổi trên thiết bị khác. Vui lòng tải lại trang rồi thử lại."
            )
        return cast(int, revision)
