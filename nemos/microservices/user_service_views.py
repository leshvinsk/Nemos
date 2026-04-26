from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.permissions import is_administrator


@require_GET
def user_list(request):
    User = get_user_model()
    users = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": "administrator" if is_administrator(user) else "employee",
            "is_active": user.is_active,
        }
        for user in User.objects.filter(is_active=True).order_by("username")
    ]
    return JsonResponse({"service": "user_service", "results": users})


@require_GET
def user_detail(request, user_id):
    User = get_user_model()
    user = User.objects.get(id=user_id)
    payload = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": "administrator" if is_administrator(user) else "employee",
        "is_active": user.is_active,
    }
    return JsonResponse(payload)
