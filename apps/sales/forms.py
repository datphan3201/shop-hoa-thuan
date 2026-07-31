from __future__ import annotations

import json
from typing import Any

from django import forms

from apps.sales.models import Sale
from apps.sales.services import SaleLineInput


class SaleCreateForm(forms.Form):
    lines_json = forms.CharField(widget=forms.HiddenInput)
    discount_amount = forms.IntegerField(
        label="Giảm giá toàn giao dịch",
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 1000}),
    )
    payment_method = forms.ChoiceField(
        label="Phương thức thanh toán",
        choices=Sale.PaymentMethod.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    note = forms.CharField(
        label="Ghi chú",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._sale_lines: list[SaleLineInput] = []

    def clean_lines_json(self) -> str:
        raw_value = str(self.cleaned_data["lines_json"])
        try:
            payload = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise forms.ValidationError("Danh sách sản phẩm không hợp lệ.") from exc

        if not isinstance(payload, list) or not payload:
            raise forms.ValidationError("Giao dịch phải có ít nhất một sản phẩm.")

        lines: list[SaleLineInput] = []
        for raw_line in payload:
            if not isinstance(raw_line, dict):
                raise forms.ValidationError("Danh sách sản phẩm không hợp lệ.")
            variant_id = raw_line.get("variant_id")
            quantity = raw_line.get("quantity")
            actual_unit_price = raw_line.get("actual_unit_price")
            if (
                not isinstance(variant_id, int)
                or isinstance(variant_id, bool)
                or not isinstance(quantity, int)
                or isinstance(quantity, bool)
                or not isinstance(actual_unit_price, int)
                or isinstance(actual_unit_price, bool)
            ):
                raise forms.ValidationError("Sản phẩm, số lượng hoặc giá bán không hợp lệ.")
            lines.append(
                SaleLineInput(
                    variant_id=variant_id,
                    quantity=quantity,
                    actual_unit_price=actual_unit_price,
                )
            )
        self._sale_lines = lines
        return raw_value

    def get_sale_lines(self) -> list[SaleLineInput]:
        return list(self._sale_lines)


class SaleCancellationForm(forms.Form):
    reason = forms.CharField(
        label="Lý do hủy giao dịch",
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Ví dụ: Khách trả lại hàng",
            }
        ),
    )
