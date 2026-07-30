from django.contrib import admin

from apps.core.models import ShopSecuritySettings


@admin.register(ShopSecuritySettings)
class ShopSecuritySettingsAdmin(admin.ModelAdmin):
    list_display = ("cost_price_lock_timeout_minutes", "updated_at")
    readonly_fields = ("cost_price_pin_hash", "created_at", "updated_at")

    def has_add_permission(self, request: object) -> bool:
        return not ShopSecuritySettings.objects.exists()

    def has_delete_permission(self, request: object, obj: object | None = None) -> bool:
        return False
