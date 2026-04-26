from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from registrations.models import Registration
from registrations.services.registration_service import RegistrationService


@require_GET
def registration_list(request):
    registrations = [
        {
            "id": registration.id,
            "employee": registration.employee.username,
            "activity": registration.activity.ngo.name,
            "service_type": registration.activity.service_type,
            "registered_at": registration.registered_at.isoformat(),
        }
        for registration in Registration.objects.select_related("employee", "activity__ngo").all()
    ]
    return JsonResponse({"service": "registration_service", "results": registrations})


@require_GET
def registration_summary(request):
    summary = RegistrationService.monitor_summary()
    return JsonResponse({"service": "registration_service", **summary})
