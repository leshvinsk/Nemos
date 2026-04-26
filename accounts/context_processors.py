from accounts.permissions import is_administrator, is_employee


def role_context(request):
    user = getattr(request, "user", None)
    return {
        "is_administrator": is_administrator(user),
        "is_employee": is_employee(user),
        "session_role_name": request.session.get("role_name", ""),
        "session_login_username": request.session.get("login_username", ""),
    }
