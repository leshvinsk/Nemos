import secrets

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from ngo.models import NGOAvailability


class NotificationJob(models.Model):
    JOB_TYPES = [
        ("reminder", "Reminder"),
        ("broadcast", "Broadcast"),
        ("scheduled", "Scheduled Reminder"),
    ]
    STATUS_CHOICES = [
        ("Queued", "Queued"),
        ("Processing", "Processing"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Queued")
    activity = models.ForeignKey(
        NGOAvailability,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_jobs",
    )
    audience = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    result_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job_type} - {self.status} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class QRCheckInSession(models.Model):
    activity = models.ForeignKey(
        NGOAvailability,
        on_delete=models.CASCADE,
        related_name="qr_sessions",
    )
    token = models.CharField(max_length=64, unique=True, default="", editable=False)
    is_live = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(18)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.activity.ngo.name} QR session {self.created_at:%Y-%m-%d %H:%M:%S}"


class AttendanceRecord(models.Model):
    session = models.ForeignKey(
        QRCheckInSession,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    checked_in_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-checked_in_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "employee"],
                name="unique_attendance_per_session_employee",
            ),
        ]

    def __str__(self):
        return f"{self.employee.username} @ {self.session.activity.ngo.name}"
