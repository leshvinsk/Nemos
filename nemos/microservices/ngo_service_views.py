from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ngo.models import NGOAvailability
from ngo.services.activity_service import ActivityService


@require_GET
def ngo_list(request):
    ngos = [
        {
            "id": ngo.id,
            "name": ngo.name,
            "description": ngo.description,
            "contact_email": ngo.contact_email,
            "contact_phone": ngo.contact_phone,
            "is_active": ngo.is_active,
        }
        for ngo in ActivityService.list_ngos_admin()
    ]
    return JsonResponse({"service": "ngo_service", "results": ngos})


@require_GET
def activity_list(request):
    activities = [
        {
            "id": activity.id,
            "ngo": {"id": activity.ngo.id, "name": activity.ngo.name},
            "service_type": activity.service_type,
            "description": activity.description,
            "location": activity.location,
            "service_date": activity.service_date.isoformat(),
            "cutoff_time": activity.cutoff_time.isoformat(),
            "max_slots": activity.max_slots,
            "is_active": activity.is_active,
        }
        for activity in NGOAvailability.objects.select_related("ngo")
        .filter(is_active=True, ngo__is_active=True)
        .order_by("service_date", "ngo__name")
    ]
    return JsonResponse({"service": "ngo_service", "results": activities})
