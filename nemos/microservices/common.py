from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse


def microservice_registry():
    return getattr(
        settings,
        "MICROSERVICE_REGISTRY",
        {
            "user_service": "http://127.0.0.1:8001",
            "ngo_service": "http://127.0.0.1:8002",
            "registration_service": "http://127.0.0.1:8003",
        },
    )


def service_url(service_name, path, query_params=None):
    base_url = microservice_registry()[service_name].rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    query_string = f"?{urlencode(query_params, doseq=True)}" if query_params else ""
    return f"{base_url}{normalized_path}{query_string}"


def proxy_request(request, service_name, downstream_path):
    target_url = service_url(service_name, downstream_path, request.GET)
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "accept-encoding"}
    }
    response = requests.request(
        method=request.method,
        url=target_url,
        headers=headers,
        data=request.body if request.body else None,
        timeout=15,
    )
    excluded_headers = {"content-encoding", "transfer-encoding", "connection"}
    django_response = HttpResponse(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type", "application/json"),
    )
    for header, value in response.headers.items():
        if header.lower() not in excluded_headers:
            django_response[header] = value
    return django_response


def registry_response():
    return JsonResponse({"services": microservice_registry()})
