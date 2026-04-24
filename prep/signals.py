from django.db.models.signals import post_save
from django.dispatch import receiver

from labels.services import build_label_from_prep_task
from .models import PrepTask


@receiver(post_save, sender=PrepTask)
def create_or_update_label_for_prep_task(sender, instance, created, **kwargs):
    if getattr(instance, "_skip_auto_label_sync", False):
        return

    build_label_from_prep_task(instance)