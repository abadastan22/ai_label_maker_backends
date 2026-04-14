from django.contrib import admin

from .models import Label, PrintJob, PrintJobItem


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "label_title",
        "prep_task",
        "paper_size",
        "created_at",
        "updated_at",
    )
    search_fields = ("label_title", "label_body", "ai_generated_text", "prep_task__prep_item__name")
    list_filter = ("paper_size", "created_at")
    ordering = ("-created_at",)


class PrintJobItemInline(admin.TabularInline):
    model = PrintJobItem
    extra = 0


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "printer",
        "requested_by",
        "status",
        "created_at",
        "updated_at",
    )
    search_fields = ("printer__name", "requested_by__username", "error_message")
    list_filter = ("status", "printer", "created_at")
    ordering = ("-created_at",)
    inlines = [PrintJobItemInline]


@admin.register(PrintJobItem)
class PrintJobItemAdmin(admin.ModelAdmin):
    list_display = ("id", "print_job", "label", "copies", "created_at")
    search_fields = ("label__label_title",)
    list_filter = ("created_at",)
    ordering = ("-created_at",)