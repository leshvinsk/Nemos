from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
import io
import qrcode

from accounts.permissions import admin_required, employee_required, is_employee
from ngo.models import NGOAvailability
from ngo.services.activity_service import ActivityService
from notifications.models import AttendanceRecord, NotificationJob, QRCheckInSession
from notifications.tasks import process_activity_reminder, process_broadcast_job
from registrations.models import Registration


CHECKIN_GRACE_MINUTES = 15


def _serialize_jobs(limit=20):
    jobs = NotificationJob.objects.select_related("activity__ngo")[:limit]
    return [
        {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "audience": job.audience,
            "activity": (
                f"{job.activity.ngo.name} - {job.activity.service_type}"
                if job.activity_id
                else ""
            ),
            "result_message": job.result_message or "Pending worker execution.",
            "created_at": job.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for job in jobs
    ]


def _build_public_absolute_uri(request, path):
    base_url = getattr(settings, "PUBLIC_BASE_URL", "")
    if base_url:
        return f"{base_url}{path}"
    current_host = request.get_host().split(":")[0]
    if current_host in {"127.0.0.1", "localhost"}:
        preferred_host = next(
            (
                host for host in getattr(settings, "ALLOWED_HOSTS", [])
                if host and host not in {"127.0.0.1", "localhost"}
            ),
            "",
        )
        if preferred_host:
            return f"{request.scheme}://{preferred_host}:8000{path}"
    return request.build_absolute_uri(path)


def _eligible_qr_activities():
    today = timezone.localdate()
    return list(
        NGOAvailability.objects.select_related("ngo")
        .filter(is_active=True, ngo__is_active=True)
        .filter(service_date__date=today)
        .annotate(registration_total=Count("registrations", distinct=True))
        .filter(registration_total__gt=0)
        .order_by("service_date", "ngo__name")
    )


def _checkin_window_is_open(activity):
    now = timezone.localtime(timezone.now())
    service_time = timezone.localtime(activity.service_date)
    if service_time.date() != now.date():
        return False
    latest_checkin = service_time + timezone.timedelta(minutes=CHECKIN_GRACE_MINUTES)
    return now <= latest_checkin

@admin_required
@require_GET
def admin_notifications(request):
    activities = ActivityService().list_all_admin()
    jobs = NotificationJob.objects.select_related("activity__ngo")[:20]
    return render(
        request,
        "notifications/admin_notifications.html",
        {"activities": activities, "jobs": jobs},
    )


@admin_required
@require_GET
def jobs_status(request):
    return JsonResponse({"jobs": _serialize_jobs()})


@admin_required
@require_GET
def qr_checkin(request):
    activities = _eligible_qr_activities()
    active_session = (
        QRCheckInSession.objects.select_related("activity__ngo")
        .prefetch_related("attendance_records__employee")
        .filter(is_active=True)
        .first()
    )
    return render(
        request,
        "notifications/qr_checkin.html",
        {
            "activities": activities[:10],
            "active_session": active_session,
        },
    )


def _serialize_session(session, request):
    registered_count = Registration.objects.filter(activity=session.activity).count()
    attendance = list(session.attendance_records.select_related("employee"))
    return {
        "id": session.id,
        "token": session.token,
        "is_live": session.is_live,
        "is_active": session.is_active,
        "activity_name": f"{session.activity.ngo.name} - {session.activity.service_type}",
        "service_date": session.activity.service_date.strftime("%Y-%m-%d %H:%M"),
        "registered_count": registered_count,
        "checked_in_count": len(attendance),
        "pending_count": max(registered_count - len(attendance), 0),
        "qr_url": _build_public_absolute_uri(request, reverse("notifications:qr_image", args=[session.token])),
        "scan_url": _build_public_absolute_uri(request, reverse("notifications:employee_checkin", args=[session.token])),
        "attendance": [
            {
                "employee": record.employee.username,
                "checked_in_at": timezone.localtime(record.checked_in_at).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for record in attendance
        ],
    }


@admin_required
@require_POST
def create_qr_session(request):
    activity_id = request.POST.get("activity_id")
    if not activity_id:
        return JsonResponse({"detail": "Please choose an activity."}, status=400)

    activity = next((item for item in _eligible_qr_activities() if str(item.id) == str(activity_id)), None)
    if activity is None:
        return JsonResponse(
            {"detail": "Only same-day activities with registered participants can open QR check-in."},
            status=400,
        )
    if not _checkin_window_is_open(activity):
        return JsonResponse(
            {
                "detail": (
                    f"QR check-in can only be opened on the activity date and no later than "
                    f"{CHECKIN_GRACE_MINUTES} minutes after the activity start time."
                )
            },
            status=400,
        )

    QRCheckInSession.objects.filter(is_active=True).update(is_active=False, is_live=False, closed_at=timezone.now())
    session = QRCheckInSession.objects.create(activity=activity)
    return JsonResponse(_serialize_session(session, request), status=201)


@admin_required
@require_POST
def activate_qr_session(request, session_id):
    session = get_object_or_404(QRCheckInSession, id=session_id, is_active=True)
    if not _checkin_window_is_open(session.activity):
        return JsonResponse(
            {"detail": f"Check-in is closed because the {CHECKIN_GRACE_MINUTES}-minute window has passed."},
            status=400,
        )
    if not session.is_live:
        session.is_live = True
        session.activated_at = timezone.now()
        session.save(update_fields=["is_live", "activated_at"])
    return JsonResponse(_serialize_session(session, request))


@admin_required
@require_GET
def qr_session_status(request, session_id):
    session = get_object_or_404(
        QRCheckInSession.objects.select_related("activity__ngo").prefetch_related("attendance_records__employee"),
        id=session_id,
    )
    return JsonResponse(_serialize_session(session, request))


@require_GET
def qr_image(request, token):
    session = get_object_or_404(QRCheckInSession, token=token, is_active=True)
    scan_url = _build_public_absolute_uri(request, reverse("notifications:employee_checkin", args=[session.token]))
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return JsonResponse({"detail": "QR image must be loaded as src via browser."}, status=405) if request.headers.get("X-Requested-With") == "XMLHttpRequest" else _png_response(buffer)


def _png_response(buffer):
    from django.http import HttpResponse

    return HttpResponse(buffer.getvalue(), content_type="image/png")


@require_GET
def employee_checkin(request, token):
    session = get_object_or_404(QRCheckInSession.objects.select_related("activity__ngo"), token=token, is_active=True)
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?next={request.path}"
        return redirect(login_url)
    if not is_employee(request.user):
        return HttpResponseForbidden("Employee access required.")

    registration_exists = Registration.objects.filter(employee=request.user, activity=session.activity).exists()
    existing = AttendanceRecord.objects.filter(session=session, employee=request.user).first()
    return render(
        request,
        "notifications/employee_checkin.html",
        {
            "session": session,
            "registration_exists": registration_exists,
            "existing_record": existing,
            "window_open": _checkin_window_is_open(session.activity),
        },
    )


@employee_required
def confirm_employee_checkin(request, token):
    session = get_object_or_404(QRCheckInSession.objects.select_related("activity__ngo"), token=token, is_active=True)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not session.is_live:
        messages.error(request, "This QR session is not live yet.")
        return redirect("notifications:employee_checkin", token=token)
    if not _checkin_window_is_open(session.activity):
        messages.error(request, f"Check-in is closed because the {CHECKIN_GRACE_MINUTES}-minute window has passed.")
        return redirect("notifications:employee_checkin", token=token)
    if not Registration.objects.filter(employee=request.user, activity=session.activity).exists():
        messages.error(request, "You are not registered for this activity.")
        return redirect("notifications:employee_checkin", token=token)

    _, created = AttendanceRecord.objects.get_or_create(session=session, employee=request.user)
    if not created:
        messages.warning(request, "Duplicate check-in prevented. You have already checked in.")
    else:
        messages.success(request, "Attendance recorded successfully.")
    return redirect("notifications:employee_checkin", token=token)


@admin_required
@require_POST
def schedule(request):
    activity_id = request.POST.get("activity_id")
    intervals = request.POST.getlist("intervals")

    if not activity_id:
        messages.error(request, "Please choose an activity.")
        return redirect("notifications:admin_notifications")

    selected_activity = next(
        (item for item in ActivityService().list_all_admin() if str(item.id) == str(activity_id)),
        None,
    )
    if selected_activity is None:
        messages.error(request, "Selected activity was not found.")
        return redirect("notifications:admin_notifications")

    if not intervals:
        job = NotificationJob.objects.create(
            job_type="reminder",
            status="Queued",
            activity=selected_activity,
            audience="employees",
            message=(
                f"Manual reminder for {selected_activity.ngo.name} - "
                f"{selected_activity.service_type}."
            ),
        )
        process_activity_reminder.delay(job.id)
        messages.success(request, "Immediate reminder queued for background processing.")
        return redirect("notifications:admin_notifications")

    for interval_value in intervals:
        interval_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=max(int(interval_value), 1),
            period=IntervalSchedule.DAYS,
        )
        PeriodicTask.objects.update_or_create(
            name=f"Reminder-{selected_activity.id}-{interval_value}d",
            defaults={
                "interval": interval_schedule,
                "task": "notifications.tasks.scheduled_activity_reminder",
                "args": f"[{selected_activity.id}, {int(interval_value)}]",
                "enabled": True,
            },
        )

    messages.success(request, "Reminder schedule saved to Celery Beat.")
    return redirect("notifications:admin_notifications")


@admin_required
@require_POST
def broadcast(request):
    audience = request.POST.get("audience")
    message = request.POST.get("message")
    if not audience or not message:
        messages.error(request, "Please choose an audience and enter a message.")
        return redirect("notifications:admin_notifications")

    job = NotificationJob.objects.create(
        job_type="broadcast",
        status="Queued",
        audience=audience,
        message=message,
    )
    process_broadcast_job.delay(job.id)
    messages.success(request, "Broadcast queued for background processing.")
    return redirect("notifications:admin_notifications")
