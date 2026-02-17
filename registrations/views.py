from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from registrations.services.registration_service import RegistrationService


def _staff_only(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


@login_required
@require_http_methods(["POST"])
def register(request, activity_id: int):
    service = RegistrationService()
    success, msg = service.register_employee(request.user, activity_id)
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("ngo:activity_list")


@login_required
@require_http_methods(["POST"])
def cancel(request, activity_id: int):
    service = RegistrationService()
    success, msg = service.cancel_registration(request.user, activity_id)
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("ngo:activity_list")


@_staff_only
@require_GET
def admin_monitor(request):
    service = RegistrationService()
    summary = service.monitor_summary()
    totals = {
        "offered": summary.get("offered", 0),
        "taken": summary.get("taken", 0),
        "remaining": summary.get("remaining", 0),
    }
    rows = summary.get("rows", [])
    return render(request, "registrations/admin_monitor.html", {"totals": totals, "rows": rows})
