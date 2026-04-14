from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_print_job_update(print_job):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = {
        "type": "print_job.updated",
        "job": {
            "id": print_job.id,
            "status": print_job.status,
            "error_message": print_job.error_message,
            "updated_at": print_job.updated_at.isoformat() if print_job.updated_at else None,
        },
    }

    async_to_sync(channel_layer.group_send)(
        "print_jobs",
        {
            "type": "print_job_update",
            "payload": payload,
        },
    )