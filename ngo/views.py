from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ngo.services.activity_service import ActivityService


def _staff_only(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Delegate to login_required behavior
            return login_required(view_func)(request, *args, **kwargs)
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


@login_required
@require_GET
def activity_list(request):
    service = ActivityService()
    # Availability slots for employees (computed slot counters attached in service).
    activities = service.list_available_slots_for_employees()
    return render(request, "ngo/activity_list.html", {"activities": activities})

@_staff_only
@require_GET
def admin_ngo_manage(request):
    service = ActivityService()
    ngos = service.list_ngos_admin()
    return render(request, "ngo/admin_ngo_manage.html", {"ngos": ngos})


@_staff_only
@require_POST
def admin_ngo_create(request):
    service = ActivityService()
    service.create_ngo(request.POST)
    messages.success(request, "NGO created successfully.")
    return redirect("ngo:admin_ngo_manage")


@_staff_only
@require_http_methods(["POST", "PATCH"])
def admin_ngo_update(request, ngo_id: int):
    service = ActivityService()
    service.update_ngo(ngo_id, request.POST)
    messages.success(request, "NGO updated successfully.")
    return redirect("ngo:admin_ngo_manage")


@_staff_only
@require_http_methods(["POST", "DELETE"])
def admin_ngo_delete(request, ngo_id: int):
    service = ActivityService()
    service.deactivate_ngo(ngo_id)
    messages.success(request, "NGO deactivated successfully.")
    return redirect("ngo:admin_ngo_manage")


@_staff_only
@require_GET
def admin_activity_manage(request):
    service = ActivityService()
    activities = service.list_slots_admin()
    ngos = service.list_ngos_admin()
    return render(request, "ngo/admin_activity_manage.html", {"activities": activities, "ngos": ngos})


@_staff_only
@require_POST
def admin_activity_create(request):
    service = ActivityService()
    if not request.POST.get("ngo_id"):
        messages.error(request, "Please select an NGO.")
        return redirect("ngo:admin_activity_manage")
    service.create_slot(request.POST)
    messages.success(request, "Slot created successfully.")
    return redirect("ngo:admin_activity_manage")


@_staff_only
@require_http_methods(["POST", "PATCH"])
def admin_activity_update(request, activity_id: int):
    service = ActivityService()
    service.update_slot(activity_id, request.POST)
    messages.success(request, "Slot updated successfully.")
    return redirect("ngo:admin_activity_manage")


@_staff_only
@require_http_methods(["POST", "DELETE"])
def admin_activity_delete(request, activity_id: int):
    service = ActivityService()
    service.deactivate_slot(activity_id)
    messages.success(request, "Slot deactivated successfully.")
    return redirect("ngo:admin_activity_manage")
