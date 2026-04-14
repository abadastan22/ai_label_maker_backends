from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Store(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(TimeStampedModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["store__name", "name"]
        unique_together = ("store", "name")

    def __str__(self):
        return f"{self.store.code} / {self.name}"


class Printer(TimeStampedModel):
    PAPER_SIZE_CHOICES = [
        ("2x1", '2" x 1"'),
        ("3x2", '3" x 2"'),
        ("4x2", '4" x 2"'),
        ("custom", "Custom"),
    ]

    DRIVER_TYPE_CHOICES = [
        ("mock_file", "Mock File"),
        ("raw_tcp", "Raw TCP"),
        ("zpl", "Zebra ZPL"),
        ("html_preview", "HTML Preview"),
        ("pdf_file", "PDF File"),
        ("windows_spooler", "Windows Spooler"),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="printers")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    driver_type = models.CharField(max_length=50, choices=DRIVER_TYPE_CHOICES, default="mock_file")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.PositiveIntegerField(default=9100)
    device_name = models.CharField(max_length=255, blank=True, help_text="OS-visible printer/spooler name when applicable")
    paper_size = models.CharField(max_length=20, choices=PAPER_SIZE_CHOICES, default="4x2")
    dpi = models.PositiveIntegerField(default=203)
    connection_options = models.JSONField(default=dict, blank=True, help_text="Driver-specific options like timeouts, queue names, media settings, etc.",)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["store__name", "name"]
        unique_together = ("store", "name")

    def __str__(self):
        return f"{self.store.code} - {self.name} ({self.driver_type})"