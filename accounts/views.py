from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST

from accounts.permissions import login_redirect_name, sync_default_user_groups


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            sync_default_user_groups(request.user)
            return redirect(login_redirect_name(request.user))
        return render(request, "accounts/login.html", {"next": request.GET.get("next", "")})

    username = request.POST.get("username")
    password = request.POST.get("password")
    next_url = request.POST.get("next", "")
    user = authenticate(request, username=username, password=password)

    if user is None:
        messages.error(request, "Invalid username or password.")
        return render(request, "accounts/login.html", {"next": next_url})

    login(request, user)
    sync_default_user_groups(user)
    request.session["role_name"] = "administrator" if user.is_staff or user.is_superuser else "employee"
    request.session["login_username"] = user.username
    request.session["last_login_method"] = "form"
    return redirect(next_url or login_redirect_name(user))

@require_POST
def logout_view(request):
    request.session.flush()
    logout(request)
    return redirect("accounts:login")
