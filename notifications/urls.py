from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("admin/notifications/", views.admin_notifications, name="admin_notifications"),
    path("admin/notifications/jobs-status/", views.jobs_status, name="jobs_status"),
    path("admin/notifications/schedule/", views.schedule, name="schedule"),
    path("admin/notifications/broadcast/", views.broadcast, name="broadcast"),
    path("admin/notifications/qr-checkin/", views.qr_checkin, name="qr_checkin"),
    path("admin/notifications/qr-checkin/create/", views.create_qr_session, name="create_qr_session"),
    path("admin/notifications/qr-checkin/<int:session_id>/activate/", views.activate_qr_session, name="activate_qr_session"),
    path("admin/notifications/qr-checkin/<int:session_id>/status/", views.qr_session_status, name="qr_session_status"),
    path("qr/<str:token>/image/", views.qr_image, name="qr_image"),
    path("qr/<str:token>/", views.employee_checkin, name="employee_checkin"),
    path("qr/<str:token>/confirm/", views.confirm_employee_checkin, name="confirm_employee_checkin"),
]

