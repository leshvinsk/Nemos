from django.urls import path

from . import views

app_name = "registrations"

urlpatterns = [
    path("registrations/<int:activity_id>/register/", views.register, name="register"),
    path("registrations/<int:activity_id>/cancel/", views.cancel, name="cancel"),
    path("registrations/history/", views.my_history, name="my_history"),
    path("admin/monitor/", views.admin_monitor, name="admin_monitor"),
]

