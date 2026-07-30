from django.contrib import admin

from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "active", "updated_at")
    list_filter = ("active",)
    search_fields = ("name",)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "color", "active", "updated_at")
    list_filter = ("active", "category")
    search_fields = ("name", "brand", "color", "variants__sku")
    inlines = (ProductVariantInline,)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "sku", "selling_price", "quantity", "active")
    list_filter = ("active", "size")
    search_fields = ("product__name", "sku")


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product_variant",
        "movement_type",
        "quantity_before",
        "quantity_change",
        "quantity_after",
        "created_at",
    )
    list_filter = ("movement_type",)
    search_fields = ("product_variant__product__name", "product_variant__sku", "note")
    readonly_fields = (
        "product_variant",
        "movement_type",
        "quantity_before",
        "quantity_change",
        "quantity_after",
        "reference_type",
        "reference_id",
        "note",
        "created_at",
    )

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False
