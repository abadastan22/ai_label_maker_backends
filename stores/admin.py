from django.contrib import admin

from .models import Store, Department, Printer


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "created_at", "updated_at")
    search_fields = ("code", "name", "address")
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "store", "is_active", "created_at")
    search_fields = ("name", "code", "store__name", "store__code")
    list_filter = ("is_active", "store")
    ordering = ("store__name", "name")


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "store",
        "driver_type",
        "paper_size",
        "ip_address",
        "port",
        "device_name",
        "is_default",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "description", "ip_address", "device_name", "store__name", "store__code")
    list_filter = ("store", "driver_type", "paper_size", "is_default", "is_active")
    ordering = ("store__name", "name")