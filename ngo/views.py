from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.permissions import admin_required, is_administrator
from core.gateway_client import GatewayError, gateway_get
from ngo.services.activity_service import ActivityService
from registrations.models import Registration


def _require_internal_api_token(request):
    configured_token = settings.INTERNAL_API_TOKEN
    if not configured_token:
        return False
    provided_token = (request.headers.get("X-API-Token") or "").strip()
    return provided_token == configured_token


@login_required
@require_GET
def activity_list(request):
    service = ActivityService()
    # Availability slots for employees (computed slot counters attached in service).
    activities = service.list_available_slots_for_employees()
    registered_ids = set(
        Registration.objects.filter(employee=request.user).values_list("activity_id", flat=True)
    )
    now = timezone.now()
    return render(
        request,
        "ngo/activity_list.html",
        {
            "activities": activities,
            "registered_ids": registered_ids,
            "now": now,
        },
    )

@admin_required
@require_GET
def admin_ngo_manage(request):
    try:
        ngos = gateway_get("/api/ngos/").get("results", [])
    except GatewayError:
        ngos = ActivityService().list_ngos_admin()
        messages.warning(request, "Gateway unavailable. Showing direct NGO data.")
    return render(request, "ngo/admin_ngo_manage.html", {"ngos": ngos})


@admin_required
@require_POST
def admin_ngo_create(request):
    service = ActivityService()
    try:
        service.create_ngo(request.POST)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "NGO created successfully.")
    return redirect("ngo:admin_ngo_manage")


@admin_required
@require_POST
def admin_ngo_update(request, ngo_id: int):
    service = ActivityService()
    try:
        service.update_ngo(ngo_id, request.POST)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "NGO updated successfully.")
    return redirect("ngo:admin_ngo_manage")


@admin_required
@require_POST
def admin_ngo_delete(request, ngo_id: int):
    service = ActivityService()
    try:
        service.deactivate_ngo(ngo_id)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "NGO deactivated successfully.")
    return redirect("ngo:admin_ngo_manage")


@admin_required
@require_GET
def admin_activity_manage(request):
    service = ActivityService()
    try:
        activities = gateway_get("/api/ngos/activities/").get("results", [])
        ngos = gateway_get("/api/ngos/").get("results", [])
    except GatewayError:
        activities = service.list_slots_admin()
        ngos = service.list_ngos_admin()
        messages.warning(request, "Gateway unavailable. Showing direct activity data.")
    return render(request, "ngo/admin_activity_manage.html", {"activities": activities, "ngos": ngos})


@admin_required
@require_POST
def admin_activity_create(request):
    service = ActivityService()
    if not request.POST.get("ngo_id"):
        messages.error(request, "Please select an NGO.")
        return redirect("ngo:admin_activity_manage")
    try:
        service.create_slot(request.POST)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Slot created successfully.")
    return redirect("ngo:admin_activity_manage")


@admin_required
@require_POST
def admin_activity_update(request, activity_id: int):
    service = ActivityService()
    try:
        service.update_slot(activity_id, request.POST)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Slot updated successfully.")
    return redirect("ngo:admin_activity_manage")


@admin_required
@require_POST
def admin_activity_delete(request, activity_id: int):
    service = ActivityService()
    try:
        service.deactivate_slot(activity_id)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Slot deactivated successfully.")
    return redirect("ngo:admin_activity_manage")


@admin_required
@require_GET
def admin_ngo_api(request):
    if not _require_internal_api_token(request):
        return JsonResponse({"detail": "Valid API token required."}, status=401)

    service = ActivityService()
    payload = [
        {
            "id": ngo.id,
            "name": ngo.name,
            "description": ngo.description,
            "contact_email": ngo.contact_email,
            "contact_phone": ngo.contact_phone,
        }
        for ngo in service.list_ngos_admin()
    ]
    return JsonResponse({"results": payload})
