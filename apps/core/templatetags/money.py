from django import template

register = template.Library()


@register.filter
def vnd(value: int | None) -> str:
    if value is None:
        return "Không có dữ liệu"
    return f"{value:,.0f}".replace(",", ".") + " ₫"
