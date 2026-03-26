from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from accounts.permissions import is_administrator
from ngo.services.activity_service import ActivityService

staff_required = user_passes_test(is_administrator)


@staff_required
@require_GET
def admin_notifications(request):
    activities = ActivityService().list_all_admin()
    return render(
        request,
        "notifications/admin_notifications.html",
        {"activities": activities},
    )


@staff_required
@require_GET
def qr_checkin(request):
    activities = ActivityService().list_all_admin()
    User = get_user_model()
    employees = User.objects.filter(is_active=True, is_staff=False).order_by("username")[:20]
    return render(
        request,
        "notifications/qr_checkin.html",
        {
            "activities": activities[:3],
            "employees": employees,
        },
    )


@staff_required
@require_POST
def schedule(request):
    activity_id = request.POST.get("activity_id")
    intervals = request.POST.get("intervals")
    _ = (activity_id, intervals)  # prototype only; intentionally not persisted/sent

    messages.success(request, "Schedule saved")
    return redirect("notifications:admin_notifications")


@staff_required
@require_POST
def broadcast(request):
    audience = request.POST.get("audience")
    message = request.POST.get("message")
    _ = (audience, message)  # prototype only; intentionally not persisted/sent

    messages.success(request, "Broadcast sent")
    return redirect("notifications:admin_notifications")
