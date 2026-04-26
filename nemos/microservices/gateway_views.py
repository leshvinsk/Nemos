from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from nemos.microservices.common import proxy_request, registry_response


def gateway_home(request):
    return JsonResponse(
        {
            "service": "api_gateway",
            "message": "NEMOS API Gateway is running.",
            "routes": {
                "users": "/api/users/",
                "ngos": "/api/ngos/",
                "registrations": "/api/registrations/",
                "registry": "/registry/",
            },
        }
    )


def gateway_registry(request):
    return registry_response()


@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def users_proxy(request, downstream_path=""):
    return proxy_request(request, "user_service", f"/users/{downstream_path}")


@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def ngos_proxy(request, downstream_path=""):
    if downstream_path.startswith("activities"):
        suffix = downstream_path[len("activities"):].lstrip("/")
        return proxy_request(request, "ngo_service", f"/activities/{suffix}")
    return proxy_request(request, "ngo_service", f"/ngos/{downstream_path}")


@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def registrations_proxy(request, downstream_path=""):
    if downstream_path.startswith("summary"):
        suffix = downstream_path[len("summary"):].lstrip("/")
        return proxy_request(request, "registration_service", f"/registrations/summary/{suffix}")
    return proxy_request(request, "registration_service", f"/registrations/{downstream_path}")
