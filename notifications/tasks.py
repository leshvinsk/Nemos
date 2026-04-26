import json
import time

from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from ngo.models import NGOAvailability
from notifications.models import NotificationJob


def _emit_job_update(job):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notification_jobs",
        {
            "type": "job.update",
            "message": {
                "id": job.id,
                "job_type": job.job_type,
                "status": job.status,
                "audience": job.audience,
                "activity": (
                    f"{job.activity.ngo.name} - {job.activity.service_type}"
                    if job.activity_id
                    else ""
                ),
                "result_message": job.result_message,
                "created_at": job.created_at.strftime("%Y-%m-%d %H:%M"),
            },
        },
    )


def _target_users(audience):
    User = get_user_model()
    qs = User.objects.filter(is_active=True)
    if audience == "employees":
        return qs.filter(is_staff=False)
    if audience == "staff":
        return qs.filter(is_staff=True)
    return qs


@shared_task
def process_broadcast_job(job_id):
    job = NotificationJob.objects.get(id=job_id)
    job.status = "Processing"
    job.save(update_fields=["status", "updated_at"])
    _emit_job_update(job)
    time.sleep(2)

    recipients = [user.email or f"{user.username}@nemos.local" for user in _target_users(job.audience)]
    send_mail(
        subject="NEMOS Broadcast",
        message=job.message,
        from_email=None,
        recipient_list=recipients or ["fallback@nemos.local"],
        fail_silently=False,
    )

    job.status = "Completed"
    job.result_message = f"Broadcast prepared for {len(recipients)} recipient(s)."
    job.save(update_fields=["status", "result_message", "updated_at"])
    _emit_job_update(job)


@shared_task
def process_activity_reminder(job_id):
    job = NotificationJob.objects.select_related("activity__ngo").get(id=job_id)
    job.status = "Processing"
    job.save(update_fields=["status", "updated_at"])
    _emit_job_update(job)
    time.sleep(2)

    activity = job.activity
    registrations = list(activity.registrations.select_related("employee"))
    recipients = [r.employee.email or f"{r.employee.username}@nemos.local" for r in registrations]
    message = job.message or (
        f"Reminder: {activity.ngo.name} - {activity.service_type} at {activity.location} "
        f"on {activity.service_date:%Y-%m-%d %H:%M}."
    )

    send_mail(
        subject="NEMOS Activity Reminder",
        message=message,
        from_email=None,
        recipient_list=recipients or ["fallback@nemos.local"],
        fail_silently=False,
    )

    job.status = "Completed"
    job.result_message = f"Reminder sent to {len(recipients)} registered participant(s)."
    job.save(update_fields=["status", "result_message", "updated_at"])
    _emit_job_update(job)


@shared_task
def scheduled_activity_reminder(activity_id, days_before_cutoff):
    activity = NGOAvailability.objects.select_related("ngo").get(id=activity_id, is_active=True)
    job = NotificationJob.objects.create(
        job_type="scheduled",
        status="Queued",
        activity=activity,
        audience="employees",
        message=(
            f"Scheduled reminder ({days_before_cutoff} day(s) before cutoff) for "
            f"{activity.ngo.name} - {activity.service_type}."
        ),
        result_message=f"Triggered by Celery Beat at {timezone.now():%Y-%m-%d %H:%M:%S}.",
    )
    _emit_job_update(job)
    process_activity_reminder.delay(job.id)
