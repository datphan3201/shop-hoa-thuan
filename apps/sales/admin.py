from django.contrib import admin

from apps.sales.models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product_variant",
        "product_name_snapshot",
        "category_name_snapshot",
        "size_snapshot",
        "color_snapshot",
        "sku_snapshot",
        "quantity",
        "listed_price",
        "actual_unit_price",
        "unit_cost_snapshot",
        "line_total",
        "created_at",
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "sale_code",
        "sold_at",
        "final_total",
        "payment_method",
        "status",
    )
    list_filter = ("status", "payment_method")
    search_fields = ("sale_code",)
    readonly_fields = (
        "sale_code",
        "sold_at",
        "subtotal",
        "discount_amount",
        "final_total",
        "payment_method",
        "note",
        "status",
        "cancelled_at",
        "cancellation_reason",
        "created_at",
        "updated_at",
    )
    inlines = (SaleItemInline,)

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False
