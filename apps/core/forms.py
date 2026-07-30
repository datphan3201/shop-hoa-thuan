from typing import Any, cast

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


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
