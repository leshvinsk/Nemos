from django.contrib import admin

from notifications.models import AttendanceRecord, NotificationJob, QRCheckInSession


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = ("job_type", "status", "activity", "audience", "created_at", "updated_at")
    list_filter = ("job_type", "status", "audience")
    search_fields = ("message", "result_message", "activity__ngo__name")


@admin.register(QRCheckInSession)
class QRCheckInSessionAdmin(admin.ModelAdmin):
    list_display = ("activity", "token", "is_live", "is_active", "created_at", "activated_at")
    list_filter = ("is_live", "is_active")
    search_fields = ("activity__ngo__name", "token")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "employee", "checked_in_at")
    list_filter = ("checked_in_at",)
    search_fields = ("employee__username", "session__activity__ngo__name")
