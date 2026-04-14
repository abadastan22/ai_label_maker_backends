from django.conf import settings
from django.db import models

from prep.models import PrepTask
from stores.models import Printer


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Label(TimeStampedModel):
    prep_task = models.OneToOneField(
        PrepTask,
        on_delete=models.CASCADE,
        related_name="label",
    )
    label_title = models.CharField(max_length=255)
    label_body = models.TextField(blank=True)
    ai_generated_text = models.TextField(blank=True)
    qr_payload = models.TextField(blank=True)
    paper_size = models.CharField(max_length=20, blank=True)
    rendered_html = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.label_title


class PrintJob(TimeStampedModel):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_PRINTED = "printed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_SENT, "Sent"),
        (STATUS_PRINTED, "Printed"),
        (STATUS_FAILED, "Failed"),
    ]

    printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_jobs",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_jobs_requested",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PrintJob #{self.pk} - {self.status}"


class PrintJobItem(TimeStampedModel):
    print_job = models.ForeignKey(
        PrintJob,
        on_delete=models.CASCADE,
        related_name="items",
    )
    label = models.ForeignKey(
        Label,
        on_delete=models.CASCADE,
        related_name="print_job_items",
    )
    copies = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("print_job", "label")

    def __str__(self):
        return f"Job {self.print_job_id} / Label {self.label_id}"