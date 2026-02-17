from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("admin/notifications/", views.admin_notifications, name="admin_notifications"),
    path("admin/notifications/schedule/", views.schedule, name="schedule"),
    path("admin/notifications/broadcast/", views.broadcast, name="broadcast"),
]

