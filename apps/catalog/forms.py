from __future__ import annotations

from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.forms import BaseInlineFormSet, inlineformset_factory
from PIL import Image, UnidentifiedImageError

from apps.catalog.models import Category, Product, ProductVariant


class OptimisticConcurrencyFormMixin(forms.ModelForm):
    revision = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial.setdefault("revision", self.instance.revision)

    def clean_revision(self) -> int:
        revision = self.cleaned_data.get("revision")
        if not self.instance.pk:
            return 1 if revision is None else revision
        if revision is None:
            raise ValidationError("Thiếu phiên bản dữ liệu. Vui lòng tải lại trang rồi thử lại.")
        current_revision = cast(
            int | None,
            type(self.instance)
            ._default_manager.filter(pk=self.instance.pk)
            .values_list("revision", flat=True)
            .first(),
        )
        if current_revision != revision:
            raise ValidationError(
                "Dữ liệu này đã được thay đổi trên thiết bị khác. Vui lòng tải lại rồi thử lại."
            )
        return cast(int, revision)


class BootstrapFormMixin:
    def apply_bootstrap_classes(self) -> None:
        for field in self.fields.values():  # type: ignore[attr-defined]
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class CategoryForm(OptimisticConcurrencyFormMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description", "active")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


class ProductForm(OptimisticConcurrencyFormMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ("category", "name", "brand", "color", "image", "description", "active")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}
        error_messages = {"image": {"invalid_image": "File tải lên không phải ảnh hợp lệ."}}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        category_field = self.fields["category"]
        if isinstance(category_field, forms.ModelChoiceField):
            category_field.queryset = Category.objects.filter(active=True)
        self.fields["image"].widget.attrs.update(
            {
                "accept": "image/jpeg,image/png,image/webp",
                "capture": "environment",
            }
        )

    def clean_image(self) -> Any:
        image = self.cleaned_data.get("image")
        if not image:
            return image
        if not isinstance(image, UploadedFile):
            return image
        if image.size is not None and image.size > 10 * 1024 * 1024:
            raise ValidationError("Ảnh không được lớn hơn 10 MB.")
        try:
            with Image.open(image) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValidationError("Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.")
                if source.width * source.height > 30_000_000:
                    raise ValidationError("Ảnh có độ phân giải quá lớn.")
                source.verify()
        except (OSError, UnidentifiedImageError) as error:
            raise ValidationError("File tải lên không phải ảnh hợp lệ.") from error
        finally:
            image.seek(0)
        return image


class ProductVariantForm(OptimisticConcurrencyFormMixin, BootstrapFormMixin, forms.ModelForm):
    initial_quantity = forms.IntegerField(
        label="Số lượng ban đầu",
        min_value=0,
        initial=0,
    )

    class Meta:
        model = ProductVariant
        fields = (
            "size",
            "sku",
            "cost_price",
            "selling_price",
            "low_stock_threshold",
            "active",
        )
        widgets = {
            "cost_price": forms.NumberInput(attrs={"min": 0, "step": 1000}),
            "selling_price": forms.NumberInput(attrs={"min": 0, "step": 1000}),
            "low_stock_threshold": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["initial_quantity"].initial = self.instance.quantity
            self.fields["initial_quantity"].disabled = True
            self.fields["initial_quantity"].label = "Tồn hiện tại"
        self.fields["size"].widget.attrs.update({"list": "default-sizes", "autocomplete": "off"})
        self.apply_bootstrap_classes()


class BaseProductVariantFormSet(BaseInlineFormSet):
    def clean(self) -> None:
        super().clean()
        if any(self.errors):
            return
        seen_sizes: set[str] = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            size = str(form.cleaned_data.get("size", "")).strip().casefold()
            if not size:
                continue
            if size in seen_sizes:
                raise ValidationError("Không được nhập hai biến thể cùng size.")
            seen_sizes.add(size)


ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    formset=BaseProductVariantFormSet,
    extra=1,
    can_delete=False,
    min_num=1,
    validate_min=True,
)


class InventoryAdjustmentForm(forms.Form):
    class Operation(models.TextChoices):
        ADD = "add", "Nhập thêm"
        SUBTRACT = "subtract", "Trừ số lượng"
        SET = "set", "Đặt số lượng chính xác"

    operation = forms.ChoiceField(label="Thao tác", choices=Operation.choices)
    quantity = forms.IntegerField(label="Số lượng", min_value=0)
    reason = forms.CharField(
        label="Lý do",
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        operation = cleaned_data.get("operation")
        quantity = cleaned_data.get("quantity")
        if operation in {self.Operation.ADD, self.Operation.SUBTRACT} and quantity == 0:
            self.add_error("quantity", "Số lượng phải lớn hơn 0 cho thao tác này.")
        return cleaned_data
