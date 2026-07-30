from __future__ import annotations

from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.catalog.models import Category, Product, ProductVariant


class BootstrapFormMixin:
    def apply_bootstrap_classes(self) -> None:
        for field in self.fields.values():  # type: ignore[attr-defined]
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description", "active")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ("category", "name", "brand", "color", "image", "description", "active")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        category_field = self.fields["category"]
        if isinstance(category_field, forms.ModelChoiceField):
            category_field.queryset = Category.objects.filter(active=True)

    def clean_image(self) -> Any:
        image = self.cleaned_data.get("image")
        if not image:
            return image
        if not isinstance(image, UploadedFile):
            return image
        if image.size is not None and image.size > 10 * 1024 * 1024:
            raise ValidationError("Ảnh không được lớn hơn 10 MB.")
        content_type = getattr(image, "content_type", "")
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValidationError("Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.")
        return image


class ProductVariantForm(BootstrapFormMixin, forms.ModelForm):
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
