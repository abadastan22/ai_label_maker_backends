from django.urls import path

from .consumers import PrintJobConsumer

websocket_urlpatterns = [
    path("ws/print-jobs/", PrintJobConsumer.as_asgi()),
]