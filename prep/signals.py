from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PrepTask
from labels.services import build_label_from_prep_task


@receiver(post_save, sender=PrepTask)
def create_or_update_label_for_prep_task(sender, instance, **kwargs):
    build_label_from_prep_task(instance)