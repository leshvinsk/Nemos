from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        return render(request, "accounts/login.html")

    username = request.POST.get("username")
    password = request.POST.get("password")
    user = authenticate(request, username=username, password=password)

    if user is None:
        messages.error(request, "Invalid username or password.")
        return render(request, "accounts/login.html")

    login(request, user)
    return redirect("ngo:activity_list")

def logout_view(request):
    logout(request)
    return redirect("accounts:login")
