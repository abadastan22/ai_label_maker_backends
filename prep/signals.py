from django.db.models.signals import post_save
from django.dispatch import receiver

from labels.services import build_label_from_prep_task
from .models import PrepTask


@receiver(post_save, sender=PrepTask)
def create_or_update_label_for_prep_task(sender, instance, created, **kwargs):
    # Skip automatic label sync for one-click print generated tasks.
    # The endpoint handles label creation explicitly and transactionally.
    if getattr(instance, "_skip_auto_label_sync", False):
        return

    build_label_from_prep_task(instance)