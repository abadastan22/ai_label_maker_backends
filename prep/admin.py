from django.contrib import admin

from .models import PrepItem, PrepTask


@admin.register(PrepItem)
class PrepItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "sku",
        "store",
        "department",
        "shelf_life_hours",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "sku", "description", "ingredients", "allergen_info")
    list_filter = ("store", "department", "is_active")
    ordering = ("name",)


@admin.register(PrepTask)
class PrepTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "prep_item",
        "store",
        "department",
        "quantity",
        "unit",
        "prepared_by",
        "prepared_at",
        "expires_at",
        "status",
    )
    search_fields = ("prep_item__name", "batch_code", "notes", "prepared_by__username")
    list_filter = ("store", "department", "status", "prepared_at")
    ordering = ("-prepared_at",)