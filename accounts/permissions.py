from __future__ import annotations

from django.contrib.auth.models import Group
from django.http import HttpResponseForbidden

ADMIN_GROUP = "Administrator"
EMPLOYEE_GROUP = "Employee"


def is_administrator(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name=ADMIN_GROUP).exists()


def is_employee(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if is_administrator(user):
        return False
    return True


def login_redirect_name(user) -> str:
    if is_administrator(user):
        return "ngo:admin_activity_manage"
    return "ngo:activity_list"


def sync_default_user_groups(user) -> None:
    if not getattr(user, "is_authenticated", False):
        return
    if is_administrator(user):
        return
    if user.groups.filter(name=EMPLOYEE_GROUP).exists():
        return

    employee_group, _ = Group.objects.get_or_create(name=EMPLOYEE_GROUP)
    user.groups.add(employee_group)


def employee_required(view_func):
    def _wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            from django.contrib.auth.decorators import login_required

            return login_required(view_func)(request, *args, **kwargs)
        if not is_employee(user):
            return HttpResponseForbidden("Employee access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            from django.contrib.auth.decorators import login_required

            return login_required(view_func)(request, *args, **kwargs)
        if not is_administrator(user):
            return HttpResponseForbidden("Administrator access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped
