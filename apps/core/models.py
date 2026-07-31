from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)
    revision = models.PositiveBigIntegerField("Phiên bản bản ghi", default=1, editable=False)

    class Meta:
        abstract = True


class IdempotencyRecord(models.Model):
    """Server-side replay record for operations that must not be duplicated."""

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    operation = models.CharField(max_length=64)
    key = models.CharField(max_length=128)
    fingerprint = models.CharField(max_length=64)
    response_location = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "operation", "key"), name="idempotency_user_op_key"
            )
        ]

    def __str__(self) -> str:
        return f"{self.operation}:{self.key}"


class ShopSecuritySettings(TimeStampedModel):
    cost_price_pin_hash = models.CharField("Hash mã PIN giá vốn", max_length=256, blank=True)
    cost_price_lock_timeout_minutes = models.PositiveSmallIntegerField(
        "Thời gian tự khóa (phút)",
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
    )

    class Meta:
        verbose_name = "Thiết lập bảo mật shop"
        verbose_name_plural = "Thiết lập bảo mật shop"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cost_price_lock_timeout_minutes__gte=1)
                & models.Q(cost_price_lock_timeout_minutes__lte=120),
                name="security_timeout_between_1_and_120",
            )
        ]

    def __str__(self) -> str:
        return "Bảo mật Shop Hoà Thuận"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.pk = 1
        if self._state.adding and type(self).objects.filter(pk=1).exists():
            existing = type(self).objects.get(pk=1)
            self.created_at = existing.created_at
            self._state.adding = False
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "ShopSecuritySettings":
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
