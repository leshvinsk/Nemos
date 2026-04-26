from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from accounts.permissions import admin_required, employee_required, is_administrator
from core.gateway_client import GatewayError, gateway_get
from registrations.services.registration_service import RegistrationService


@employee_required
@require_http_methods(["POST"])
def register(request, activity_id: int):
    service = RegistrationService()
    success, msg = service.register_employee(request.user, activity_id)
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("ngo:activity_list")


@employee_required
@require_http_methods(["POST"])
def cancel(request, activity_id: int):
    service = RegistrationService()
    success, msg = service.cancel_registration(request.user, activity_id)
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("ngo:activity_list")


@employee_required
@require_GET
def my_history(request):
    service = RegistrationService()
    history = service.employee_history(request.user)
    return render(request, "registrations/my_history.html", {"history": history})


@admin_required
@require_GET
def admin_monitor(request):
    try:
        summary = gateway_get("/api/registrations/summary/")
    except GatewayError:
        service = RegistrationService()
        summary = service.monitor_summary()
        messages.warning(request, "Gateway unavailable. Showing direct registration summary.")
    totals = {
        "offered": summary.get("offered", 0),
        "taken": summary.get("taken", 0),
        "remaining": summary.get("remaining", 0),
    }
    rows = summary.get("rows", [])
    return render(
        request,
        "registrations/admin_monitor.html",
        {"totals": totals, "rows": rows},
    )
