from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from stores.models import Store, Department


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PrepItem(TimeStampedModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="prep_items",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prep_items",
    )
    sku = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    allergen_info = models.TextField(blank=True)
    shelf_life_hours = models.PositiveIntegerField(default=24)
    storage_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("store", "name")

    def __str__(self):
        return self.name


class PrepTask(TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_PRINTED = "printed"
    STATUS_COMPLETED = "completed"
    STATUS_DISCARDED = "discarded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PRINTED, "Printed"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_DISCARDED, "Discarded"),
    ]

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="prep_tasks",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prep_tasks",
    )
    prep_item = models.ForeignKey(
        PrepItem,
        on_delete=models.CASCADE,
        related_name="prep_tasks",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=50, blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prepared_tasks",
    )
    prepared_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    batch_code = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-prepared_at"]

    def save(self, *args, **kwargs):
        if not self.expires_at and self.prepared_at and self.prep_item:
            self.expires_at = self.prepared_at + timedelta(hours=self.prep_item.shelf_life_hours)
        if not self.department and self.prep_item and self.prep_item.department:
            self.department = self.prep_item.department
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prep_item.name} - {self.prepared_at:%Y-%m-%d %H:%M}"