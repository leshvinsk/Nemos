from django.urls import re_path

from notifications.consumers import NotificationJobConsumer


websocket_urlpatterns = [
    re_path(r"ws/notifications/jobs/$", NotificationJobConsumer.as_asgi()),
]
