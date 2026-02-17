from __future__ import annotations

import time

from django.shortcuts import redirect


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        print(f"[timing] {request.method} {request.path} -> {elapsed_ms:.2f}ms")
        return response


class MethodOverrideMiddleware:
    """
    Allows HTML forms to emulate PATCH/DELETE by sending POST with _method.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and "_method" in request.POST:
            override = (request.POST.get("_method") or "").upper()
            if override in {"PATCH", "DELETE"}:
                request.method = override
        return self.get_response(request)


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/service-day/admin/"):
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated or not user.is_staff:
                return redirect("/login/")
        return self.get_response(request)

