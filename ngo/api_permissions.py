from accounts.permissions import is_administrator, is_employee
from rest_framework.permissions import BasePermission


class IsAdministratorUser(BasePermission):
    message = "Administrator access required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_administrator(request.user))


class IsEmployeeUser(BasePermission):
    message = "Employee access required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_employee(request.user))
